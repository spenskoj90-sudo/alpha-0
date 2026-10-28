"""Credential-free tests for the inert, strictly scoped B2 S3 adapter."""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from b2_s3_transport import B2S3Transport, independently_scoped_transports
from b2_versioned_transfer import TransferRejected

ENDPOINT = "https://s3.eu-central-003.backblazeb2.com"
REGION = "eu-central-003"
BUCKET = "sentinel-private-b2-test"
KEY = "sentinel/staging/sentinel-db-20261028T150000Z-" + "a" * 24 + ".pgdump.age"
VERSION = "4_z_synthetic_not_real"
OWNER = "synthetic-owner"
PAYLOAD = b"SYNTHETIC_AGE_CIPHERTEXT_NOT_REAL" * 10


class FakeS3:
    def __init__(self, state=None, region=REGION, endpoint=ENDPOINT):
        self.state = state if state is not None else {}
        self.meta = SimpleNamespace(endpoint_url=endpoint, region_name=region)
        self.calls = []

    def _call(self, method, **kwargs):
        self.calls.append((method, kwargs))

    def get_bucket_acl(self, **kwargs):
        self._call("get_bucket_acl", **kwargs)
        return {"Owner": {"ID": OWNER}, "Grants": [
            {"Permission": "FULL_CONTROL", "Grantee": {"Type": "CanonicalUser", "ID": OWNER}}]}

    def list_object_versions(self, **kwargs):
        self._call("list_object_versions", **kwargs)
        versions = []
        if "bytes" in self.state:
            versions = [{"Key": kwargs["Prefix"], "VersionId": VERSION,
                         "Size": len(self.state["bytes"])}]
        return {"IsTruncated": False, "Versions": versions, "DeleteMarkers": []}

    def put_object(self, **kwargs):
        self._call("put_object", **{k: v for k, v in kwargs.items() if k != "Body"})
        self.state["bytes"] = kwargs["Body"].read()
        return {"VersionId": VERSION}

    def head_object(self, **kwargs):
        self._call("head_object", **kwargs)
        return {"VersionId": VERSION, "ContentLength": len(self.state["bytes"])}

    def get_object(self, **kwargs):
        self._call("get_object", **kwargs)
        return {"VersionId": VERSION, "Body": io.BytesIO(self.state["bytes"])}


class B2S3TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "synthetic.age"
        self.source.write_bytes(PAYLOAD)
        self.output = self.root / "independent-read.age"
        state = {}
        self.writer_client = FakeS3(state)
        self.reader_client = FakeS3(state)
        self.writer = B2S3Transport(self.writer_client, role="writer", endpoint=ENDPOINT,
                                     region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)
        self.reader = B2S3Transport(self.reader_client, role="reader", endpoint=ENDPOINT,
                                     region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)

    def test_roundtrip_expected_s3_calls_and_version(self):
        writer, reader = independently_scoped_transports(self.writer, self.reader)
        acl = writer("get-bucket-acl", bucket=BUCKET)
        self.assertEqual(acl["Owner"]["ID"], OWNER)
        self.assertEqual(writer("list-object-versions", bucket=BUCKET, prefix=KEY, max_keys=10)["Versions"], [])
        written = writer("put-object", bucket=BUCKET, key=KEY, path=self.source)
        self.assertEqual(written["VersionId"], VERSION)
        self.assertEqual(reader("list-object-versions", bucket=BUCKET, prefix=KEY, max_keys=10)["Versions"][0]["VersionId"], VERSION)
        self.assertEqual(reader("head-object", bucket=BUCKET, key=KEY, version_id=VERSION)["ContentLength"], len(PAYLOAD))
        downloaded = reader("get-object", bucket=BUCKET, key=KEY, version_id=VERSION, output_path=self.output)
        self.assertEqual(downloaded["VersionId"], VERSION)
        self.assertEqual(self.output.read_bytes(), PAYLOAD)
        allowed = {"get_bucket_acl", "list_object_versions", "put_object", "head_object", "get_object"}
        self.assertTrue(all(k in allowed for c in (self.writer_client, self.reader_client) for k, _ in c.calls))
        put_args = [kw for method, kw in self.writer_client.calls if method == "put_object"][0]
        self.assertEqual(put_args["ContentLength"], len(PAYLOAD))
        self.assertNotIn("ACL", put_args)
        self.assertNotIn("Tagging", put_args)

    def test_writer_cannot_download_and_reader_cannot_upload(self):
        with self.assertRaises(TransferRejected):
            self.writer("get-object", bucket=BUCKET, key=KEY, version_id=VERSION, output_path=self.output)
        with self.assertRaises(TransferRejected):
            self.reader("put-object", bucket=BUCKET, key=KEY, path=self.source)
        self.assertFalse(self.writer_client.calls or self.reader_client.calls)

    def test_never_allow_delete_hide_public_acl_or_unversioned_get(self):
        for role in (self.writer, self.reader):
            for name in ("delete-object", "delete-objects", "put-bucket-acl", "put-object-acl", "get-object"):
                with self.subTest(role=role.role, name=name), self.assertRaises(TransferRejected):
                    role(name, bucket=BUCKET, key=KEY)
        self.assertFalse(self.writer_client.calls or self.reader_client.calls)

    def test_refuse_wrong_account_endpoint_or_region_before_sdk(self):
        for changed in (dict(endpoint="https://s3.us-west-004.backblazeb2.com"),
                        dict(region="us-west-004")):
            with self.assertRaises((ValueError, TransferRejected)):
                B2S3Transport(FakeS3(**changed), role="writer", endpoint=ENDPOINT,
                               region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)

    def test_refuse_same_client_object_even_with_separate_wrappers(self):
        fake = FakeS3()
        w = B2S3Transport(fake, role="writer", endpoint=ENDPOINT,
                           region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)
        r = B2S3Transport(fake, role="reader", endpoint=ENDPOINT,
                           region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)
        with self.assertRaises(TransferRejected):
            independently_scoped_transports(w, r)

    def test_refuse_cross_bucket_and_unscoped_listing(self):
        with self.assertRaises(TransferRejected):
            self.writer("put-object", bucket="other-bucket", key=KEY, path=self.source)
        for prefix, max_keys in (("sentinel/", 10), (KEY, 1000)):
            with self.assertRaises(TransferRejected):
                self.reader("list-object-versions", bucket=BUCKET, prefix=prefix, max_keys=max_keys)
        self.assertFalse(self.writer_client.calls or self.reader_client.calls)

    def test_refuse_bad_key_and_large_ciphertext_before_upload(self):
        with self.assertRaises(TransferRejected):
            self.writer("put-object", bucket=BUCKET, key="../unsafe", path=self.source)
        large = self.root / "large.age"
        large.write_bytes(b"Z" * 10001)
        with self.assertRaises(TransferRejected):
            self.writer("put-object", bucket=BUCKET, key=KEY, path=large)
        self.assertFalse(self.writer_client.calls)

    def test_version_required_before_head_and_get(self):
        for version in ("", "x\n", None):
            with self.assertRaises(TransferRejected):
                self.reader("head-object", bucket=BUCKET, key=KEY, version_id=version)
        self.assertFalse(self.reader_client.calls)

    def test_refuse_preexisting_destination_and_symlink(self):
        self.output.write_bytes(b"already exists")
        with self.assertRaises(TransferRejected):
            self.reader("get-object", bucket=BUCKET, key=KEY, version_id=VERSION, output_path=self.output)
        self.output.unlink()
        self.output.symlink_to(self.source)
        with self.assertRaises(TransferRejected):
            self.reader("get-object", bucket=BUCKET, key=KEY, version_id=VERSION, output_path=self.output)
        self.assertFalse(self.reader_client.calls)

    def test_download_byte_cap_does_not_leave_partial_file(self):
        self.writer_client.state["bytes"] = b"Z" * 10001
        with self.assertRaises(TransferRejected):
            self.reader("get-object", bucket=BUCKET, key=KEY, version_id=VERSION, output_path=self.output)
        self.assertFalse(self.output.exists())

    def test_legacy_r2_manual_job_explicitly_inert(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/offsite-db-backup.yml"
        self.assertIn("&& false", workflow.read_text())

    def test_remote_sdk_exception_is_scrubbed(self):
        class BadS3(FakeS3):
            def get_bucket_acl(self, **kwargs):
                raise RuntimeError("FAKE_TOKEN_MUST_NEVER_ESCAPE")
        writer = B2S3Transport(BadS3(), role="writer", endpoint=ENDPOINT,
                                 region=REGION, bucket=BUCKET, max_ciphertext_bytes=10000)
        with self.assertRaises(TransferRejected) as caught:
            writer("get-bucket-acl", bucket=BUCKET)
        self.assertNotIn("FAKE_TOKEN", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
