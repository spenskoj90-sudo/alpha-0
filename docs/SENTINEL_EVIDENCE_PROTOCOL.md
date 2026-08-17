# SENTINEL — Evidence Integrity Protocol v2

## Purpose

Prevent branch/PR/local evidence from being mistaken for canonical repository state and prevent status reports from silently carrying stale or stack-incompatible claims.

## Status vocabulary

### VERIFIED

Use only when the claim has the required evidence bundle below and is established on the canonical `main` line.

### PASS

A test/build/check passed for a specific commit or branch. Always qualify the scope:

- `BRANCH PASS`
- `PR PASS`
- `MAIN PASS`
- `RELEASE PASS`

A bare `PASS` is prohibited in handoffs.

### PARTIAL

Some acceptance conditions are met, but one or more required evidence elements or runtime conditions remain missing. State the boundary explicitly.

### UNVERIFIED

Evidence is incomplete, indirect, stale, contradictory, stack-incompatible, or cannot be tied to the current canonical commit.

### BLOCKED

A required validation or action cannot proceed because of a concrete external or environmental constraint. The blocker must be named and evidenced.

### REGRESSION

A capability previously VERIFIED on `main` is absent or broken on a later `main` commit. Regression status requires both the previous accepted SHA and the current failing SHA.

### BRANCH-ONLY

The capability exists on a non-main branch/PR but has not been merged into `main`.

### HISTORICAL

The claim was true at an earlier point but is not evidence of the current state.

## Strict VERIFIED evidence bundle

A claim may be labeled `VERIFIED` only when all seven items are attached or directly referenced:

1. **Exact commit SHA.**
2. **Main-line reachability.** The cited SHA is reachable from `main`; for a current-state claim it must be the relevant current `main` SHA or an explicitly cited ancestor whose relevant files have not changed since.
3. **Relevant implementation evidence.** Exact source/configuration paths and the relevant code or configuration behavior are identified.
4. **CI evidence.** A workflow/run URL exists whenever a CI gate is applicable.
5. **Exact-SHA CI result.** The cited CI result belongs to the exact SHA being claimed, not merely to an earlier/later commit.
6. **Test detail.** Test suite/job names and pass/fail detail are provided rather than only saying "green".
7. **Runtime/device evidence.** Required when behavior cannot be established by CI; otherwise explicitly state `N/A — CI-only claim`.

If any item is missing, the status must be `PARTIAL` or `UNVERIFIED`, never `VERIFIED`.

## Pass scope is not equivalent

| Scope | Proves | Does not prove |
|---|---|---|
| `BRANCH PASS` | Checks succeeded on a feature branch | Main integration or current product acceptance |
| `PR PASS` | Checks succeeded for a PR/review state | That the PR was merged or remains valid after main changes |
| `MAIN PASS` | Checks succeeded on a specific main commit | That a later main commit did not break the result |
| `RELEASE PASS` | Release pipeline succeeded for a specific tagged/release commit | Deployment, distribution, or installation unless separately evidenced |

Only `MAIN PASS` and `RELEASE PASS` can satisfy the PASS component of a canonical acceptance claim. Branch and PR passes remain `PARTIAL` until revalidated on `main`.

## Evidence hierarchy

1. Current `main` source/configuration at exact SHA.
2. CI run/check tied to that exact SHA.
3. Runtime/device evidence tied to the same build/commit.
4. Merged PR and review history.
5. Unmerged PR/branch evidence.
6. Human/AI reports, chat history, or descriptions.

Lower levels never override higher levels.

## Stack-correctness rule

Every technical finding must first identify the actual current stack and repository paths. A report that cites files, packages, languages, frameworks, or runtime components absent from the cited `main` tree is not direct evidence and must be downgraded to `UNVERIFIED` until independently reproduced against the real repository.

For the current SENTINEL baseline, the canonical backend stack is Python/FastAPI under `server/`. Go-specific paths or Go middleware claims cannot be accepted as evidence for the Python/FastAPI runtime without a separately verified Go component on `main`.

## Contradictions

When agents disagree, inspect the actual `main` ref and exact files. Do not resolve contradictions using memory, prior reports, branch descriptions, or PR prose.

A report can be useful as a hypothesis even when its finding is not verified. Hypotheses must be labeled accordingly and independently reproduced before implementation.

## Required handoff fields

Every engineering handoff ends with:

- AI / role
- mission
- baseline SHA
- scope
- result
- confidence
- VERIFIED items with the seven-part evidence bundle
- PARTIAL items
- UNVERIFIED items
- BRANCH-ONLY items
- REGRESSIONS with both SHAs
- blockers
- decisions required

## Stale evidence handling

Evidence is stale when:

- it references a commit no longer reachable from current `main`,
- it references an unmerged branch,
- a later `main` commit changed relevant files,
- the CI run belongs to a different SHA,
- runtime/configuration dependencies changed,
- or the underlying stack/path no longer matches the report.

Stale evidence must be revalidated before reuse.

## Regression handling

When an accepted feature disappears from `main`:

1. stop feature implementation work on that item;
2. classify it as `REGRESSION`;
3. identify the last accepted SHA and evidence;
4. identify the first known SHA where it disappeared/broke;
5. determine whether the change was intentional;
6. require Human Owner decision before reimplementation if scope or architecture changed.

Required format:

```text
REGRESSION:
FEATURE:
PREVIOUSLY VERIFIED AT: <SHA>, <CI/run evidence>, <date>
CURRENT MAIN HEAD: <SHA>
CURRENT STATE: absent / failing / contradicted
LIKELY CAUSE: not-merged / reverted / overwritten / never-actually-on-main / unknown
REQUIRES: Human Owner decision before reimplementation
```

## Main-branch acceptance

A feature is not complete merely because its branch builds. Canonical acceptance requires:

`implementation on main + exact-head MAIN PASS + required runtime evidence = accepted`

## Repository hygiene rule

One authoritative `main` branch. Feature work happens in short-lived branches with a PR. Dated diagnostic branches are temporary. Once a branch is classified as obsolete and its useful commits are preserved or merged, it should be deleted by an authorized repository administrator.
