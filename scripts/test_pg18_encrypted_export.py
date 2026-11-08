"""Process-boundary tests: synthetic commands, never real DB/cloud proof."""
import os
from pathlib import Path
import tempfile
import unittest
from pg18_encrypted_export import encrypted_export, ExportRejected

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'bin'; self.bin.mkdir()
        self.out = self.root / 'out'; self.out.mkdir(mode=0o700)
        for name in ('pg_dump', 'pg_dumpall', 'age'):
            p = self.bin / name
            p.write_text('''#!/usr/bin/env python3
import os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
if '--version' in sys.argv:
 print(name + (' v1.2.1' if name == 'age' else ' (PostgreSQL) '+os.environ.get('PG_FAKE_VERSION','18.1'))); sys.exit(0)
if name == 'age':
 data = sys.stdin.buffer.read()
 if os.environ.get('FAIL_AGE'): sys.exit(3)
 sys.stdout.buffer.write(b'age-encryption.org/v1\\n-> synthetic\\n' + data)
else:
 with open(os.environ['CALL_LOG'], 'a') as f: f.write(name + ' ' + ' '.join(sys.argv[1:]) + '\\n')
 if os.environ.get('STALL_DUMP') == name:
  import time; time.sleep(10)
 if os.environ.get('FAIL_DUMP') == name:
  print('private-source-secret',file=sys.stderr); sys.exit(4)
 sys.stdout.buffer.write(b'synthetic-' + name.encode()*20)
''')
            p.chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.bin)+':'+os.environ['PATH'], CALL_LOG=str(self.root/'calls'))
        self.service = self.root/'service.conf'
        self.service.write_text('[source]\nhost=synthetic.invalid\n'); self.service.chmod(0o600)
    def run_export(self):
        return encrypted_export(output=self.out, service_file=self.service,
            service='source', recipient='age1'+'q'*58, max_bytes=4096, env=self.env)
    def test_full_archive_and_passwordless_roles_are_both_encrypted(self):
        result = self.run_export()
        self.assertEqual(set(result), {'database', 'roles'})
        calls = (self.root/'calls').read_text()
        self.assertIn('pg_dump --format=custom --create', calls)
        self.assertNotIn('--no-owner', calls); self.assertNotIn('--no-acl', calls)
        self.assertIn('pg_dumpall --roles-only --no-role-passwords', calls)
        self.assertNotIn('--dbname', calls)
        for item in result.values():
            self.assertTrue(item.path.read_bytes().startswith(b'age-encryption.org/v1\n'))
            self.assertEqual(item.path.stat().st_mode & 0o777, 0o600)
    def test_dump_failure_leaves_no_partial_package(self):
        self.env['FAIL_DUMP']='pg_dump'
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertEqual(list(self.out.iterdir()), [])
    def test_second_stream_failure_removes_first_ciphertext(self):
        self.env['FAIL_DUMP']='pg_dumpall'
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertEqual(list(self.out.iterdir()), [])
    def test_encryptor_failure_leaves_no_partial_package(self):
        self.env['FAIL_AGE']='1'
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertEqual(list(self.out.iterdir()), [])
    def test_byte_cap_aborts_before_publishing(self):
        self.env['FAIL_DUMP']=''
        with self.assertRaises(ExportRejected):
            encrypted_export(output=self.out, service_file=self.service, service='source',
                recipient='age1'+'q'*58, max_bytes=110, env=self.env)
        self.assertEqual(list(self.out.iterdir()), [])
    def test_nonprivate_service_rejected_before_process(self):
        self.service.chmod(0o644)
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertFalse((self.root/'calls').exists())
    def test_wrong_client_major_is_rejected_before_dump(self):
        # Test override is not PG-prefixed, because production clears PG overrides.
        p = self.bin/'pg_dump'
        p.write_text(p.read_text().replace("'18.1'", "'17.6'"))
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertFalse((self.root/'calls').exists())
    def test_stalled_producer_is_killed_and_partial_removed(self):
        self.env['STALL_DUMP']='pg_dump'
        with self.assertRaises(ExportRejected):
            encrypted_export(output=self.out, service_file=self.service, service='source',
                recipient='age1'+'q'*58, max_bytes=4096, env=self.env, timeout=1)
        self.assertEqual(list(self.out.iterdir()), [])
    def test_subprocess_error_never_echoes_private_diagnostic(self):
        self.env['FAIL_DUMP']='pg_dump'
        with self.assertRaises(ExportRejected) as caught: self.run_export()
        self.assertNotIn('private-source-secret', str(caught.exception))
    def test_existing_output_is_never_overwritten(self):
        (self.out/'existing').write_bytes(b'keep')
        with self.assertRaises(ExportRejected): self.run_export()
        self.assertEqual((self.out/'existing').read_bytes(),b'keep')

if __name__ == '__main__': unittest.main()
