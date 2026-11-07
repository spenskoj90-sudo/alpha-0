"""SYNTHETIC provenance/DEX fixtures; no protected signer or real APK acceptance."""
import base64
import copy
import io
import json
import struct
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import signed_feed_candidate as feed
import release_lineage as play


def dex(fields):
    # Minimal encoded DEX tables for parser tests, not an executable APK.
    strings = ['Lcom/alpha0/app/BuildConfig;'] + list(fields) + [v for v in fields.values() if isinstance(v, str)]
    def leb(n):
        out = bytearray()
        while n >= 128:
            out.append((n & 127) | 128); n >>= 7
        return bytes(out + bytes([n]))
    raw = bytearray(112 + 4 * len(strings) + 4 + 8 * len(fields) + 32)
    raw[:8] = b'dex\n035\0'
    def put(offset, value): struct.pack_into('<I', raw, offset, value)
    string_offset = 112
    type_offset = string_offset + 4 * len(strings)
    field_offset = type_offset + 4
    class_offset = field_offset + 8 * len(fields)
    for offset, value in [(40, 0x12345678), (56, len(strings)), (60, string_offset),
            (64, 1), (68, type_offset), (80, len(fields)), (84, field_offset), (96, 1), (100, class_offset)]:
        put(offset, value)
    for i, value in enumerate(strings):
        put(string_offset + i * 4, len(raw)); raw.extend(leb(len(value)) + value.encode() + b'\0')
    for i, key in enumerate(fields): put(field_offset + i * 8 + 4, strings.index(key))
    put(class_offset + 24, len(raw))
    raw.extend(leb(len(fields)) + b'\0\0\0')
    for i in range(len(fields)): raw.extend(leb(0 if i == 0 else 1) + leb(0x19))
    put(class_offset + 28, len(raw)); raw.extend(leb(len(fields)))
    for value in fields.values():
        if type(value) is bool: raw.append(0x3f if value else 0x1f)
        elif type(value) is int: raw.extend(b'\x64' + value.to_bytes(4, 'little'))
        else:
            index = strings.index(value)
            raw.extend(b'\x17' + bytes([index]))
    put(32, len(raw))
    return bytes(raw)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        key = self.root / 'ephemeral.pem'
        subprocess.run(['openssl', 'ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', str(key)], check=True)
        public = subprocess.check_output(['openssl', 'pkey', '-in', str(key), '-pubout', '-outform', 'DER'])
        self.policy = dict(schema='sentinel.signed-feed-approval.v1', status='APPROVED',
            channel='signed_feed', package='com.alpha0.app', signer=feed.APPROVED_SIGNER,
            apiBaseUrl='https://core.example.org', vkClientId='123', googleClientId='123-ci.apps.googleusercontent.com', feedUrl='https://example.org/android/feed.txt', verifyingKey=base64.b64encode(public).decode(),
            highestIssuedVersionCode=10007, baselineSourceSha='a'*40, baselineApkSha256='b'*64, reviewIssue=532)
        self.binding = dict(schema=feed.BINDING_SCHEMA, repository=feed.REPOSITORY, sourceSha='c'*40,
            sourceRef='refs/heads/main', channel='signed_feed', distribution='non_play', policy=self.policy, versionCode=10008)
        self.fields = dict(APPLICATION_ID='com.alpha0.app', DEBUG=False, VERSION_CODE=10008,
            SENTINEL_SOURCE_SHA='c'*40, SENTINEL_DISTRIBUTION_CHANNEL='signed_feed',
            SENTINEL_API_BASE_URL=self.policy['apiBaseUrl'], SENTINEL_API_FALLBACK_BASE_URL='',
            SENTINEL_GOOGLE_CLIENT_ID=self.policy['googleClientId'], SENTINEL_AUTH_CALLBACK_SCHEME='com.alpha0.app.auth', SENTINEL_VK_REDIRECT_URI='vk123://vk.ru/blank.html',
            SENTINEL_UPDATE_FEED_URL=self.policy['feedUrl'], SENTINEL_UPDATE_FEED_VERIFYING_KEY=self.policy['verifyingKey'])
        self.apk = self.root / feed.APK
        self.write_apk()
        with zipfile.ZipFile(self.apk) as z:
            self.binding['compiledPayloadSha256'] = feed.digest(feed.canonical({n:feed.digest(z.read(n)) for n in z.namelist()}))
        self.badging = "package: name='com.alpha0.app' versionCode='10008'\n"
        self.permissions = "uses-permission: name='android.permission.REQUEST_INSTALL_PACKAGES'\n"
        self.signature = 'Verified using v2 scheme (APK Signature Scheme v2): true\nSigner #1 certificate SHA-256 digest: '+feed.APPROVED_SIGNER+'\n'
        self.real_tool = feed.tool
        self.mock = patch.object(feed, 'tool', side_effect=self.tool); self.mock.start(); self.addCleanup(self.mock.stop)
    def write_apk(self):
        with zipfile.ZipFile(self.apk, 'w') as z: z.writestr('classes.dex', dex(self.fields))
    def tool(self, args, **kw):
        if args[0] == 'aapt2': return (self.permissions if args[2] == 'permissions' else self.badging).encode()
        if args[0] == 'apksigner': return self.signature.encode()
        return self.real_tool(args, **kw)
    def inspect(self): return feed.inspect(self.apk, self.binding, 'aapt2', 'apksigner')
    def test_workflow_presecret_separation(self):
        workflow = Path('.github/workflows/signed-feed-candidate.yml').read_text()
        self.assertLess(workflow.index('verify-compiled'), workflow.index('secrets.'))
        self.assertLess(workflow.index('bind-compiled'), workflow.index('environment: sentinel-release-signing'))
        self.assertIn('--v2-signing-enabled true --v3-signing-enabled true', workflow)
        self.assertNotIn('assembleRelease', workflow)
        self.assertNotIn('sentinel-release-candidate-', workflow)
        self.assertNotIn('inputs.api_base_url', workflow)
        self.assertNotIn('inputs.vk_client_id', workflow)
        self.assertIn('["apiBaseUrl"]', workflow)
        self.assertIn('["vkClientId"]', workflow)
        self.assertIn('needs: presecret', workflow)
        self.assertIn('needs: signed-feed', workflow)
        self.assertNotIn('contents: write', workflow)
        producer = Path('scripts/signed_update_feed_release.py').read_text()
        self.assertIn('candidate-source-sha', producer)
        self.assertIn('candidate-run-id', producer)
        self.assertNotIn('"expected-apk-sha256"', producer)
    def test_presecret_payload_is_mandatory(self):
        self.binding.pop('compiledPayloadSha256')
        with self.assertRaises(ValueError): self.inspect()
    def test_approved_but_foreign_public_pin_rejects_compiled_apk(self):
        key = self.root / 'other.pem'
        subprocess.run(['openssl','ecparam','-name','prime256v1','-genkey','-noout','-out',str(key)],check=True)
        public = subprocess.check_output(['openssl','pkey','-in',str(key),'-pubout','-outform','DER'])
        self.policy['verifyingKey'] = base64.b64encode(public).decode()
        with self.assertRaises(ValueError): self.inspect()
    def test_unsigned_presecret_is_never_a_release_candidate(self):
        self.signature = 'untrusted presecret signer'
        self.assertEqual(10008, feed.inspect(self.apk,self.binding,'aapt2','apksigner',unsigned=True)['versionCode'])
        with self.assertRaises(ValueError): self.inspect()
    def test_typed_dex_and_candidate(self):
        self.assertEqual([self.fields], feed.dex_constants(dex(self.fields)))
        self.assertEqual(feed.digest(self.apk.read_bytes()), self.inspect()['apkSha256'])
    def test_compiled_field_substitutions(self):
        for key in self.fields:
            with self.subTest(key=key):
                previous = self.fields[key]
                self.fields[key] = True if key == 'DEBUG' else 10007 if key == 'VERSION_CODE' else 'wrong'
                self.write_apk()
                with self.assertRaises(ValueError): self.inspect()
                self.fields[key] = previous
    def test_bad_metadata(self):
        for bad in ["package: name='other' versionCode='10008'", "package: name='com.alpha0.app' versionCode='10007'", self.badging+'application-debuggable\n']:
            with self.subTest(bad=bad):
                self.badging = bad
                with self.assertRaises(ValueError): self.inspect()
    def test_installer_permission(self):
        self.permissions = ''
        with self.assertRaises(ValueError): self.inspect()
    def test_sdk37_modern_certificate_report(self):
        self.signature = self.signature.replace('Signer #1', 'V2 Signer:')
        self.assertEqual(10008, self.inspect()['versionCode'])
        self.signature += 'V3 Signer: certificate SHA-256 digest: '+feed.APPROVED_SIGNER+'\n'
        self.assertEqual(10008, self.inspect()['versionCode'])
    def test_signer_and_v1(self):
        for report in [self.signature.replace(feed.APPROVED_SIGNER, '0'*64), self.signature.replace(': true', ': false'), self.signature+self.signature.replace('Signer #1', 'Signer #2')]:
            with self.subTest(report=report):
                self.signature = report
                with self.assertRaises(ValueError): self.inspect()
    def test_policy_denials(self):
        for key, value in [('googleClientId','https://attacker.invalid'), ('apiBaseUrl','http://core.example.org'), ('apiBaseUrl','https://core.example.org/path'), ('vkClientId','01'), ('status','PENDING'), ('channel','play'), ('verifyingKey',''), ('feedUrl','http://example.org/feed'), ('highestIssuedVersionCode',10006)]:
            policy = dict(self.policy); policy[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): feed.approval(policy)
    def test_binding_alias(self):
        for key, value in [('schema',play.PRESECRET_SCHEMA), ('channel','play'), ('distribution','play')]:
            binding = dict(self.binding); binding[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): feed.inspect(self.apk,binding,'aapt2','apksigner')
    def test_duplicate_json(self):
        with self.assertRaises(ValueError): feed.document('{"channel":"signed_feed","channel":"play"}')
    def test_play_reader_cannot_read_nonplay(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for name in feed.MEMBERS: z.writestr(name,b'synthetic')
        with self.assertRaises(ValueError): play._read_zip_exact(stream.getvalue(), {play.APK_FILE,play.CANDIDATE_FILE,play.PRESECRET_FILE})
    def test_play_publication_files_unchanged(self):
        # Baseline ba77d291: explicit byte contracts, independent of clone depth.
        expected = {'.github/workflows/release-candidate.yml': '8f959bfd667fabed6994d3ea6306b93e343820f6fc19727a4295fa26593b0090', '.github/workflows/release.yml': '83497db97dfdd46940356ac282918fa3da06288fbc2108c27a69bea6473d5437', '.github/workflows/final-release-acceptance.yml': '3bc59fff50caba5b17a93b1264c3f0eb4c1e489841fb50111c4ee2a99491f5e2', 'scripts/release_lineage.py': '249a43cf0722119253c881e8a51c2a52b5ccdabc677633ac4e23b82fd2510f95', 'scripts/final_release_acceptance.py': '916429a54ffb8dfec74518f6bff5b9255a1ca39280a866698837845f414e2701'}
        for filename, sha256 in expected.items():
            self.assertEqual(sha256, feed.digest(Path(filename).read_bytes()), filename)
    def setup_fetch(self):
        candidate = self.inspect()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            z.writestr(feed.APK,self.apk.read_bytes()); z.writestr(feed.BINDING,feed.canonical(self.binding)); z.writestr(feed.CANDIDATE,feed.canonical(candidate))
        archive=stream.getvalue()
        run=dict(head_sha='c'*40, head_branch='main',event='workflow_dispatch',path=feed.WORKFLOW,name=feed.WORKFLOW_NAME,status='completed',conclusion='success')
        artifact=dict(id=9,name='sentinel-signed-feed-candidate-'+'c'*40,expired=False,digest='sha256:'+feed.digest(archive),size_in_bytes=len(archive),workflow_run=dict(id=7,head_sha='c'*40))
        return candidate,archive,run,artifact
    def fetch(self, archive, run, artifact, attestor):
        def api(endpoint): return {'artifacts':[artifact]} if '/artifacts?' in endpoint else run
        with patch.object(feed,'approved_source',return_value=self.policy), patch.object(feed,'presecret',return_value={k:v for k,v in self.binding.items() if k != 'compiledPayloadSha256'}), patch.object(play,'_gh_api_get',side_effect=api), patch.object(play,'_gh_api_download',return_value=archive), patch.object(feed,'attest',side_effect=attestor):
            return feed.fetch('c'*40,7,self.root/'download','aapt2','apksigner')
    def test_verified_fetch(self):
        candidate,archive,run,artifact=self.setup_fetch()
        calls=[]
        self.assertEqual(candidate,self.fetch(archive,run,artifact,lambda p,s:calls.append(p.name)))
        self.assertEqual(feed.MEMBERS,set(calls))
    def test_unattested_substitution_even_self_adjusted_hash(self):
        self.fields['SENTINEL_RUNTIME_ENVIRONMENT'] = 'substituted'
        self.write_apk()
        with zipfile.ZipFile(self.apk) as z:
            self.binding['compiledPayloadSha256'] = feed.digest(feed.canonical({n:feed.digest(z.read(n)) for n in z.namelist()}))
        _,archive,run,artifact=self.setup_fetch()
        def deny(path,sha): raise ValueError('independent trusted subject mismatch')
        with self.assertRaises(ValueError): self.fetch(archive,run,artifact,deny)
    def test_archive_digest_substitution(self):
        _,archive,run,artifact=self.setup_fetch()
        with self.assertRaises(ValueError): self.fetch(archive+b'tamper',run,artifact,lambda p,s:None)
    def test_play_workflow_alias(self):
        _,archive,run,artifact=self.setup_fetch();run['path']='.github/workflows/release-candidate.yml'
        with self.assertRaises(ValueError): self.fetch(archive,run,artifact,lambda p,s:None)
    def test_attestation_command_has_exact_trust_constraints(self):
        with patch.object(feed,'tool') as tool:
            feed.attest(self.apk,'c'*40)
            args=tool.call_args.args[0]
            for item in ['--source-digest','c'*40,'--source-ref','refs/heads/main','--deny-self-hosted-runners',feed.REPOSITORY+'/'+feed.WORKFLOW]: self.assertIn(item,args)

if __name__ == '__main__': unittest.main()
