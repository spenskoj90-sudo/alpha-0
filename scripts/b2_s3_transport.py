"""Inert Backblaze B2 S3 adapter for the version-pinned ciphertext contract.

This module neither creates a client nor reads credentials/environment variables.
It is not called by any GitHub Actions workflow. A separate reviewed entrypoint
must supply two independently scoped, preconfigured S3 clients. Offline tests use
synthetic clients only; they are NOT proof of provider authorization or backup.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from b2_target_contract import validate_target
from b2_versioned_transfer import KEY, MAX_STAGE_BYTES, TransferRejected

CHUNK_BYTES = 1024 * 1024


class B2S3Transport:
    """Restrict a preconfigured S3 client to one role and five exact operations.

    A writer can check bucket ACL, list an exact key and upload. A distinct
    reader can list, HEAD and download a specific version. The S3 clients must
    independently enforce provider-side least-privilege; this adapter is not a
    substitute for negative authorization tests on the provider itself.
    """

    def __init__(self, client: Any, *, role: str, endpoint: str,
                 region: str, bucket: str, max_ciphertext_bytes: int) -> None:
        validate_target(endpoint, region, bucket, max_ciphertext_bytes)
        if max_ciphertext_bytes > MAX_STAGE_BYTES:
            raise TransferRejected("B2 staging byte cap exceeded")
        if role not in {"writer", "reader"}:
            raise TransferRejected("unknown B2 transport role")
        # Do not silently route through a different provider or AWS S3.
        meta = getattr(client, "meta", None)
        if (getattr(meta, "endpoint_url", None) != endpoint
                or getattr(meta, "region_name", None) != region):
            raise TransferRejected("S3 client endpoint or region mismatch")
        self._client = client
        self.role = role
        self.endpoint = endpoint
        self.region = region
        self.bucket = bucket
        self.max_ciphertext_bytes = max_ciphertext_bytes

    @property
    def client(self) -> Any:
        """Identity-only reference for the caller's independent-client check."""
        return self._client

    def __call__(self, operation: str, **kw: Any) -> dict:
        if kw.get("bucket") != self.bucket:
            raise TransferRejected("bucket scope mismatch")
        if operation == "get-bucket-acl" and self.role == "writer":
            if set(kw) != {"bucket"}:
                raise TransferRejected("unexpected ACL request fields")
            return self._sdk("get_bucket_acl", Bucket=self.bucket)

        if operation == "list-object-versions":
            if (set(kw) != {"bucket", "prefix", "max_keys"}
                    or kw["max_keys"] != 10 or not isinstance(kw["prefix"], str)
                    or not KEY.fullmatch(kw["prefix"])):
                raise TransferRejected("version enumeration must target one exact key")
            return self._sdk("list_object_versions", Bucket=self.bucket,
                             Prefix=kw["prefix"], MaxKeys=10)

        if operation == "put-object" and self.role == "writer":
            if (set(kw) != {"bucket", "key", "path"}
                    or not isinstance(kw["key"], str)
                    or not KEY.fullmatch(kw["key"])):
                raise TransferRejected("unsafe B2 upload request")
            source = kw["path"]
            if not isinstance(source, Path) or not source.is_file() or source.suffix != ".age":
                raise TransferRejected("preencrypted ciphertext path required")
            size = source.stat().st_size
            if size <= 100 or size > self.max_ciphertext_bytes:
                raise TransferRejected("ciphertext exceeds explicit byte cap")
            try:
                with source.open("rb") as stream:
                    return self._sdk("put_object", Bucket=self.bucket,
                                     Key=kw["key"], Body=stream,
                                     ContentLength=size, ContentType="application/octet-stream")
            except (OSError, ValueError):
                raise TransferRejected("encrypted source could not be read") from None

        if operation == "head-object" and self.role == "reader":
            key, version = self._read_key_version(kw, {"bucket", "key", "version_id"})
            return self._sdk("head_object", Bucket=self.bucket,
                             Key=key, VersionId=version)

        if operation == "get-object" and self.role == "reader":
            key, version = self._read_key_version(kw,
                                                   {"bucket", "key", "version_id", "output_path"})
            destination = kw["output_path"]
            if not isinstance(destination, Path) or destination.exists() or destination.is_symlink():
                raise TransferRejected("download destination must be a new file")
            response = self._sdk("get_object", Bucket=self.bucket,
                                 Key=key, VersionId=version)
            body = response.get("Body") if isinstance(response, dict) else None
            if (not body or not callable(getattr(body, "read", None))
                    or response.get("VersionId") != version):
                self._close(body)
                raise TransferRejected("unverified B2 version stream")
            total = 0
            try:
                with destination.open("xb") as output:
                    while True:
                        chunk = body.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        if not isinstance(chunk, bytes):
                            raise TransferRejected("unexpected B2 download payload type")
                        total += len(chunk)
                        if total > self.max_ciphertext_bytes:
                            raise TransferRejected("download exceeded explicit byte cap")
                        output.write(chunk)
            except Exception:
                destination.unlink(missing_ok=True)
                raise TransferRejected("B2 ciphertext download incomplete or over cap") from None
            finally:
                self._close(body)
            return {"VersionId": response["VersionId"]}

        # No delete, hide, public ACL update, bucket mutation or unversioned read.
        raise TransferRejected("operation unavailable to scoped B2 transport")

    @staticmethod
    def _read_key_version(kw: dict, names: set[str]) -> tuple[str, str]:
        if (set(kw) != names or not isinstance(kw["key"], str)
                or not KEY.fullmatch(kw["key"])):
            raise TransferRejected("unsafe B2 read request")
        version = kw["version_id"]
        if not isinstance(version, str) or not version or len(version) > 512:
            raise TransferRejected("explicit B2 object version required")
        if any(ord(c) < 33 or ord(c) > 126 for c in version):
            raise TransferRejected("invalid B2 object version")
        return kw["key"], version

    def _sdk(self, method: str, **args: Any) -> dict:
        try:
            response = getattr(self._client, method)(**args)
        except Exception:
            # Do not leak response bodies, request headers or credentials.
            raise TransferRejected("B2 S3 operation failed: " + method) from None
        if not isinstance(response, dict):
            raise TransferRejected("unexpected B2 S3 response")
        return response

    @staticmethod
    def _close(body: Any) -> None:
        close = getattr(body, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def independently_scoped_transports(writer: B2S3Transport, reader: B2S3Transport
                                    ) -> tuple[B2S3Transport, B2S3Transport]:
    """Reject accidentally shared SDK client objects; scopes need live DENY proof."""
    if (not isinstance(writer, B2S3Transport) or not isinstance(reader, B2S3Transport)
            or writer.role != "writer" or reader.role != "reader"
            or writer.client is reader.client or writer.bucket != reader.bucket
            or writer.region != reader.region or writer.endpoint != reader.endpoint):
        raise TransferRejected("separate B2 writer and reader clients are required")
    return writer, reader
