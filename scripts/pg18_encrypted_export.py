"""Manual building block: stream full PG18 archive and passwordless roles to age.

Not a workflow/CLI and not a source-identity, privilege, provider or restore gate.
An authorized caller MUST first verify the exact source and export readiness.
No credentials in argv/logs, no plaintext dumps on disk, no cloud operations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time


class ExportRejected(ValueError):
    """Generic failure; never include paths, subprocess output or credentials."""


@dataclass(frozen=True)
class EncryptedPart:
    path: Path
    sha256: str
    size_bytes: int


def _private(path: Path, *, directory: bool) -> None:
    try:
        info = path.lstat()
        correct = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if not correct or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ExportRejected('private owner-controlled path required')
    except OSError:
        raise ExportRejected('private owner-controlled path required') from None


def _stream(command: list[str], destination: Path, recipient: str,
            env: dict[str, str], max_bytes: int, timeout: int) -> EncryptedPart:
    processes = []
    fd = None
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        producer = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        processes.append(producer)
        encryptor = subprocess.Popen(['age', '--encrypt', '--recipient', recipient],
            stdin=producer.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        processes.append(encryptor)
        producer.stdout.close()
        digest = hashlib.sha256(); size = 0
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(encryptor.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise ExportRejected('encrypted export timed out')
                chunk = os.read(encryptor.stdout.fileno(), 65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ExportRejected('encrypted export exceeds byte cap')
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    count = os.write(fd, view)
                    view = view[count:]
        for process in processes:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or process.wait(timeout=remaining) != 0:
                raise ExportRejected('dump or encryption process failed')
        if size <= 100:
            raise ExportRejected('encrypted export unexpectedly small')
        os.fsync(fd)
        return EncryptedPart(destination, digest.hexdigest(), size)
    except (OSError, subprocess.SubprocessError):
        raise ExportRejected('dump or encryption process failed') from None
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.kill()
            process.wait()
            if process.stdout:
                process.stdout.close()
        if fd is not None:
            os.close(fd)


def encrypted_export(*, output: Path, service_file: Path, service: str,
                     recipient: str, max_bytes: int,
                     env: dict[str, str] | None = None, timeout: int = 1200
                     ) -> dict[str, EncryptedPart]:
    """Create two ciphertexts in a new private empty staging directory.

    max_bytes caps the TOTAL ciphertext package (both parts). Partial packages
    are removed on failure. Roles omit password hashes deliberately; recovery
    authentication must be provisioned separately. Managed Auth runtime is not
    reproduced by SQL restoration. No RESTORE_PASS is returned.
    """
    _private(output, directory=True); _private(service_file, directory=False)
    if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,62}', service)
            or not re.fullmatch(r'age1[0-9a-z]{58}', recipient)
            or type(max_bytes) is not int or not 110 <= max_bytes <= 256*1024*1024
            or type(timeout) is not int or not 1 <= timeout <= 3600):
        raise ExportRejected('invalid bounded export configuration')
    if any(output.iterdir()):
        raise ExportRejected('empty private output directory required')
    # Remove inherited PG overrides, including PGPASSWORD/PGOPTIONS/PGDATABASE.
    child_env = {k: v for k, v in (os.environ if env is None else env).items()
                 if not k.startswith('PG')}
    child_env.update(PGSERVICEFILE=str(service_file.absolute()), PGSERVICE=service,
                     PGPASSFILE='/dev/null', PGCONNECT_TIMEOUT='15')
    for tool in ('pg_dump', 'pg_dumpall'):
        try:
            version = subprocess.run([tool, '--version'], env=child_env,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=True).stdout
            if not re.fullmatch(rb'pg_dump(?:all)? \(PostgreSQL\) 18(?:\.[0-9]+)?[^\n]*\n?', version):
                raise ExportRejected('PostgreSQL 18 client tools required')
        except (OSError, subprocess.SubprocessError):
            raise ExportRejected('PostgreSQL 18 client tools required') from None
    paths = [output/'database.pgdump.age', output/'roles.sql.age']
    result = {}
    try:
        remaining = max_bytes
        for name, command, path in (
            ('database', ['pg_dump', '--format=custom', '--create'], paths[0]),
            ('roles', ['pg_dumpall', '--roles-only', '--no-role-passwords'], paths[1]),
        ):
            part = _stream(command, path, recipient, child_env, remaining, timeout)
            remaining -= part.size_bytes
            result[name] = part
        return result
    except BaseException:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
