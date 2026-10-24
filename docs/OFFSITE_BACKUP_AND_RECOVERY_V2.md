# Sentinel independent backup and recovery — Storage v2.1 (Cloudflare R2)

Status: **APPROVED PROVIDER, CODE PREPARED, NOT ACTIVATED**, 2026-10-24.
This document supersedes the earlier AWS S3/OIDC setup in this PR, **not** the global minimum-necessary Storage Policy v2.0. A prepared exporter, Cloudflare free-tier selection or an on-provider Neon snapshot is NOT an independent verified backup.

## Source and preservation

- Current authoritative source: Neon project `royal-butterfly-62116978`, branch `br-lingering-block-b1qa4fcd` (default `main`), PostgreSQL 18 database `sentinel`.
- Verified direct compute hostname on 2026-10-24: `ep-fragrant-hall-b14yfhj5.c-5.eu-central-1.aws.neon.tech`; check it against the *actual current Neon main branch* immediately before configuring/dispatching export. Never use a pooler host or a different Neon branch.
- A provider-internal manual snapshot `snap-royal-brook-b1hmsahq` expires **2026-11-07T00:00:00Z**. Its isolated Neon restore preview (`br-proud-lake-b1axiq7m`, auto-expiry 2026-10-31T15:00:00Z) previously matched 53 tables, 11 selected row-count aggregates, and six schema fingerprints. This DOES NOT prove external pg_dump completeness or independent recovery.
- Do not modify default database, uninstall applications, delete old archives, deactivate legacy providers or close the Sentinel repository as part of the backup preparation.

## Off-provider design

- Cloudflare R2 **Standard** bucket, private, created and owned by the Human Owner under their own account; R2 activation and provider billing rules are an explicit owner action. Free usage allowances are not a hard no-charge ceiling: configure spend alerts/caps and review retention.
- R2 S3-compatible endpoint `https://<32-character-account-id>.r2.cloudflarestorage.com`; jurisdiction-specific endpoints can use the supported suffix (e.g. EU). Script fails closed if the endpoint is not an approved exact Cloudflare R2 pattern.
- R2 **bucket-scoped Object Read & Write API token** (not general Cloudflare admin key). GitHub Actions secrets `SENTINEL_BACKUP_R2_ACCESS_KEY_ID` and `SENTINEL_BACKUP_R2_SECRET_ACCESS_KEY`. R2 S3 API uses `AWS_REGION=auto`. Limit access to the designated backup bucket only, and rotate credentials after tests. R2 API tokens may be granted broader scope than a prefix; rely on a dedicated bucket for least privilege. Never put credentials in repository files, Google Drive docs, ChatGPT or Actions artifacts.
- Dedicated Neon **read-only** backup URL via GitHub encrypted secret `SENTINEL_BACKUP_DATABASE_URL`; least-privilege access must cover *all required* schemas including `public` and managed auth objects. Permissions for future tables/extensions must be designed and tested. No production runtime password reuse unless independently approved.
- Generate an `age` X25519 identity offline; store the **private identity** in independently backed up encrypted custody, away from GitHub/Cloudflare/Neon, with a second recovery copy. Set only the public age recipient in GitHub variables. R2 encrypts storage at rest, but backup confidentiality relies primarily on this client-side age encryption.
- `pg_dump -Fc --no-owner --no-acl` streams from an ephemeral PostgreSQL 18 client into `age`; plaintext is not stored on the CI runner. `set -euo pipefail` fails on pg_dump/encryption errors. Cloudflare R2 upload and download are checked byte-for-byte before reporting encrypted SHA256, size and object key. **Do not use AWS-only --sse AES256 with R2**.
- Export is **manual only** on exact `spenskoj90-sudo/alpha-0` repository's `refs/heads/main`. It is deliberately not scheduled and no data is exported by a pull-request workflow. Main-branch secret access and workflow editing must be restricted.

## Owner setup checklist — no secrets pasted into conversations

1. Activate Cloudflare R2 in the owner's account; check plan, billing settings and region/legal-data requirements. Create one **dedicated private Standard bucket** for encrypted database backups, no public URL/custom public domain and no anonymous reads. Record only the bucket name and region in the owner-approved non-secret asset register.
2. Create one R2 API token with **Object Read & Write** for that *specific bucket only*. Store secret key and access key in GitHub Actions repository secrets `SENTINEL_BACKUP_R2_ACCESS_KEY_ID` and `SENTINEL_BACKUP_R2_SECRET_ACCESS_KEY` or use a later verified secret-manager injection. Confirm no keys leak into action logs.
3. Create a read-only dump role with proper access to `public`, `neon_auth` and necessary extensions. Validate the actual direct Neon URL/branch identity and set secret `SENTINEL_BACKUP_DATABASE_URL`. Data access must remain limited to this intended source.
4. Independently create/export and **test opening** an offline age private identity. Set public GitHub variable `SENTINEL_BACKUP_AGE_RECIPIENT`; never upload the identity itself to GitHub, Drive or R2.
5. Set non-secret GitHub Actions variables: `SENTINEL_BACKUP_S3_BUCKET` (historical name retained to avoid breaking exporter contract), `SENTINEL_BACKUP_R2_ENDPOINT`, `SENTINEL_BACKUP_EXPECTED_HOST`, `SENTINEL_BACKUP_EXPECTED_DATABASE` (expected `sentinel`). Current endpoint and database must be read back from Neon main before execution.
6. Review current exact source and PR CI; after a reviewed merge to protected main, run exactly one **manual** workflow dispatch. Validate ciphertext SHA256/length, R2 object existence and negative anonymous-access test. Keep evidence metadata only; never store a plaintext dump or decryption keys in CI artifacts.
7. If any precondition fails, mark BACKUP_FAILED, do not promote to release readiness, do not remove old backups/snapshots or change production DB.

## Independent full recovery drill — REQUIRED

Using a **separate, empty PostgreSQL 18 restore environment** and the offline age private identity:

1. Download one encrypted object via a separate tested R2 read path. Verify SHA256 equals export log. Confirm owner can still access the recovery key without dependency on GitHub, Cloudflare or Neon.
2. Decrypt under temporary encrypted local custody; run `pg_restore --list` without outputting PII or secret values.
3. Assert the target is **not** Sentinel Neon main/staging or any other serving database. Restore into a fresh empty isolated database using `pg_restore --exit-on-error --no-owner --no-acl`. Never use `--clean` or `--create` against an existing database.
4. Validate all expected schema objects, extensions, migrations, table row-count aggregates, critical constraints and application smoke tests. Pay particular attention to managed auth schema permissions and ownership; a successful pg_dump process alone is insufficient.
5. Log anonymized results: date, source fingerprint and snapshot time, ciphertext SHA256, backup object key, RTO and RPO, target identity, tests run, and PASS/FAIL. No records, auth tokens, SQL data values or private keys in Google Drive.
6. Do not enable scheduled retention or discard old data unless export **and independent restore** pass. Isolated test cleanup requires a separately checked identity and owner-reviewed non-destructive disposal.

## After recovery PASS

- Schedule time-bounded backups with explicit target RPO <=24 hours and periodic alerting on missing exports.
- Implement and **test** an affordable retention lifecycle target (7 daily, 4 weekly, 3 monthly). R2 API/retention semantics must be verified before implementing any automated delete, and the last verified-good backup must never be deleted.
- Run monthly isolated restore tests. Include costs/free-usage and security reviews.
- Review availability of disaster recovery beyond the R2 account itself: the age identity and at least one tested export must remain retrievable after provider-account loss.
- Re-evaluate public-to-private GitHub transition and all Render integrations independently; GitHub Actions minutes may change after privatization.

## Current blockers

No Cloudflare R2 account connection, bucket, scoped credentials, backup DB secret or offline age identity is verified. Firebase and Infisical are separate approved-but-not-configured components. The repository PR is draft and the job must stay inactive until verified setup. No encrypted offsite object or independent pg_restore PASS exists yet.
