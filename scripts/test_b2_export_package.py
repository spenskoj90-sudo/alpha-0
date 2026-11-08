"""Synthetic SDK boundary tests; no real B2 authorizations or ciphertext."""
import hashlib
import io
import json
from b2_private_journal import PrivatePackageJournal
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from b2_export_package import transfer_export_package, PackageRejected
from b2_s3_transport import B2S3Transport
from pg18_encrypted_export import EncryptedPart

ENDPOINT='https://s3.eu-central-003.backblazeb2.com'
REGION='eu-central-003'; BUCKET='synthetic-private-bucket'; OWNER='synthetic-owner'

class Client:
    def __init__(self,state,role):
        self.meta=SimpleNamespace(endpoint_url=ENDPOINT,region_name=REGION)
        self.state=state; self.role=role
    def get_bucket_acl(self,**kw):
        return {'Owner':{'ID':OWNER},'Grants':[{'Permission':'FULL_CONTROL','Grantee':{'Type':'CanonicalUser','ID':OWNER}}]}
    def list_object_versions(self,**kw):
        key=kw['Prefix']; data=self.state.get(key)
        return {'IsTruncated':False,'DeleteMarkers':[], 'Versions':[] if data is None else [{'Key':key,'VersionId':'synthetic-version','Size':len(data)}]}
    def put_object(self,**kw):
        if self.state.get('fail-second') and sum(isinstance(v,bytes) for v in self.state.values())==1:
            raise RuntimeError('synthetic private diagnostic')
        self.state[kw['Key']]=kw['Body']; return {'VersionId':'synthetic-version'}
    def head_object(self,**kw):
        return {'VersionId':'synthetic-version','ContentLength':len(self.state[kw['Key']])}
    def get_object(self,**kw):
        return {'VersionId':'synthetic-version','Body':io.BytesIO(self.state[kw['Key']])}

class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.state={}; self.events=[]; self.parts={}
        for name in ('database','roles'):
            path=self.root/(name+'.age'); payload=b'age-encryption.org/v1\n-> synthetic\n'+name.encode()*100
            path.write_bytes(payload)
            self.parts[name]=EncryptedPart(path,hashlib.sha256(payload).hexdigest(),len(payload))
        def transport(role):
            return B2S3Transport(Client(self.state,role),role=role,endpoint=ENDPOINT,
                region=REGION,bucket=BUCKET,max_ciphertext_bytes=10000)
        self.writer=transport('writer'); self.reader=transport('reader')
    def go(self,**kw):
        args=dict(parts=self.parts,writer=self.writer,reader=self.reader,expected_owner=OWNER,
                  max_total_bytes=10000,journal=lambda event:self.events.append(event))
        args.update(kw); return transfer_export_package(**args)
    def test_both_parts_have_distinct_versioned_receipts(self):
        receipts=self.go()
        self.assertEqual(set(receipts),{'database','roles'})
        self.assertNotEqual(receipts['database'].key,receipts['roles'].key)
        for name,receipt in receipts.items():
            self.assertEqual(self.state[receipt.key],self.parts[name].path.read_bytes())
            self.assertEqual(receipt.sha256,self.parts[name].sha256)
        self.assertEqual([e['event'] for e in self.events],['planned','verified','verified'])
        self.assertEqual(set(self.events[0]['parts']),{'database','roles'})
    def test_real_private_journal_binds_both_completed_versions(self):
        path=self.root/'attempt.jsonl'
        with PrivatePackageJournal(path) as journal:
            receipts=self.go(journal=journal)
        rows=[json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['parts']['roles']['key'],receipts['roles'].key)
        self.assertEqual(rows[2]['receipt']['version_id'],'synthetic-version')
    def test_missing_roles_rejected_before_network(self):
        del self.parts['roles']
        with self.assertRaises(PackageRejected): self.go()
        self.assertEqual(self.state,{}); self.assertEqual(self.events,[])
    def test_changed_roles_rejected_before_any_upload(self):
        self.parts['roles'].path.write_bytes(b'age-encryption.org/v1\n-> corrupted\n'+b'X'*500)
        with self.assertRaises(PackageRejected): self.go()
        self.assertEqual(self.state,{})
    def test_total_cap_rejects_before_any_upload(self):
        with self.assertRaises(PackageRejected): self.go(max_total_bytes=800)
        self.assertEqual(self.state,{})
    def test_failed_plan_journal_prevents_all_uploads(self):
        def failed(_): raise OSError('private-path')
        with self.assertRaises(PackageRejected): self.go(journal=failed)
        self.assertEqual(self.state,{})
    def test_second_upload_failure_keeps_first_and_plan_for_recovery(self):
        self.state['fail-second']=True
        with self.assertRaises(PackageRejected) as caught: self.go()
        self.assertEqual(sum(isinstance(v,bytes) for v in self.state.values()),1)
        self.assertEqual([e['event'] for e in self.events],['planned','verified'])
        self.assertNotIn('synthetic private diagnostic',str(caught.exception))
    def test_same_client_rejected_before_network(self):
        with self.assertRaises(PackageRejected): self.go(reader=self.writer)
        self.assertEqual(self.state,{})

if __name__=='__main__': unittest.main()
