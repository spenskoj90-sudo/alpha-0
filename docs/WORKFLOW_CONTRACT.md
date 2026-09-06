# SENTINEL — Autonomous Engineering Workflow Contract

**Tracking issue:** #167  
**Status:** PROPOSED — pending Human Owner approval.  
**Authority:** Human Owner is final authority for product direction and protected actions. GPT/ChatGPT is the sole AI engineering participant and executor.

This contract defines the normal autonomous engineering lifecycle. It complements `docs/SENTINEL_EVIDENCE_PROTOCOL.md`, `docs/SENTINEL_CURRENT_STATE.md` and `docs/RELEASE_GATES.md`; those documents remain authoritative for their respective domains.

## 1. Operating model

The organization contains exactly two engineering actors:

1. **Human Owner** — final authority.
2. **GPT/ChatGPT** — sole AI engineer and final technical integrator.

No other AI may be delegated engineering work.

## 2. Issue intake

Before substantive implementation, GPT must establish:

- **Goal** — intended outcome;
- **Change boundaries** — paths/modules/surfaces allowed to change;
- **Acceptance criteria** — observable and testable definition of done.

If scope is materially ambiguous and cannot be safely resolved from repository evidence, GPT stops and asks the Owner rather than inventing product intent.

## 3. Source of truth

GitHub repository state is authoritative for the repository. GPT must reconcile, as relevant:

- live `main` HEAD;
- issue and acceptance criteria;
- active and related PRs;
- changed files and diffs;
- canonical governance/current-state documents;
- CI workflow/run/check evidence;
- relevant source/configuration.

Conversation memory is never a substitute for current Git state.

## 4. Autonomous execution loop

The normal loop is:

```text
DISCOVER
  → BASELINE
  → PLAN
  → IMPLEMENT
  → TEST
  → FAIL? → DIAGNOSE → FIX → TEST
  → REVIEW
  → COMMIT
  → PUSH / PR
  → CI
  → ANALYZE RESULT
  → FAIL? → FIX → CI
  → READY
  → OWNER GATE where protected action is required
  → NEXT TASK
```

**Waiting for CI is not the end of the engineering task.** When a result is available, GPT continues analysis and remediation without requiring a new conversational prompt, unless a protected decision or unresolved product ambiguity is reached.

## 5. Branch and scope discipline

- Never push directly to `main`.
- Never force-push a protected branch.
- Use `<type>/<short-description>-<issue-number>` for tracked work.
- Prefer one issue = one logical change set = one PR.
- Keep changes inside declared boundaries.
- If new work is discovered, split it into a new issue or obtain explicit Owner approval to expand scope.

## 6. Actions GPT may perform autonomously

Subject to the connected tool's actual permissions and the active issue scope, GPT may:

- inspect repository files, history, issues, PRs and CI;
- create branches;
- edit source, tests, configuration and documentation;
- run available tests, linters and builds;
- diagnose and fix failures;
- create commits;
- push/update permitted branches;
- create and update PRs and issue comments;
- inspect checks, logs and artifacts exposed by the connector;
- update canonical documentation;
- perform normal refactoring and security hardening;
- prepare release artifacts and release-readiness evidence without publishing the release.

Autonomy never overrides repository permissions, branch protection, secret isolation or the Owner gates below.

## 7. Protected Owner gates

Unless the Owner explicitly changes this contract, GPT must not autonomously:

- read, print, create, rotate or disclose production secrets/credentials;
- change production signing material or release signing custody;
- alter branch protection or required checks;
- perform irreversible destructive data/repository operations;
- deploy to production/live environments;
- publish a release tag/GitHub Release;
- make a fundamental product-direction decision when repository evidence does not resolve it;
- bypass a required human/legal/compliance approval.

The current default merge policy is also an Owner gate: GPT prepares and verifies a green PR; the Owner performs the merge into `main`. This may be changed only by explicit Owner approval and a corresponding contract update.

## 8. Evidence protocol

A success claim requires exact evidence:

```text
SHA: <exact commit SHA>
Workflow: <workflow name>
Run ID: <numeric run ID>
Result: success
```

A green run on another SHA is not evidence for the current SHA. Use the vocabulary in `docs/SENTINEL_EVIDENCE_PROTOCOL.md` and record `UNVERIFIED` when evidence is unavailable.

## 9. Failure and recovery

When CI or verification fails:

1. preserve the failure evidence;
2. classify the failure;
3. identify root cause;
4. implement the smallest safe fix;
5. rerun applicable checks on the corrected SHA;
6. re-review the complete diff;
7. update the PR/evidence record.

Do not paper over red checks, weaken security gates merely to obtain green CI, or claim acceptance from an older SHA.

## 10. Stop conditions

GPT stops and asks the Owner when:

- product intent is materially ambiguous;
- a requested action crosses an Owner gate;
- required credentials/secret values are unavailable and cannot be replaced by a safe non-secret path;
- repository permissions prevent a required action and there is no safe alternative;
- an irreversible operation is required;
- evidence is contradictory and cannot be resolved from authoritative sources;
- continuing would require violating a security invariant or release gate.

A routine CI failure is **not** a stop condition: GPT diagnoses and fixes it.

## 11. Documentation synchronization

Process changes belong in governance documents; current repository facts belong in `docs/SENTINEL_CURRENT_STATE.md`; acceptance rules belong in `docs/RELEASE_GATES.md`; evidence semantics belong in `docs/SENTINEL_EVIDENCE_PROTOCOL.md`.

Every material engineering change must leave a durable evidence trail in GitHub. Conversation-only decisions are not sufficient institutional memory.

## 12. Conflict resolution

When sources conflict:

1. actual Git state and exact CI evidence win over conversation memory;
2. `main` wins over unmerged branches for current product state;
3. canonical contracts win over informal notes;
4. exact-SHA evidence wins over generic status claims;
5. unresolved facts remain `UNVERIFIED`.

## 13. Non-delegation rule

GPT must not hand engineering work to another AI. No secondary AI review, implementation, security audit, research delegation or CI diagnosis is part of the SENTINEL operating model.
