"""Synthetic path-race tests: no credentials, network, or real backup bytes."""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from b2_upload_snapshot import pinned_ciphertext_snapshot
from b2_versioned_transfer import TransferRejected

AGE = b"age-encryption.org/v1\n-> X25519 SYNTHETIC\n" + b"CIPHERTEXT_NOT_AGE" * 20
HASH = hashlib.sha256(AGE).hexdigest()


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "synthetic.age"
        self.path.write_bytes(AGE)

    def snap(self):
        return pinned_ciphertext_snapshot(self.path, 2048, HASH, len(AGE))

    def test_immutable_verified_snapshot_survives_path_mutation(self):
        frozen = self.snap()
        self.path.write_bytes(b"Z" * len(AGE))
        self.assertEqual(frozen, AGE)
        self.assertIsInstance(frozen, bytes)

    def test_reject_same_size_mutation(self):
        self.path.write_bytes(AGE[:-1] + b"X")
        with self.assertRaises(TransferRejected):
            self.snap()

    def test_reject_path_swap_to_symlink(self):
        target = self.root / "replacement.age"
        target.write_bytes(AGE)
        self.path.unlink()
        self.path.symlink_to(target)
        with self.assertRaises(TransferRejected):
            self.snap()

    def test_reject_mutation_between_parent_check_and_open(self):
        actual_open = os.open

        def mutate_then_open(path, flags, *args, **kw):
            self.path.write_bytes(AGE[:-1] + b"X")
            return actual_open(path, flags, *args, **kw)

        with mock.patch("b2_upload_snapshot.os.open", side_effect=mutate_then_open):
            with self.assertRaises(TransferRejected):
                self.snap()

    def test_reject_non_private_staging_parent(self):
        self.root.chmod(0o755)
        with self.assertRaises(TransferRejected):
            self.snap()

    def test_reject_fifo_without_blocking(self):
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises(TransferRejected):
            self.snap()

    def test_reject_plaintext_even_with_matching_sha(self):
        plaintext = b"UNENCRYPTED_PG_DUMP" * 20
        self.path.write_bytes(plaintext)
        with self.assertRaisesRegex(TransferRejected, "binary age v1 header"):
            pinned_ciphertext_snapshot(
                self.path, 2048, hashlib.sha256(plaintext).hexdigest(), len(plaintext))

    def test_reject_wrong_length_and_cap(self):
        for length, cap in ((len(AGE) - 1, 2048), (len(AGE), len(AGE) - 1)):
            with self.subTest(length=length, cap=cap), self.assertRaises(TransferRejected):
                pinned_ciphertext_snapshot(self.path, cap, HASH, length)


if __name__ == "__main__":
    unittest.main(verbosity=2)
