import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from b2_private_journal import PrivatePackageJournal, JournalRejected
from b2_versioned_transfer import Receipt

KEY_A='sentinel/staging/sentinel-db-20261108T000000Z-'+'a'*24+'.pgdump.age'
KEY_B='sentinel/staging/sentinel-db-20261108T000000Z-'+'b'*24+'.pgdump.age'
PLAN={'event':'planned','parts':{'database':{'key':KEY_A,'sha256':'a'*64,'size_bytes':120},'roles':{'key':KEY_B,'sha256':'b'*64,'size_bytes':130}}}

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.path=self.root/'private.jsonl'
    def test_plan_and_version_receipts_are_readable_and_private(self):
        with PrivatePackageJournal(self.path) as journal:
            journal(PLAN)
            journal({'event':'verified','part':'database','receipt':Receipt(KEY_A,'version-a','a'*64,120)})
            journal({'event':'verified','part':'roles','receipt':Receipt(KEY_B,'version-b','b'*64,130)})
        rows=[json.loads(s) for s in self.path.read_text().splitlines()]
        self.assertEqual([r['event'] for r in rows],['planned','verified','verified'])
        self.assertEqual(rows[2]['receipt']['version_id'],'version-b')
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_fsync_failure_poisoned_journal_cannot_continue(self):
        with PrivatePackageJournal(self.path) as journal:
            with patch('b2_private_journal.os.fsync',side_effect=OSError('synthetic-disk-failure')):
                with self.assertRaises(JournalRejected): journal(PLAN)
            with self.assertRaises(JournalRejected): journal(PLAN)
        self.assertEqual(len(self.path.read_text().splitlines()),1)
    def test_existing_file_is_not_overwritten(self):
        self.path.write_text('preserve')
        with self.assertRaises(JournalRejected): PrivatePackageJournal(self.path)
        self.assertEqual(self.path.read_text(),'preserve')
    def test_nonprivate_parent_is_denied(self):
        self.root.chmod(0o755)
        with self.assertRaises(JournalRejected): PrivatePackageJournal(self.path)
        self.assertFalse(self.path.exists())
    def test_verified_cannot_precede_plan(self):
        with PrivatePackageJournal(self.path) as journal:
            with self.assertRaises(JournalRejected): journal({'event':'verified','part':'database','receipt':Receipt(KEY_A,'v','a'*64,120)})
        self.assertEqual(self.path.read_bytes(),b'')
    def test_unbound_receipt_is_rejected(self):
        with PrivatePackageJournal(self.path) as journal:
            journal(PLAN)
            with self.assertRaises(JournalRejected): journal({'event':'verified','part':'roles','receipt':Receipt(KEY_A,'v','b'*64,130)})
        self.assertEqual(len(self.path.read_text().splitlines()),1)
    def test_duplicate_plan_is_denied(self):
        with PrivatePackageJournal(self.path) as journal:
            journal(PLAN)
            with self.assertRaises(JournalRejected): journal(PLAN)
        self.assertEqual(len(self.path.read_text().splitlines()),1)
    def test_extra_fields_cannot_be_saved(self):
        with PrivatePackageJournal(self.path) as journal:
            with self.assertRaises(JournalRejected): journal(dict(PLAN,credential='synthetic-secret'))
        self.assertEqual(self.path.read_bytes(),b'')

if __name__=='__main__': unittest.main()
