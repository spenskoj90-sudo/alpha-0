"""Purely synthetic verified ciphertext staging and no-clobber tests."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from b2_atomic_download import DownloadRejected, publish_verified_ciphertext

DATA = b"SYNTHETIC_AGE_CIPHERTEXT_NEVER_REAL" * 16
SHA = hashlib.sha256(DATA).hexdigest()


class TestAtomicDownload(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "independent.age"

    def download(self, stream=None, **overrides):
        kw = dict(body=stream if stream is not None else io.BytesIO(DATA),
                  destination=self.path, expected_sha256=SHA,
                  expected_bytes=len(DATA), max_ciphertext_bytes=4096)
        kw.update(overrides)
        return publish_verified_ciphertext(**kw)

    def test_publish_exact_digest_and_size(self):
        self.assertEqual(self.download(), {"sha256": SHA, "size_bytes": len(DATA)})
        self.assertEqual(self.path.read_bytes(), DATA)
        self.assertFalse(list(self.root.glob("*.part")))
        self.assertFalse(list(self.root.glob(".*.part")))

    def test_reject_corrupted_digest_without_publishing(self):
        with self.assertRaises(DownloadRejected):
            self.download(stream=io.BytesIO(DATA[:-1] + b"X"))
        self.assertFalse(self.path.exists())
        self.assertFalse(list(self.root.glob(".*.part")))

    def test_reject_short_stream(self):
        with self.assertRaises(DownloadRejected):
            self.download(stream=io.BytesIO(DATA[:-1]))
        self.assertFalse(self.path.exists())

    def test_reject_oversized_stream(self):
        with self.assertRaises(DownloadRejected):
            self.download(stream=io.BytesIO(DATA + b"X"))
        self.assertFalse(self.path.exists())

    def test_cannot_overwrite_existing_destination(self):
        self.path.write_bytes(b"somebody-else")
        with self.assertRaises(DownloadRejected):
            self.download()
        self.assertEqual(self.path.read_bytes(), b"somebody-else")

    def test_cannot_overwrite_destination_created_midstream(self):
        dest = self.path
        class RacingStream(io.BytesIO):
            def read(self, n=-1):
                if self.tell() == len(DATA):
                    dest.write_bytes(b"racing-owner")
                return super().read(n)
        with self.assertRaises(DownloadRejected):
            self.download(stream=RacingStream(DATA))
        self.assertEqual(self.path.read_bytes(), b"racing-owner")
        self.assertFalse(list(self.root.glob(".*.part")))

    def test_stream_exception_leaves_no_destination(self):
        class BrokenStream(io.BytesIO):
            def read(self, n=-1):
                raise OSError("fake response with secret must not leak")
        with self.assertRaisesRegex(DownloadRejected, "publication failed") as e:
            self.download(stream=BrokenStream(DATA))
        self.assertNotIn("secret", str(e.exception))
        self.assertFalse(self.path.exists())
        self.assertFalse(list(self.root.glob(".*.part")))

    def test_wrong_sha_or_size_rejected(self):
        for override in ({"expected_sha256": "z" * 64},
                         {"expected_sha256": "0" * 64},
                         {"expected_bytes": True},
                         {"expected_bytes": 5000},
                         {"expected_bytes": len(DATA) - 1}):
            with self.subTest(override=override), self.assertRaises(DownloadRejected):
                self.download(**override)
            self.assertFalse(self.path.exists())

    def test_symlink_or_shared_dir_refused(self):
        link = self.root / "link.age"
        link.symlink_to(self.root / "other.age")
        with self.assertRaises(DownloadRejected):
            self.download(destination=link)
        shared = self.root / "shared"
        shared.mkdir(mode=0o777)
        shared.chmod(0o777)
        with self.assertRaises(DownloadRejected):
            self.download(destination=shared / "new.age")

    def test_no_non_age_path(self):
        with self.assertRaises(DownloadRejected):
            self.download(destination=self.root / "dump.sql")


if __name__ == "__main__":
    unittest.main()
