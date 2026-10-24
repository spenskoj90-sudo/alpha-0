# Sentinel offsite recovery — storage architecture v2.0

Status: PREPARED / DISABLED (2026-10-24). Backup workflow is manual-only and has not been run with production/staging credentials. No independent backup or restore PASS may be claimed yet.

## Source and safeguards

- Source: Neon project `royal-butterfly-62116978`, default branch `br-lingering-block-b1qa4fcd`, database `sentinel` (PostgreSQL 18). These are inventory identities; do not automatically switch connections if defaults change.
- Current Neon snapshot: `snap-royal-brook-b1hmsahq`, created 2026-10-24T14:30:51Z, expires 2026-11-07T00:00:00Z. This is *inside Neon*, not an independent backup.
- Export: `scripts/offsite_pg_backup.sh`, driven by manual-only `.github/workflows/offsite-db-backup.yml`. The CI job is deliberately inert until its provider prerequisites are configured. It must not run on pull requests or automatically on schedule before the first independent restore.
- Transport: direct, unpooled Neon PostgreSQL URL; `pg_dump -Fc --no-owner --no-acl` with PostgreSQL 18 in ephemeral Docker; the plaintext stream is piped straight to `age`.
- Storage: independent AWS S3 bucket, versioning and access logging enabled, public access blocked, default encryption enabled; age recipient protects the payload before S3 upload. Avoid storing a decrypting private key in GitHub, Render, Drive, or ChatGPT.
- Verification performed by workflow: `pg_dump` and `age` success with pipeline failure propagation, encrypted object uploaded, object downloaded, byte-for-byte ciphertext comparison. **Not** a restore test. No artifact bytes or credentials are uploaded to GitHub Actions.
- Default backup is treated as confidential: it can contain account records, MFA recovery codes, session material, or other sensitive rows, regardless of tenant-level RLS.

## Owner-controlled prerequisites (not yet provisioned)

1. Provision an independent S3 bucket under an AWS account, with block-public-access, encryption, versioning, audit logging, cost notifications, and a narrowly scoped retention policy. Avoid a bucket in the same infrastructure account as Neon. This may incur charges. The exact bucket name and AWS account are not chosen in this document.
2. Provision an IAM OIDC role for GitHub Actions with access to *only* `arn:aws:s3:::<backup-bucket>/sentinel/staging/*` and `s3:PutObject`, `s3:GetObject`. Trust must require `token.actions.githubusercontent.com:aud=sts.amazonaws.com` and `token.actions.githubusercontent.com:sub=repo:spenskoj90-sudo/alpha-0:ref:refs/heads/main`. The role must not be usable from PRs/forks or other repositories.
3. Generate an age X25519 key pair offline. Keep **private identity** offline with a separate recovery copy. GitHub receives *only the public recipient*.
4. Create a least-privilege **read-only backup DB role** on the correct Neon branch that has SELECT privileges on all required tables, including future schema changes and application/managed-auth schemas, or use a narrowly scoped backup credential whose access has been assessed. Do not reuse the runtime role if it cannot read all required objects. Use a dedicated, direct (non-pooler) URL. Put it into GitHub Actions encrypted secret `SENTINEL_BACKUP_DATABASE_URL` or into a verified secret-manager injection; never commit it or place it into chat/Drive.
5. Set GitHub Actions variables `SENTINEL_BACKUP_AGE_RECIPIENT` (public), `SENTINEL_BACKUP_S3_BUCKET`, `SENTINEL_BACKUP_AWS_ROLE_ARN`, `SENTINEL_BACKUP_AWS_REGION`, `SENTINEL_BACKUP_EXPECTED_HOST`, and `SENTINEL_BACKUP_EXPECTED_DATABASE`. The last two must exactly match the *current verified main branch compute host* and DB name, not a pooled endpoint; initially verified on 2026-10-24: `ep-fragrant-hall-b14yfhj5.c-5.eu-central-1.aws.neon.tech`, database `sentinel`. If Neon endpoint is rotated/restored, update the expected host after verifying branch identity. The workflow aborts if URL credentials/TLS/host/database mismatch. No secret values are recorded here.
6. Restrict workflow edit and dispatch access; audit GitHub branch protection and AWS OIDC trust before enabling. The repository currently is public.
7. Execute the workflow once on protected main. Confirm the S3 object exists, its size and SHA-256 match the workflow report, and public read is blocked.

## Independent restore drill (mandatory before declaring backup operational)

In a controlled, temporary PostgreSQL 18 environment **separate from Neon production/staging**:

1. Retrieve one encrypted `.pgdump.age` object and verify its encrypted SHA-256 against the recorded audit record. Keep the offline age private key out of CI and chat.
2. Decrypt locally in a protected temporary directory, and run `pg_restore --list` on the custom-format dump. Do not print actual row values or sensitive DDL.
3. Create a *new empty* isolated Postgres database, using a target connection string verified **not** to reference Neon main, staging, or any active service. Restore with `pg_restore --exit-on-error --no-owner --no-acl --dbname="<isolated_test_connection>" <dump>`. Never use `--clean` or `--create` against an existing database.
4. Check schema count, object count, migration markers, extension dependencies, relevant row-count aggregates, key constraints and application smoke tests without displaying personal data.
5. Confirm restore time against an agreed RTO and backup freshness against an agreed RPO. Document exact backup name, checksum, test date, target identity (without secrets), pass/fail and limitations.
6. Destroy the isolated recovery test environment only after the Owner permits, without touching Neon main or retained encrypted source backup.

If anything fails, declare **RESTORE_UNVERIFIED**, repair the pipeline, and repeat on a fresh backup. Do not claim success from a snapshot or `pg_restore --list` alone.

## After first restore PASS

- Add a bounded nightly schedule (initial target RPO <=24h) in a separate reviewed change. Monitor last-success timestamps and notify on missed backups; failures must not erase the most recent valid backup.
- Implement 7 daily, 4 weekly, 3 monthly generations with explicit immutable-object/retention and cost review. Do not use an unconditional bucket-wide delete rule.
- Run monthly off-provider restore drills and reconcile source schema and protection status.
- Record only safe evidence metadata in Google Drive `Projects/00-portfolio/assets-register`, never backup bytes or keys.
- If the manual Neon snapshot expires, do not assume it is independently recoverable; re-evaluate available Neon snapshot limits and offsite health.

## Risk and current blocking facts

- The account is currently Neon Free (1 manual snapshot, 6h history window). A single manual snapshot is not nightly protection.
- The connected tools cannot create the customer's AWS account, bucket, OIDC trust, or inject the real GitHub secret via the existing GitHub connector. Those gates remain unsatisfied; **no encrypted S3 object has been created** by this change.
- Backup exporter does not yet independently certify complete access to all auth schemas. The first export and isolated restore must prove completeness.
- Do not route exports through public GitHub artifacts, issue comments, ChatGPT messages, or unencrypted Drive files.
- Restore operations on the original Neon branch are prohibited for this validation: a prior restore incident affected the default branch unexpectedly.
