"""Inert, credential-free verified ciphertext downloader. No SDK or key access.

Publish downloaded bytes only after exact expected SHA-256 and length match.
The caller owns/validates the B2 object identity and closes the SDK body.
The destination must be in a private, trusted staging directory.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO

CHUNK_BYTES = 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class DownloadRejected(ValueError):
    """Generic fail-closed download failure without sensitive SDK response text."""


def publish_verified_ciphertext(
    body: BinaryIO, destination: Path, *, expected_sha256: str,
    expected_bytes: int, max_ciphertext_bytes: int,
) -> dict[str, str | int]:
    """Stage bytes privately, hash, then publish exclusively by hard link.

    An unauthorized process writing inside the *trusted* staging directory is
    outside this function's guarantees. Never point to a public/shared folder.
    No destination path is created for a corrupt, oversized, interrupted or
    competing download; the exclusive link cannot overwrite another file.
    """
    if (not isinstance(destination, Path) or destination.suffix != ".age"
            or destination.exists() or destination.is_symlink()):
        raise DownloadRejected("new age destination required")
    if (not isinstance(expected_sha256, str)
            or not SHA256.fullmatch(expected_sha256)):
        raise DownloadRejected("valid pinned SHA-256 required")
    if (type(expected_bytes) is not int or type(max_ciphertext_bytes) is not int
            or expected_bytes <= 100 or max_ciphertext_bytes <= 100
            or expected_bytes > max_ciphertext_bytes):
        raise DownloadRejected("pinned ciphertext length outside cap")
    parent = destination.parent
    try:
        if parent.is_symlink() or not parent.is_dir():
            raise DownloadRejected("trusted private staging directory required")
        mode = parent.stat().st_mode
        if not stat.S_ISDIR(mode) or mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise DownloadRejected("trusted private staging directory required")
    except OSError:
        raise DownloadRejected("staging directory unavailable") from None

    fd = None
    temporary = None
    try:
        fd, name = tempfile.mkstemp(prefix="." + destination.name + ".", suffix=".part", dir=parent)
        temporary = Path(name)
        checksum = hashlib.sha256()
        n = 0
        with os.fdopen(fd, "wb") as output:
            fd = None
            while True:
                chunk = body.read(CHUNK_BYTES)
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise DownloadRejected("unexpected ciphertext stream chunk")
                n += len(chunk)
                if n > expected_bytes or n > max_ciphertext_bytes:
                    raise DownloadRejected("ciphertext exceeded pinned length")
                output.write(chunk)
                checksum.update(chunk)
            if n != expected_bytes or checksum.hexdigest() != expected_sha256:
                raise DownloadRejected("ciphertext integrity mismatch")
            output.flush()
            os.fsync(output.fileno())
        # Atomic no-clobber publication; NEVER use os.replace here.
        os.link(temporary, destination)
        return {"sha256": expected_sha256, "size_bytes": n}
    except Exception:
        raise DownloadRejected("verified ciphertext publication failed") from None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
