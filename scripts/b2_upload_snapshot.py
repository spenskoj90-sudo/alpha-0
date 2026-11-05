"""Freeze a pinned, already-encrypted age upload before any B2 SDK call.

The returned immutable bytes must be the *only* SDK Body. The source staging
parent must be a private, owner-controlled directory. Header inspection is
format preflight, NOT cryptographic proof that age encryption/decryption works.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path

from b2_versioned_transfer import AGE_V1_STANZA_PREFIX, TransferRejected

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def pinned_ciphertext_snapshot(source: Path, max_bytes: int,
                               expected_sha256: str, expected_bytes: int) -> bytes:
    """Copy once, verify every byte, then expose an immutable, pinned SDK Body.

    O_NOFOLLOW and O_NONBLOCK prevent a replaced symlink or FIFO from being
    followed/hanging. If input changes while read, the pinned digest rejects it.
    A separate OS user/process boundary is required against hostile same-UID
    modifications to the private parent itself; this method cannot guarantee
    that earlier *source* custody was trustworthy.
    """
    if (not isinstance(source, Path) or source.suffix != ".age"
            or type(max_bytes) is not int or max_bytes <= 100
            or type(expected_bytes) is not int or not 100 < expected_bytes <= max_bytes
            or not isinstance(expected_sha256, str)
            or not _SHA256.fullmatch(expected_sha256)):
        raise TransferRejected("pinned ciphertext length, hash and path required")
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC", "geteuid")):
        raise TransferRejected("no safe no-follow ciphertext staging support")
    # Preserve the explicit no-symlink diagnostic. O_NOFOLLOW still protects
    # against replacements occurring after this check.
    if source.is_symlink():
        raise TransferRejected("regular local age ciphertext file required")
    try:
        parent = source.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode)
                or parent.st_uid != os.geteuid() or parent.st_mode & 0o077):
            raise TransferRejected("owner-private ciphertext staging directory required")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        fd = os.open(source, flags)
        with os.fdopen(fd, "rb") as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_size > max_bytes:
                raise TransferRejected("regular pinned ciphertext file required")
            snapshot = stream.read(max_bytes + 1)
        if not snapshot.startswith(AGE_V1_STANZA_PREFIX):
            raise TransferRejected("binary age v1 header missing")
        if (len(snapshot) != expected_bytes
                or hashlib.sha256(snapshot).hexdigest() != expected_sha256):
            raise TransferRejected("pinned ciphertext changed")
    except (OSError, ValueError) as exc:
        if isinstance(exc, TransferRejected):
            raise
        raise TransferRejected("pinned ciphertext could not be safely captured") from None
    return snapshot
