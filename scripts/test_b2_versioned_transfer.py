"""Offline safety tests for the inert B2 versioned ciphertext transport."""
from __future__ import annotations

import pathlib
import tempfile
import unittest
from datetime import datetime, timezone

from b2_versioned_transfer import (
    TransferRejected, new_unique_key, stage_and_verify, MAX_STAGE_BYTES
)

ENDPOINT = "https://s3.eu-central-003.backblazeb2.com"
REGION = "eu-central-003"
BUCKET = "sentinel-private-b2-test"
OWNER = "synthetic-owner-not-real"
VERSION = "4_z_synthetic_version"
KEY = new_unique_key(datetime(2026, 10, 28, tzinfo=timezone.utc), "a" * 24)
PAYLOAD = b"TEST_ENCRYPTED_CIPHERTEXT_NOT_A_REAL_DATABASE" * 8


class FakeB2:
    def __init__(self, state, role):
        self.state, self.role, self.calls = state, role, []
    def __call__(self, operation, **args):
        self.calls.append(operation)
        if operation == "get-bucket-acl":
            return self.state.get("acl", {
                "Owner": {"ID": OWNER}, "Grants": [
                    {"Grantee": {"Type": "CanonicalUser", "ID": OWNER},
                     "Permission": "FULL_CONTROL"}]})
        if operation == "list-object-versions":
            versions = []
            if "object" in self.state:
                versions = [{"Key": args["prefix"], "VersionId": VERSION,
                             "Size": len(self.state["object"])}]
            return {"IsTruncated": self.state.get("truncated", False),
                    "Versions": versions,
                    "DeleteMarkers": self.state.get("markers", [])}
        if operation == "put-object":
            if self.role != "writer":
                raise AssertionError("reader cannot upload")
            self.state["object"] = args["path"].read_bytes()
            return {"VersionId": self.state.get("upload_version", VERSION)}
        if operation == "head-object":
            return {"VersionId": self.state.get("head_version", VERSION),
                    "ContentLength": len(self.state.get("object", b""))}
        if operation == "get-object":
            payload = self.state["object"]
            if self.state.get("corrupt"):
                payload = payload[:-1] + bytes([payload[-1] ^ 1])
            args["output_path"].write_bytes(payload)
            return {"VersionId": self.state.get("download_version", VERSION)}
        raise AssertionError(f"unexpected or destructive S3 operation: {operation}")


class B2VersionedTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-b2-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.source = self.root / "synthetic.age"
        self.source.write_bytes(PAYLOAD)
        self.download = self.root / "download.age"
        self.state = {}
        self.writer = FakeB2(self.state, "writer")
        self.reader = FakeB2(self.state, "reader")

    def go(self, **kw):
        args = dict(endpoint=ENDPOINT, region=REGION, bucket=BUCKET,
                    expected_owner=OWNER, key=KEY, ciphertext=self.source,
                    max_ciphertext_bytes=MAX_STAGE_BYTES, uploader=self.writer,
                    reader=self.reader, download_path=self.download)
        args.update(kw)
        return stage_and_verify(**args)

    def test_roundtrip_version_specific_sha(self):
        receipt = self.go()
        self.assertEqual(receipt.version_id, VERSION)
        self.assertEqual(receipt.size_bytes, len(PAYLOAD))
        self.assertEqual(self.download.read_bytes(), PAYLOAD)
        self.assertEqual(self.reader.calls, [
            "list-object-versions", "head-object", "get-object"])
        self.assertTrue(all(x not in self.writer.calls + self.reader.calls
                            for x in ("delete-object", "delete-objects", "put-bucket-acl")))

    def test_wrong_owner_fails_before_upload(self):
        with self.assertRaises(TransferRejected):
            self.go(expected_owner="wrong-owner")
        self.assertNotIn("put-object", self.writer.calls)

    def test_public_grant_fails_closed(self):
        self.state["acl"] = {"Owner": {"ID": OWNER}, "Grants": [
            {"Grantee": {"Type": "Group", "URI": "AllUsers"}, "Permission": "READ"}]}
        with self.assertRaises(TransferRejected):
            self.go()
        self.assertNotIn("put-object", self.writer.calls)

    def test_preexisting_exact_key_rejected(self):
        self.state["object"] = PAYLOAD
        with self.assertRaises(TransferRejected):
            self.go()
        self.assertNotIn("put-object", self.writer.calls)

    def test_truncated_listing_rejected(self):
        self.state["truncated"] = True
        with self.assertRaises(TransferRejected):
            self.go()
        self.assertNotIn("put-object", self.writer.calls)

    def test_missing_version_after_write_fails(self):
        self.state["upload_version"] = None
        with self.assertRaises(TransferRejected):
            self.go()

    def test_head_version_mismatch_fails(self):
        self.state["head_version"] = "other-version"
        with self.assertRaises(TransferRejected):
            self.go()

    def test_download_version_mismatch_fails(self):
        self.state["download_version"] = "other-version"
        with self.assertRaises(TransferRejected):
            self.go()

    def test_tampered_download_fails_sha(self):
        self.state["corrupt"] = True
        with self.assertRaises(TransferRejected):
            self.go()

    def test_hide_marker_rejected(self):
        self.state["markers"] = [{"Key": KEY, "VersionId": "hidden"}]
        with self.assertRaises(TransferRejected):
            self.go()

    def test_no_standing_identity_reuse(self):
        with self.assertRaises(TransferRejected):
            self.go(reader=self.writer)
        self.assertEqual(self.writer.calls, [])

    def test_too_small_ciphertext_refused(self):
        self.source.write_bytes(b"x" * 90)
        with self.assertRaises(TransferRejected):
            self.go()
        self.assertEqual(self.writer.calls, [])

    def test_cap_refused_before_remote(self):
        with self.assertRaises(TransferRejected):
            self.go(max_ciphertext_bytes=MAX_STAGE_BYTES + 1)
        self.assertEqual(self.writer.calls, [])

    def test_wrong_region_refused_before_remote(self):
        with self.assertRaises(ValueError):
            self.go(region="us-west-004")
        self.assertEqual(self.writer.calls, [])

    def test_bad_namespace_refused_before_remote(self):
        with self.assertRaises(TransferRejected):
            self.go(key="../../secrets")
        self.assertEqual(self.writer.calls, [])

    def test_existing_download_refused(self):
        self.download.write_bytes(b"old")
        with self.assertRaises(TransferRejected):
            self.go()
        self.assertEqual(self.writer.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
