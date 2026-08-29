# SENTINEL — Workflow Contract

**Issue:** #14  
**Purpose:** Machine-operable contract for automated task-to-PR workflow. Prevents autonomous merge, release, credential, and production actions while maximizing routine automation.  
**Authority:** Human Owner is final authority for merge into `main`, deploy, credential changes, and release. Agents never perform these actions; they only propose them in text.

This contract is binding for engineering agents working on this repository. It does not replace `docs/SENTINEL_EVIDENCE_PROTOCOL.md` or `docs/SENTINEL_CURRENT_STATE.md` — agents must follow those documents and reference them rather than duplicating their content.

---

## 1. Issue intake

Before any implementation work begins, the following fields are **mandatory**. Work must not start until they are explicit in the issue body or an accepted linked note.

| Field | Requirement |
|-------|-------------|
| **Goal** | One-sentence statement of the intended outcome. |
| **Change boundaries** | Exact paths, modules, or surfaces that may be modified. Paths outside this list are out of scope. |
| **Acceptance criteria** | Observable, testable conditions that define "done". Prefer measurable checks (tests green on exact SHA, specific behavior, documented artifact). |

Optional but recommended: baseline SHA, non-goals, related issues/PRs, and any required Human Owner decisions.

If an issue lacks these fields, the agent must stop and request clarification rather than invent scope.

---

## 2. Branch naming

All work branches use a single, predictable format:

```text
<type>/<short-description>-<issue-number>
```

Examples:

- `docs/workflow-contract-14`
- `fix/auth-lockout-42`
- `feat/device-attestation-55`
- `ci/coverage-gate-30`
- `security/public-release-hardening`

Rules:

- `type` is one of: `feat`, `fix`, `docs`, `ci`, `test`, `security`, `chore`, `refactor`, `sentinel` (or other established prefixes already used in the repo).
- Short description is lowercase, hyphen-separated, and descriptive.
- Issue number is appended when the branch implements a tracked issue.
- Branches are short-lived. Long-lived feature branches are discouraged.
- Never push directly to `main`. Never force-push to `main` or to any protected branch.

---

## 3. Implementation boundaries

**One issue = one PR = limited file set.**

- A single PR must implement exactly one issue (or a narrowly scoped sub-task of one issue).
- The set of changed files must stay within the change boundaries declared at issue intake.
- Do not expand scope mid-PR. If additional changes become necessary, open a new issue or obtain explicit Human Owner approval and update the boundaries in writing.

**Must not be changed without separate, explicit Human Owner permission:**

- Production credentials, secrets, or key material
- Signing certificates / keystore configuration used for release
- Branch protection rules or required status checks on `main`
- Database migration semantics that break existing data or checksums
- Core security invariants listed in `docs/SENTINEL_CURRENT_STATE.md` (opaque-token sessions, Keystore identity model, default-deny authorization, production `DATABASE_URL` requirements, RLS/service-role boundary, transactional refresh rotation)
- Release tags, production deploys, or live environment configuration

Agents may propose such changes in text only.

---

## 4. CI gates

Required automated checks that must be green on the **exact commit SHA** under review are defined in `docs/RELEASE_GATES.md`. Do not duplicate that list here.

Agents must:

- Cite the exact SHA and the corresponding GitHub Actions run IDs.
- Treat a green result on a different SHA as non-evidence for the current claim.
- Respect the Evidence Protocol status vocabulary (`VERIFIED`, `MAIN PASS`, `BRANCH PASS`, `PARTIAL`, `UNVERIFIED`, `REGRESSION`, etc.) defined in `docs/SENTINEL_EVIDENCE_PROTOCOL.md`.

---

## 5. Review evidence

Claims about CI status, test results, or acceptance may only be supported by **concrete GitHub Actions run IDs** (and optionally the run URL) tied to the exact SHA.

Prohibited:

- Vague statements such as "CI is green", "tests passed", or "everything looks good" without run IDs.
- Re-using run IDs from a different SHA or from a branch that is no longer the one under review.

Required form for any success claim:

```text
SHA: <full-or-short-sha>
Workflow: <name>
Run ID: <numeric-id>
Result: success
```

---

## 6. Regression handling

If CI fails on the exact SHA after a claimed success, or if a previously accepted capability disappears:

1. Do **not** declare success.
2. Re-run or obtain a fresh run on the same SHA (or the corrected SHA after a fix).
3. Classify according to `docs/SENTINEL_EVIDENCE_PROTOCOL.md` (including the `REGRESSION` format when applicable).
4. Fix the regression in a new commit on the same branch or a follow-up PR; do not paper over a red check.

A prior green run on an older SHA does not satisfy acceptance for a later SHA.

---

## 7. PR acceptance

Before requesting merge, the following checklist must be satisfied and evidenced:

- [ ] Issue intake fields (goal, boundaries, acceptance criteria) are present and the PR stays inside those boundaries.
- [ ] Branch name follows the naming convention and is based on current `main`.
- [ ] Exactly one logical change set; no unrelated files.
- [ ] All required CI gates from `docs/RELEASE_GATES.md` are green on the **exact PR head SHA**, with run IDs recorded.
- [ ] Evidence Protocol rules observed; no bare `PASS` claims.
- [ ] Documentation updated if public behavior, deployment, or contracts changed.
- [ ] No secrets, credentials, or production configuration introduced or modified.
- [ ] Human Owner has been informed that the PR is ready for review/merge (agent does not merge).

---

## 8. Human approval points

The following actions are **never** performed by an agent. The agent may only describe the recommended action in text and wait for explicit Human Owner execution or one-word confirmation where the repository process requires it.

| Action | Agent role |
|--------|------------|
| Merge into `main` | Propose only; never click merge or use API to merge. |
| Deploy to any environment | Propose only. |
| Create or rotate credentials / secrets / signing material | Propose only; never write or print secret values. |
| Create a release tag or GitHub Release | Propose only. |
| Change branch protection or required status checks | Propose only. |
| Delete protected branches or perform force-push to `main` | Never. |
| Production database migrations that are irreversible | Propose only after explicit Human Owner approval. |

---

## References (do not duplicate)

- Evidence rules and status vocabulary: `docs/SENTINEL_EVIDENCE_PROTOCOL.md`
- Canonical product state and security invariants: `docs/SENTINEL_CURRENT_STATE.md`
- Release and CI gate definitions: `docs/RELEASE_GATES.md`
- High-level contribution notes: `docs/CONTRIBUTING.md`
