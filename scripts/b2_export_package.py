"""Unwired two-part encrypted export transport. No credentials/client creation.

Actual B2 scopes, billing/Class D, source/export authority and recovery custody
must be separately approved and verified. A returned receipt is ciphertext
transport evidence only, never independent PostgreSQL/Auth RESTORE_PASS.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Callable

from b2_s3_transport import B2S3Transport, independently_scoped_transports
from b2_upload_snapshot import pinned_ciphertext_snapshot
from b2_versioned_transfer import MAX_STAGE_BYTES, Receipt, new_unique_key, stage_and_verify
from pg18_encrypted_export import EncryptedPart


class PackageRejected(ValueError):
    """Generic rejection. Use the private journal to reconcile partial uploads."""


def transfer_export_package(*, parts: dict[str, EncryptedPart],
                            writer: B2S3Transport, reader: B2S3Transport,
                            expected_owner: str, max_total_bytes: int,
                            journal: Callable[[dict], None]) -> dict[str, Receipt]:
    """Verify both exported hashes BEFORE network; preserve partial remote copies.

    journal MUST synchronously persist private recovery metadata before returning.
    A planned event records every unique key/hash/length before any provider call.
    Each verified event records a version receipt after independent readback.
    A missing verified event may still mean PUT succeeded: reconcile planned keys
    before retrying. Never delete/overwrite partial objects or claim package PASS.
    Caller retains original ciphertexts; local temporary ciphertext copies are
    removed. No real source data or credential belongs in a public journal.
    """
    try:
        if (type(parts) is not dict or set(parts) != {'database', 'roles'}
                or any(type(v) is not EncryptedPart for v in parts.values())
                or type(max_total_bytes) is not int or not 200 < max_total_bytes <= MAX_STAGE_BYTES
                or not callable(journal)):
            raise PackageRejected('complete bounded encrypted package required')
        independently_scoped_transports(writer, reader)
        if (writer.max_ciphertext_bytes < max_total_bytes
                or reader.max_ciphertext_bytes < max_total_bytes):
            raise PackageRejected('transport byte caps must cover package cap')
        if (any(type(v.size_bytes) is not int for v in parts.values())
                or sum(v.size_bytes for v in parts.values()) > max_total_bytes
                or parts['database'].path == parts['roles'].path):
            raise PackageRejected('distinct parts within aggregate byte cap required')
        # Capture both export-pinned inputs, not freshly recalculated identities.
        snapshots = {name: pinned_ciphertext_snapshot(
            part.path, max_total_bytes, part.sha256, part.size_bytes)
            for name, part in parts.items()}
        keys = {name: new_unique_key() for name in ('database','roles')}
        if len(set(keys.values())) != 2:
            raise PackageRejected('distinct fresh object keys required')
        journal({'event':'planned','parts':{
            name:{'key':keys[name],'sha256':parts[name].sha256,'size_bytes':parts[name].size_bytes}
            for name in ('database','roles')}})
        receipts = {}
        with tempfile.TemporaryDirectory(prefix='g3-ciphertext-package-') as tmp:
            root = Path(tmp)
            for name in ('database','roles'):
                source=root/(name+'.age')
                fd=os.open(source,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as stream:
                    stream.write(snapshots[name])
                receipt=stage_and_verify(endpoint=writer.endpoint,region=writer.region,
                    bucket=writer.bucket,expected_owner=expected_owner,key=keys[name],
                    ciphertext=source,max_ciphertext_bytes=max_total_bytes,
                    uploader=writer,reader=reader,download_path=root/(name+'-readback.age'))
                if receipt.sha256 != parts[name].sha256 or receipt.size_bytes != parts[name].size_bytes:
                    raise PackageRejected('export identity changed during transfer')
                journal({'event':'verified','part':name,'receipt':receipt})
                receipts[name]=receipt
        return receipts
    except Exception:
        # Provider/client/journal exceptions can contain credentials or paths.
        # No cleanup requests to B2: partial copies are recovery assets.
        raise PackageRejected('encrypted package incomplete; reconcile private planned keys') from None
