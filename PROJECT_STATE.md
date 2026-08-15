# SENTINEL — Project State

Updated: 2026-08-15

## Keystore / signing state

The 5th release keystore is the intended permanent release key for this validation cycle. It was not recreated because of a defect in the previous keystore. The previous key was known-good and CI-validated; rotation was performed solely so the password could be backed up safely outside GitHub Secrets. The new keystore was backed up immediately using GPG + Drive + KeePass.

New release certificate fingerprint:

`2A:CD:1C:FF:F4:F3:4D:B1:25:0D:3F:6C:81:F0:88:74:93:C4:60:2D:3C:FA:65:31:09:93:C0:58:08:9D:B8:8E`

GitHub Secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, and `ANDROID_KEY_PASSWORD` were updated for the new key.

The first CI attempt against the new key failed before keystore validation because the Base64 secret had been manually pasted through the browser and was truncated at 5738 characters. The failure was `keytool error: java.io.EOFException`, confirming that the decoded byte stream was not a complete keystore. No keystore recreation is required or planned.

The Base64 secret was subsequently replaced directly from the saved file using `gh secret set`, avoiding browser/manual entry entirely.

## CI validation after direct secret replacement

The failed `Build & Test` run `31874695151` (run #154) is being rerun as attempt 2 against the exact same HEAD `a0ed24e83089fc3ca9e64f77a7d9d39829244a59`; no source commit is required for the secret-only correction.

The rerun must validate the complete chain:

`keystore decode → keystore format → store password → release alias → PrivateKeyEntry → certificate fingerprint → expected fingerprint comparison → signed release APK → apksigner/fingerprint verification`.

Other Build & Test jobs are already passing in the rerun; the Android build/signing job is the remaining active job.

## GitHub Actions workflow inventory

The repository currently has **13 workflow YAML files** under `.github/workflows/` plus **1 GitHub-generated Dependabot Dependency Graph workflow**, for **14 registered active workflows** in GitHub Actions.

Therefore the ~1500+ runs visible in the Actions UI are **not evidence of 1500 active workflows**. They are historical workflow-run records accumulated during the project's development, debugging, repeated PR validations, retries, and CI iterations. The repository has substantially more than the six workflows previously summarized in this document; the six-item description was incomplete, not an indication that GitHub was displaying old runs as active workflows.

The registered workflows include Android CI, Build & Test, sentinel-ci, CodeQL, Dependency Review, deploy, Fingerprint Diagnostic, Full Validation variants, P1 Evidence, security, backend CI, Server E2E, release, and the generated Dependabot Dependency Graph workflow.

The large historical run count does **not** affect source code, builds, releases, signing, or runtime behavior. It does not need to be cleaned for technical correctness. Keeping the history is normally preferable because it preserves debugging/audit evidence. Old runs can be deleted only for repository housekeeping/UI reduction if desired; deletion is not a release or CI remediation and is not required for SENTINEL readiness.

## Validation baseline

- Repository verification: PASS
- Core tests and coverage: PASS
- PostgreSQL integration and recovery: PASS
- Web build: PASS
- Container build: PASS
- Reproducible container build comparison: PASS
- Deployment smoke and health: PASS
- Android assembleDebug: PASS
- Android unit tests: PASS
- Android instrumentation APK build: PASS

## Firebase Test Lab

FTL remains an independent environment/authentication concern and is not caused by the release keystore or Base64 transport issue.

## Release gate

Release signing is pending the completion of the current Build & Test rerun. No further keystore recreation is authorized or required.
