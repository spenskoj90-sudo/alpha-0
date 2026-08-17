# SENTINEL — Evidence Integrity Protocol v1

## Purpose

Prevent branch/PR/local evidence from being mistaken for canonical repository state.

## Status vocabulary

### VERIFIED

Use only when implementation, exact commit on `main`, applicable CI evidence, and required runtime evidence are all established.

### PASS

A test/build/check passed for a specific commit or branch. Always qualify the scope:

- `BRANCH PASS`
- `PR PASS`
- `MAIN PASS`
- `RELEASE PASS`

A bare `PASS` is prohibited in handoffs.

### UNVERIFIED

Evidence is incomplete, indirect, stale, contradictory, or cannot be tied to the current canonical commit.

### BLOCKED

A required validation or action cannot proceed because of a concrete external or technical blocker. The blocker must be named and evidenced.

### REGRESSION

A capability previously accepted on `main` is absent or broken on a later `main` commit. Regression status requires the previous accepted SHA and current failing SHA.

### BRANCH-ONLY

The capability exists on a non-main branch/PR but has not been merged into `main`.

### HISTORICAL

The claim was true at an earlier point but is not evidence of the current state.

## Evidence hierarchy

1. Current `main` source/configuration at exact SHA.
2. CI run/check tied to that exact SHA.
3. Runtime/device evidence tied to the same build/commit.
4. Merged PR and review history.
5. Unmerged PR/branch evidence.
6. Human/AI reports, chat history, or descriptions.

Lower levels never override higher levels.

## Required handoff fields

Every engineering handoff ends with:

- AI / role
- mission
- baseline SHA
- scope
- result
- confidence
- VERIFIED items with exact paths/SHA/CI evidence
- UNVERIFIED items
- BRANCH-ONLY items
- REGRESSIONS
- blockers
- decisions required

## Main-branch acceptance

A feature is not complete merely because its branch builds. Acceptance requires:

`implementation on main + exact-head CI + required runtime evidence = accepted`

## Contradictions

When agents disagree, inspect the actual `main` ref and exact files. Do not resolve contradictions using memory, prior reports, or PR descriptions.

## Stale evidence

Evidence must be treated as stale when:

- it references a commit no longer reachable from the current main lineage,
- it references an unmerged branch,
- a later main commit changed the relevant implementation,
- the CI run was for a different SHA,
- or runtime/configuration dependencies changed.

## Regression handling

When an accepted feature disappears from main:

1. stop feature implementation work on that item;
2. classify it as `REGRESSION`;
3. identify the last accepted SHA;
4. identify the first known SHA where it disappeared/broke;
5. determine whether the change was intentional;
6. require Human Owner decision before reimplementation if scope or architecture changed.

## Repository hygiene rule

One authoritative `main` branch. Feature work happens in short-lived branches with a PR. Dated diagnostic branches are temporary. Once a branch is classified as obsolete and its useful commits are preserved or merged, it should be deleted by an authorized repository administrator.
