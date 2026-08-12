# RC1 Key Management Evidence

Gate A evidence is supplied by the release operator and is intentionally recorded without secrets or keystore passwords.

Verified on 2026-08-12:

- `release.keystore.gpg` present.
- `release.keystore.gpg.sig` present.
- `release.keystore.sha256` present.
- `public-key.asc` present.
- GPG signature verification: PASS / Good signature.
- GPG decryption: PASS.
- Byte-for-byte original/restored comparison: PASS.
- SHA-256 verification: PASS.
- Android `keytool` keystore open: PASS.

The release keystore remains outside GitHub. GitHub Actions must receive only the required CI signing secret through the repository secret store; private keys must never be committed.
