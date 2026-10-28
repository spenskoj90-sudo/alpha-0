"""Inert, credential-free-verifiable B2 ciphertext transfer guard.

Not imported by an Actions backup or release workflow. The caller must supply
distinct bucket-scoped upload and read-only transports *after* owner/provider
gates. No connection strings, API keys or plaintext backup data in this file.
The S3 transport adapter and actual external restore are separate gates.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import token_hex
from typing import Callable

from b2_target_contract import require_version_id, validate_target

MAX_STAGE_BYTES = 256 * 1024 * 1024
KEY = re.compile(r"sentinel/staging/sentinel-db-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{24}\.pgdump\.age\Z")


class TransferRejected(ValueError):
    """Fail-closed transport or acceptance requirement."""


@dataclass(frozen=True)
class Receipt:
    key: str
    version_id: str
    sha256: str
    size_bytes: int


def new_unique_key(instant: datetime | None = None, nonce: str | None = None) -> str:
    when = instant or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise TransferRejected("timestamp must be timezone-aware")
    stamp = when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    random_hex = nonce if nonce is not None else token_hex(12)
    result = f"sentinel/staging/sentinel-db-{stamp}-{random_hex}.pgdump.age"
    if not KEY.fullmatch(result):
        raise TransferRejected("unexpected object naming")
    return result


def _versions(transport: Callable, bucket: str, key: str) -> tuple[list, list]:
    response = transport("list-object-versions", bucket=bucket, prefix=key, max_keys=10)
    if not isinstance(response, dict) or response.get("IsTruncated") is not False:
        raise TransferRejected("B2 version enumeration incomplete")
    versions = [v for v in response.get("Versions", []) if v.get("Key") == key]
    hidden = [v for v in response.get("DeleteMarkers", []) if v.get("Key") == key]
    return versions, hidden


def _private_bucket(transport: Callable, bucket: str, expected_owner: str) -> None:
    if not expected_owner or len(expected_owner) > 200:
        raise TransferRejected("independent expected bucket owner required")
    acl = transport("get-bucket-acl", bucket=bucket)
    if not isinstance(acl, dict) or acl.get("Owner", {}).get("ID") != expected_owner:
        raise TransferRejected("bucket ownership not verified")
    grants = acl.get("Grants")
    if not isinstance(grants, list) or len(grants) != 1:
        raise TransferRejected("bucket ACL not exclusively private")
    grant = grants[0]
    if (grant.get("Permission") != "FULL_CONTROL"
            or grant.get("Grantee", {}).get("Type") != "CanonicalUser"
            or grant.get("Grantee", {}).get("ID") != expected_owner):
        raise TransferRejected("bucket ACL not exclusively private")


def stage_and_verify(
    *, endpoint: str, region: str, bucket: str, expected_owner: str,
    key: str, ciphertext: pathlib.Path, max_ciphertext_bytes: int,
    uploader: Callable, reader: Callable, download_path: pathlib.Path
) -> Receipt:
    """No side effects until all local and bucket guards pass.

    Transport operations: get-bucket-acl, list-object-versions, put-object,
    head-object, get-object. Upload is intentionally NOT wired to production.
    Reader must be an independently provisioned read-only transport.
    No overwrite/hide/delete requests are ever generated.
    """
    validate_target(endpoint, region, bucket, max_ciphertext_bytes)
    if max_ciphertext_bytes > MAX_STAGE_BYTES:
        raise TransferRejected("staging single-object safety cap exceeded")
    if not KEY.fullmatch(key):
        raise TransferRejected("object key must be a fresh non-reusable namespace key")
    if uploader is reader:
        raise TransferRejected("a separately scoped read transport is required")
    if not ciphertext.is_file() or ciphertext.suffix != ".age":
        raise TransferRejected("pre-encrypted age ciphertext file required")
    if download_path.exists() or download_path == ciphertext:
        raise TransferRejected("download path must be new and independent")
    size = ciphertext.stat().st_size
    if size <= 100 or size > max_ciphertext_bytes:
        raise TransferRejected("ciphertext size outside explicit pre-upload cap")
    digest = hashlib.file_digest(ciphertext.open("rb"), "sha256").hexdigest()
    _private_bucket(uploader, bucket, expected_owner)
    before, old_hidden = _versions(uploader, bucket, key)
    if before or old_hidden:
        raise TransferRejected("object key already used; refusing overwrite or hidden generation")
    response = uploader("put-object", bucket=bucket, key=key, path=ciphertext)
    version = response.get("VersionId") if isinstance(response, dict) else None
    try:
        require_version_id(version)
    except (ValueError, TypeError) as exc:
        raise TransferRejected("upload did not return a valid version ID") from exc
    # Independent read identity must be able to list the exact uploaded version.
    actual, markers = _versions(reader, bucket, key)
    if markers or len(actual) != 1:
        raise TransferRejected("unexpected version count or hide markers")
    if actual[0].get("VersionId") != version or actual[0].get("Size") != size:
        raise TransferRejected("listed B2 version identity or size mismatch")
    head = reader("head-object", bucket=bucket, key=key, version_id=version)
    if head.get("VersionId") != version or head.get("ContentLength") != size:
        raise TransferRejected("version-specific HEAD mismatch")
    result = reader("get-object", bucket=bucket, key=key, version_id=version,
                    output_path=download_path)
    if result.get("VersionId") != version or not download_path.is_file():
        raise TransferRejected("version-specific ciphertext download failed")
    if download_path.stat().st_size != size:
        raise TransferRejected("remote ciphertext length differs from source")
    with download_path.open("rb") as stream:
        downloaded_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if downloaded_digest != digest:
        raise TransferRejected("remote ciphertext SHA-256 mismatch")
    return Receipt(key=key, version_id=version, sha256=digest, size_bytes=size)
