# SENTINEL Security Boundary Audit — Issue #9

**Audit date:** 2026-08-29  
**Baseline SHA (main at audit start):** `8027f2f914184e7aea5b36a75e531f436e26b915`  
**Branch:** `security/least-privilege-secrets-audit-9-clean`  
**Scope:** least-privilege CI permissions, secret exposure paths, signing separation, dependency surface, secret handling, auditability.  
**Invariants preserved:** opaque-token sessions, Android Keystore P-256 identity, default-deny authorization, production DATABASE_URL / enrollment-token requirements, migration checksums, service-role/RLS boundary, transactional refresh rotation, signing secrets, production credentials.

---

## Control status summary

| Control area | Status | Notes |
| --- | --- | --- |
| Authorization / Default Deny | VERIFIED | Covered by existing security regression / negative tests; not modified. |
| CI/CD GITHUB_TOKEN permissions | VERIFIED | All workflows declare explicit minimal `permissions`. |
| Signing configuration | VERIFIED + FIXED | Release/debug separation enforced; secret length metadata logging removed. |
| Dependency surface | VERIFIED | Security workflow runs pip-audit, npm audit (high+), Trivy fs. |
| Secret handling | VERIFIED + FIXED | No hardcoded secrets found; CI secret scan present; length echoes removed. |
| Auditability / traceability | VERIFIED | Findings bound to files; CI evidence requires exact SHA + Run ID. |

---

## Findings

### Finding 1 — Secret metadata logged in Build & Test workflow

```text
Finding
Severity: low
Location: .github/workflows/build.yml — android job steps "Decode release keystore" and "Assemble signed release"
Status: FIXED
Evidence: echo lines for ANDROID_KEYSTORE_BASE64 / ANDROID_KEYSTORE_PASSWORD / ANDROID_KEY_PASSWORD length removed; set +x retained; functional decode/assemble/verify path unchanged.
Safe remediation: Removed the three `echo "... length: ${#...}"` statements. No secret values were ever printed; metadata exposure reduced to zero for these fields.
```

### Finding 2 — Workflow GITHUB_TOKEN permissions (least privilege)

```text
Finding
Severity: low (informational)
Location: .github/workflows/*.yml — top-level permissions blocks
Status: VERIFIED
Evidence:
  - build.yml, android-build.yml, p1-evidence.yml, release-candidate.yml: contents: read
  - security.yml: contents: read, security-events: write, actions: read (CodeQL)
  - deploy.yml: contents: read, packages: write (GHCR push)
  - release.yml: contents: write (gh release create)
  No pull_request_target; no workflow_run privilege escalation path.
Safe remediation: None required. Write scopes are limited to jobs that need them.
```

### Finding 3 — Signing secrets not present on PR / fork paths

```text
Finding
Severity: low (informational)
Location: .github/workflows/android-build.yml (PR/all-branches debug only); build.yml / release*.yml (secrets only where signing required)
Status: VERIFIED
Evidence: android-build.yml has no secrets.* references and only builds debug APK. Release signing steps exist only in build.yml (main/PR on main), release.yml (tag), release-candidate.yml (main). GitHub does not inject repository secrets into workflows from forked PRs by default.
Safe remediation: None required.
```

### Finding 4 — deploy.yml secrets-in-if condition

```text
Finding
Severity: low
Location: .github/workflows/deploy.yml — job "remote" if: ${{ secrets.DEPLOY_HOST != '' && secrets.DEPLOY_USER != '' && secrets.DEPLOY_KEY != '' }}
Status: GAP
Evidence: Workflow triggers only on release published. Pattern is common but GitHub docs discourage secrets in `if` expressions (existence leakage / evaluation quirks). Job is skipped when secrets absent; no secret values are logged.
Safe remediation: Optional Owner-approved change: move presence checks to env vars set from secrets and test those, or keep as-is. No change applied in this PR (deploy configuration boundary).
```

### Finding 5 — Hardcoded credentials / obvious secret material in source

```text
Finding
Severity: low (informational)
Location: repository tree (security.yml filesystem job + manual review of .env.example, .gitignore, security.py)
Status: VERIFIED
Evidence: security.yml rejects AKIA*, private key PEMs, and gh[pousr]_ tokens. .env.example uses CHANGE_ME placeholders only. .gitignore excludes .env, *.jks, *.keystore. No production credential material found in audited paths.
Safe remediation: None required. Continue relying on GitHub Secret Scanning + push protection (environment gate).
```

### Finding 6 — Authorization / default-deny (server)

```text
Finding
Severity: low (informational)
Location: server/app (auth, security, RLS migrations, tests/test_security*.py, test_service_role_boundary.py, test_rls_policies.py)
Status: VERIFIED
Evidence: Existing automated tests cover default-deny, service-role boundary, RLS force, lockout, integrity policy. No change in this issue scope; invariants not modified.
Safe remediation: None required for issue #9.
```

### Finding 7 — Dependency / SCA surface

```text
Finding
Severity: low (informational)
Location: .github/workflows/security.yml — dependencies + filesystem jobs
Status: VERIFIED
Evidence: pip-audit (server), npm audit --audit-level=high (web), Trivy fs HIGH/CRITICAL with exit-code 1. No actionable dependency change required without a concrete CVE finding at this SHA.
Safe remediation: None in this PR. Future actionable CVEs would be fixed via lockfile/manifest PRs only.
```

### Finding 8 — docs lag on Canonical HEAD

```text
Finding
Severity: low
Location: docs/SENTINEL_CURRENT_STATE.md claims HEAD ba3c310… while live main is 8027f2f…
Status: GAP
Evidence: State document not updated for subsequent docs merges (issue #14 completion commit). Outside pure security control; recorded for traceability.
Safe remediation: Separate docs sync PR (not issue #9). Owner may schedule HANDOVER/CURRENT_STATE update.
```

---

## Changes in this PR

1. `.github/workflows/build.yml` — removed three secret-length echo statements (Finding 1 FIXED).
2. `docs/SENTINEL_SECURITY_BOUNDARY_AUDIT_ISSUE9.md` — this audit record.

No production credentials, signing material, branch protection, or security invariants were modified.

---

## Acceptance mapping

| Criterion | Result |
| --- | --- |
| Each control VERIFIED or GAP | Yes |
| VERIFIED backed by check/test/doc | Yes |
| GAP has next action | Yes (Findings 4, 8) |
| Fixed finding has automated or objective evidence path | Yes (workflow source change; CI will re-run on PR) |
| No secret values printed | Yes |
| Scope within change boundaries | Yes |
| No merge/deploy/credential rotation | Yes |
