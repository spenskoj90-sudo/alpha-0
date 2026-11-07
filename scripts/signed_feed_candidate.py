#!/usr/bin/env python3
"""Dedicated non-Play candidate boundary. No signing, publication or key creation.

Approval is a separately reviewed, protected-main source record, never dispatch
inputs. Missing approval is deliberately fatal. GitHub API metadata and Sigstore
subject verification are both required; local caller hashes confer no authority.
"""
import argparse
import base64
import hashlib
import json
import re
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

import release_lineage as play
from signed_update_feed_release import (APPROVED_SIGNER, CERT, INSTALL_PERMISSION,
    MODERN_APK_SIGNATURE, PACKAGE, tool, url)

REPOSITORY = 'spenskoj90-sudo/alpha-0'
WORKFLOW = '.github/workflows/signed-feed-candidate.yml'
WORKFLOW_NAME = 'Signed Feed Candidate Artifact'
SCHEMA = 'sentinel.signed-feed-candidate.v1'
BINDING_SCHEMA = 'sentinel.signed-feed-presecret-binding.v1'
APK = 'app-signedRelease.apk'
CANDIDATE = 'signed-feed-candidate.json'
BINDING = 'signed-feed-presecret-binding.json'
MEMBERS = {APK, CANDIDATE, BINDING}
POLICY = Path('release/signed-feed-approval.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('expected JSON object')
    return value


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def attest(path, sha, workflow=WORKFLOW):
    tool(['gh', 'attestation', 'verify', str(path), '--repo', REPOSITORY,
          '--signer-workflow', f'{REPOSITORY}/{workflow}', '--source-digest', sha,
          '--source-ref', 'refs/heads/main', '--deny-self-hosted-runners'])


def approval(value):
    require(set(value) == {'schema', 'status', 'channel', 'package', 'signer',
        'feedUrl', 'verifyingKey', 'highestIssuedVersionCode', 'baselineSourceSha',
        'baselineApkSha256', 'reviewIssue'}, 'approval fields')
    require(value['schema'] == 'sentinel.signed-feed-approval.v1' and
            value['status'] == 'APPROVED' and value['reviewIssue'] == 532,
            'separate PROJECTS approval required')
    require(value['channel'] == 'signed_feed' and value['package'] == 'com.alpha0.app'
            and value['signer'] == APPROVED_SIGNER, 'approval identity')
    url(value['feedUrl'])
    require(type(value['highestIssuedVersionCode']) is int and
            10007 <= value['highestIssuedVersionCode'] < 2100000000, 'independent ledger floor')
    require(bool(re.fullmatch('[0-9a-f]{40}', value['baselineSourceSha'])) and
            bool(re.fullmatch('[0-9a-f]{64}', value['baselineApkSha256'])), 'baseline provenance')
    pin = base64.b64decode(value['verifyingKey'], validate=True)
    require(base64.b64encode(pin).decode() == value['verifyingKey'], 'canonical public pin')
    info = tool(['openssl', 'pkey', '-pubin', '-inform', 'DER', '-text_pub', '-noout'], data=pin)
    require(b'ASN1 OID: prime256v1' in info and b'Public-Key: (256 bit)' in info,
            'named P-256 SPKI required')
    return value


def approved_source(sha):
    require(bool(re.fullmatch('[0-9a-f]{40}', sha)), 'exact source SHA')
    require(tool(['git', 'rev-parse', 'HEAD']).decode().strip() == sha, 'checkout SHA')
    require(play._gh_api_get(f'/repos/{REPOSITORY}/git/ref/heads/main')['object']['sha'] == sha,
            'current protected main SHA')
    raw = tool(['git', 'show', f'{sha}:{POLICY.as_posix()}'])
    require(POLICY.read_bytes() == raw, 'approval must match protected source')
    return approval(document(raw))


def verify_baseline(policy, aapt2, apksigner):
    # Independently retained existing Play candidate, with original attestation.
    sha = policy['baselineSourceSha']
    version = tool(['git', 'show', f'{sha}:VERSION']).decode().strip()
    binding = play.build_presecret_binding(REPOSITORY, sha, version)
    candidate, files = play.fetch_candidate_package(REPOSITORY, sha, version, binding, APPROVED_SIGNER)
    with tempfile.TemporaryDirectory() as tmp:
        for name, raw in files.items():
            path = Path(tmp, name)
            path.write_bytes(raw)
            attest(path, sha, '.github/workflows/release-candidate.yml')
        apk = Path(tmp, play.APK_FILE)
        require(digest(apk.read_bytes()) == policy['baselineApkSha256'], 'approved baseline APK bytes')
        badging = tool([aapt2, 'dump', 'badging', str(apk)]).decode()
        found = PACKAGE.search(badging)
        require(found is not None and found[1] == 'com.alpha0.app', 'baseline package')
        baseline = int(found[2])
        require(10007 <= baseline <= policy['highestIssuedVersionCode'], 'baseline ledger inconsistency')
        verify_signature(apk, apksigner)
    return candidate


def presecret(sha, aapt2, apksigner):
    policy = approved_source(sha)
    # Existing canonical evidence verifies the full required workflow set.
    play.verify_live_presecret(REPOSITORY, sha, Path('VERSION').read_text().strip())
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['bash', 'scripts/verify_release_evidence_attestation.sh', REPOSITORY,
                        sha, str(Path(tmp) / 'evidence')], check=True)
    verify_baseline(policy, aapt2, apksigner)
    code = re.search(r'val canonicalVersionCode = (\d+)', Path('app/build.gradle.kts').read_text())
    require(code is not None and int(code[1]) > policy['highestIssuedVersionCode'], 'reviewed source version must advance ledger')
    return {'schema': BINDING_SCHEMA, 'repository': REPOSITORY, 'sourceSha': sha,
            'sourceRef': 'refs/heads/main', 'channel': 'signed_feed',
            'distribution': 'non_play', 'policy': policy, 'versionCode': int(code[1])}


def verify_signature(apk, apksigner):
    report = tool([apksigner, 'verify', '--verbose', '--print-certs', str(apk)]).decode('ascii')
    certs = CERT.findall(report)
    require(len(certs) == 1 and certs[0].lower().replace(':', '') == APPROVED_SIGNER,
            'single existing signer required')
    require(bool(MODERN_APK_SIGNATURE.search(report)), 'v2/v3 signature required')


def dex_constants(raw):
    """Read encoded static BuildConfig fields from actual DEX, not string presence.

    signedRelease retains this class for auditable post-R8 constant inspection.
    All offsets/indices are checked by Python's bounded buffers and final caller
    rejects malformed DEX. Only ASCII identity fields and boolean are accepted.
    """
    require(raw[:4] == b'dex\n' and len(raw) >= 112, 'DEX header')
    def u32(offset):
        return struct.unpack_from('<I', raw, offset)[0]
    require(u32(32) == len(raw) and u32(40) == 0x12345678, 'DEX size/endian')
    def leb(offset):
        result = 0
        for shift in range(0, 35, 7):
            byte = raw[offset]; offset += 1
            result |= (byte & 127) << shift
            if byte < 128:
                return result, offset
        raise ValueError('DEX invalid leb')
    def string(index):
        require(0 <= index < u32(56), 'DEX string index')
        offset = u32(u32(60) + 4 * index)
        _, offset = leb(offset)
        end = raw.index(b'\0', offset)
        return raw[offset:end].decode('utf-8')
    def type_name(index):
        require(0 <= index < u32(64), 'DEX type index')
        return string(u32(u32(68) + 4 * index))
    matches = []
    for index in range(u32(96)):
        offset = u32(100) + index * 32
        if type_name(u32(offset)) != 'Lcom/alpha0/app/BuildConfig;':
            continue
        class_data, values = u32(offset + 24), u32(offset + 28)
        require(class_data > 0 and values > 0, 'retained static BuildConfig required')
        count, pos = leb(class_data)
        for _ in range(3):
            _, pos = leb(pos)
        fields = []
        field_index = 0
        for _ in range(count):
            delta, pos = leb(pos); field_index += delta
            access, pos = leb(pos)
            require(field_index < u32(80), 'DEX field index')
            field = u32(84) + field_index * 8
            name = string(u32(field + 4))
            fields.append((name, access))
        length, pos = leb(values)
        require(length <= len(fields), 'DEX static array')
        result = {}
        for index in range(length):
            tag = raw[pos]; pos += 1
            kind, size = tag & 31, (tag >> 5) + 1
            if kind == 31:
                require(size in (1, 2), 'DEX boolean')
                value = size == 2
            else:
                require(kind in (4, 23) and size <= 4, 'DEX constant kind')
                value = int.from_bytes(raw[pos:pos + size], 'little'); pos += size
                if kind == 23:
                    value = string(value)
            name, access = fields[index]
            require(access & 0x18 == 0x18, 'DEX static final field')
            result[name] = value
        matches.append(result)
    return matches


def inspect(apk, binding, aapt2, apksigner, *, unsigned=False):
    policy = approval(binding['policy'])
    require(binding['schema'] == BINDING_SCHEMA and binding['repository'] == REPOSITORY and
            binding['sourceRef'] == 'refs/heads/main' and binding['channel'] == 'signed_feed' and
            binding['distribution'] == 'non_play', 'non-Play binding')
    require(apk.is_file() and 0 < apk.stat().st_size <= play.MAX_APK_BYTES, 'bounded APK bytes')
    before = digest(apk.read_bytes())
    if not unsigned:
        verify_signature(apk, apksigner)
    badging = tool([aapt2, 'dump', 'badging', str(apk)]).decode()
    package = PACKAGE.search(badging)
    require(package is not None and package[1] == 'com.alpha0.app', 'APK package')
    code = int(package[2])
    require(policy['highestIssuedVersionCode'] < code <= 2100000000 and
            code == binding['versionCode'], 'APK version downgrade/source mismatch')
    require(not re.search(r'(?m)^application-debuggable(?:\s|$)', badging), 'debug APK')
    permissions = tool([aapt2, 'dump', 'permissions', str(apk)]).decode()
    require(bool(INSTALL_PERMISSION.search(permissions)), 'merged installer permission')
    constants = []
    payload = {}
    with zipfile.ZipFile(apk) as archive:
        names = [i.filename for i in archive.infolist()]
        require(len(names) == len(set(names)), 'duplicate APK entries')
        for entry in archive.infolist():
            require(entry.file_size <= 64 * 1024 * 1024, 'bounded APK member')
            if not re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))', entry.filename, re.IGNORECASE):
                payload[entry.filename] = digest(archive.read(entry))
            if re.fullmatch(r'classes(?:[2-9]|[1-9][0-9]+)?\.dex', entry.filename):
                require(entry.file_size <= 64 * 1024 * 1024, 'bounded DEX')
                constants += dex_constants(archive.read(entry))
    require(len(constants) == 1, 'unique retained BuildConfig')
    expected = {'APPLICATION_ID': 'com.alpha0.app', 'DEBUG': False,
        'VERSION_CODE': code, 'SENTINEL_SOURCE_SHA': binding['sourceSha'],
        'SENTINEL_DISTRIBUTION_CHANNEL': 'signed_feed',
        'SENTINEL_UPDATE_FEED_URL': policy['feedUrl'],
        'SENTINEL_UPDATE_FEED_VERIFYING_KEY': policy['verifyingKey']}
    require(all(constants[0].get(key) == value for key, value in expected.items()),
            'compiled channel/source/feed/SPKI constants mismatch')
    payload_digest = digest(canonical(payload))
    if not unsigned:
        require(binding.get('compiledPayloadSha256') == payload_digest, 'presecret compiled payload mismatch')
    require(digest(apk.read_bytes()) == before, 'APK changed during inspection')
    return {'schema': 'sentinel.signed-feed-compiled-payload.v1' if unsigned else SCHEMA, 'repository': REPOSITORY, 'sourceSha': binding['sourceSha'],
        'sourceRef': 'refs/heads/main', 'channel': 'signed_feed', 'distribution': 'non_play',
        'apkFile': APK, 'apkSha256': before, 'apkSize': apk.stat().st_size,
        'package': 'com.alpha0.app', 'signer': None if unsigned else APPROVED_SIGNER, 'versionCode': code,
        'bindingSha256': digest(canonical(binding)), 'compiledPayloadSha256': payload_digest}


def fetch(sha, run_id, output, aapt2, apksigner):
    policy = approved_source(sha)
    prefix = f'/repos/{REPOSITORY}'
    run = play._gh_api_get(f'{prefix}/actions/runs/{run_id}')
    require(run.get('head_sha') == sha and run.get('head_branch') == 'main' and
        run.get('event') == 'workflow_dispatch' and run.get('path') == WORKFLOW and
        run.get('name') == WORKFLOW_NAME and run.get('status') == 'completed' and
        run.get('conclusion') == 'success', 'dedicated successful exact-source workflow required')
    artifacts = play._gh_api_get(f'{prefix}/actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    found = [a for a in artifacts if a.get('name') == f'sentinel-signed-feed-candidate-{sha}']
    require(len(found) == 1, 'unique non-Play artifact')
    artifact = found[0]
    require(artifact.get('workflow_run', {}).get('id') == run_id, 'artifact run identity')
    archive = play._gh_api_download(play._artifact_archive_endpoint(REPOSITORY, artifact['id']), play.MAX_CANDIDATE_ARCHIVE_BYTES)
    play._verify_archive_metadata(artifact, archive, expected_sha=sha)
    # Generic Play ZIP reader bounds non-Play APK as JSON; use a local strict
    # reader here to keep Play archive contracts byte-for-byte unchanged.
    import io
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        infos = z.infolist()
        require(len(infos) == 3 and {i.filename for i in infos} == MEMBERS, 'non-Play archive filenames')
        require(all(0 < i.file_size <= (200 * 1024 * 1024 if i.filename == APK else 65536)
                    for i in infos), 'archive member size')
        files = {i.filename: z.read(i) for i in infos}
    output.mkdir(exist_ok=False)
    for name, raw in files.items():
        (output / name).write_bytes(raw)
        attest(output / name, sha)
    binding = document(files[BINDING])
    require(binding['sourceSha'] == sha and binding['policy'] == policy, 'approval/source drift')
    expected = dict(binding); expected.pop('compiledPayloadSha256', None)
    require(expected == presecret(sha, aapt2, apksigner), 'independent presecret evidence drift')
    candidate = inspect(output / APK, binding, aapt2, apksigner)
    require(document(files[CANDIDATE]) == candidate, 'attested candidate metadata/bytes mismatch')
    return candidate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['presecret', 'bind-compiled', 'verify-compiled', 'inspect', 'fetch'])
    p.add_argument('--sha', required=True)
    p.add_argument('--aapt2', required=True)
    p.add_argument('--apksigner', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--binding', type=Path)
    p.add_argument('--apk', type=Path)
    p.add_argument('--run-id', type=int)
    args = p.parse_args()
    if args.command == 'presecret':
        value = presecret(args.sha, args.aapt2, args.apksigner)
    elif args.command in ('bind-compiled', 'verify-compiled'):
        binding = document(args.binding.read_bytes())
        require(binding['sourceSha'] == args.sha, 'compiled binding SHA')
        report = inspect(args.apk, binding, args.aapt2, args.apksigner, unsigned=True)
        value = dict(binding)
        value['compiledPayloadSha256'] = report['compiledPayloadSha256']
        if args.command == 'verify-compiled':
            expected = dict(binding); expected.pop('compiledPayloadSha256', None)
            require(expected == presecret(args.sha, args.aapt2, args.apksigner), 'presecret revalidation')
            require(value == binding, 'compiled presecret substitution')
    elif args.command == 'inspect':
        binding = document(args.binding.read_bytes())
        require(binding['sourceSha'] == args.sha, 'binding SHA')
        value = inspect(args.apk, binding, args.aapt2, args.apksigner)
    else:
        require(args.run_id is not None and args.run_id > 0, 'explicit trusted workflow run ID')
        fetch(args.sha, args.run_id, args.output, args.aapt2, args.apksigner)
        return
    with args.output.open('xb') as target:
        target.write(canonical(value))


if __name__ == '__main__':
    main()
