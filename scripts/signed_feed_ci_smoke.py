#!/usr/bin/env python3
"""Real Android tool smoke, EPHEMERAL TEST KEYS, never release evidence/upload."""
import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import signed_feed_candidate as feed
from apk_signer_certificate import certificate_digests


def main():
    sdk = Path(os.environ.get('ANDROID_SDK_ROOT', os.environ.get('ANDROID_HOME', '')))
    tools = sorted((sdk / 'build-tools').glob('*/apksigner'), key=lambda p: [int(v) for v in re.findall(r'\d+', p.parent.name)])
    feed.require(bool(tools), 'existing Android SDK build tools required')
    apksigner = tools[-1]
    aapt2 = apksigner.with_name('aapt2')
    sha = feed.tool(['git', 'rev-parse', 'HEAD']).decode().strip()
    with tempfile.TemporaryDirectory(prefix='signed-feed-ci-') as tmp:
        root = Path(tmp)
        key = root / 'ephemeral-feed.pem'
        feed.tool(['openssl', 'ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', str(key)])
        public = feed.tool(['openssl', 'pkey', '-in', str(key), '-pubout', '-outform', 'DER'])
        keystore = root / 'ephemeral.jks'
        feed.tool(['keytool', '-genkeypair', '-keystore', str(keystore), '-alias', 'isolated',
            '-storepass', 'isolated-only', '-keypass', 'isolated-only', '-dname', 'CN=SyntheticCI',
            '-keyalg', 'RSA', '-keysize', '2048', '-validity', '1'])
        cert = feed.tool(['keytool', '-exportcert', '-keystore', str(keystore), '-alias', 'isolated', '-storepass', 'isolated-only'])
        cert_hash = hashlib.sha256(cert).hexdigest()
        feed.require(cert_hash != feed.APPROVED_SIGNER, 'CI must never have release signer')
        policy = dict(schema='sentinel.signed-feed-approval.v1', status='APPROVED', reviewIssue=532,
            channel='signed_feed', package='com.alpha0.app', signer=feed.APPROVED_SIGNER,
            apiBaseUrl='https://ci.invalid', vkClientId='123', feedUrl='https://ci.invalid/synthetic/feed.txt', verifyingKey=base64.b64encode(public).decode(),
            highestIssuedVersionCode=10007, baselineSourceSha='0'*40, baselineApkSha256='0'*64)
        # This fixture is not passed to approved_source or any secret/provenance
        # gate. Its APPROVED value only satisfies the low-level parser schema.
        code = int(re.search(r'val canonicalVersionCode = (\d+)', Path('app/build.gradle.kts').read_text())[1])
        binding = dict(schema=feed.BINDING_SCHEMA, repository=feed.REPOSITORY, sourceSha=sha,
            sourceRef='refs/heads/main', channel='signed_feed', distribution='non_play', policy=policy, versionCode=code)
        env = dict(os.environ, ANDROID_KEYSTORE_PATH=str(keystore), ANDROID_KEYSTORE_PASSWORD='isolated-only',
            ANDROID_KEY_ALIAS='isolated', ANDROID_KEY_PASSWORD='isolated-only',
            SENTINEL_SOURCE_SHA=sha, SENTINEL_API_BASE_URL=policy['apiBaseUrl'],
            SENTINEL_API_FALLBACK_BASE_URL='', SENTINEL_VK_CLIENT_ID=policy['vkClientId'],
            SENTINEL_UPDATE_FEED_URL=policy['feedUrl'], SENTINEL_UPDATE_FEED_VERIFYING_KEY=policy['verifyingKey'])
        apk = Path('app/build/outputs/apk/signedRelease/app-signedRelease.apk')
        try:
            subprocess.run(['bash', './gradlew', '--no-daemon', 'assembleSignedRelease', 'lintDebug'], env=env, check=True)
            report = feed.tool([str(apksigner), 'verify', '--verbose', '--print-certs', str(apk)]).decode('ascii')
            feed.require(certificate_digests(report)['sha256'] == cert_hash, 'real ephemeral APK certificate')
            feed.require(bool(feed.MODERN_APK_SIGNATURE.search(report)), 'real ephemeral APK v2/v3 signature')
            compiled = feed.inspect(apk, binding, str(aapt2), str(apksigner), unsigned=True)
            binding['compiledPayloadSha256'] = compiled['compiledPayloadSha256']
            try:
                feed.inspect(apk, binding, str(aapt2), str(apksigner))
            except ValueError as error:
                feed.require(str(error) == 'single existing signer required', 'unexpected real APK rejection')
            else:
                raise ValueError('CI signer was accepted as protected release signer')
            receipt = dict(schema='sentinel.signed-feed-ci-receipt.v1', status='CI_ONLY',
                sourceSha=sha, channel='signed_feed', versionCode=code,
                apkSha256=compiled['apkSha256'], compiledPayloadSha256=compiled['compiledPayloadSha256'],
                ephemeralCertificateSha256=cert_hash, protectedSignerVerified=False,
                installableArtifactRetained=False, productionPublished=False)
            Path('signed-feed-ci-receipt.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')
            print('SIGNED_FEED_CI_RECEIPT ' + json.dumps(receipt, sort_keys=True))
            print('PASS real APK aapt2/permissions/non-debuggable/typed DEX/source/channel/feed/P-256 and ephemeral v2/v3; release signer rejected')
            print('SYNTHETIC CI ONLY: protected signing/attestation/publication/physical acceptance NOT_RUN')
        finally:
            # CI artifacts never retain installable test APKs or disposable keys.
            apk.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
