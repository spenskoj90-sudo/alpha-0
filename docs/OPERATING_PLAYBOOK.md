# SENTINEL — Operating Playbook

**Issue:** #134  
**Status:** Canonical workflow reference.  
**Authority:** Human Owner is the final authority for merge, deploy, credentials/secrets, releases, branch protection, destructive operations, and final product acceptance.

This playbook describes how SENTINEL engineering work is performed under `docs/WORKFLOW_CONTRACT.md`. The repository state on `main` is authoritative; conversation memory is not.

## 1. Roles

### GPT / ChatGPT — primary executor and final integrator

GPT performs the normal SENTINEL engineering lifecycle:

- inspect the live repository state;
- read and reconcile issues, PRs, commits, diffs and authoritative documents;
- define and validate scope;
- make architecture and technical decisions;
- implement normal code and documentation changes;
- write and repair tests;
- inspect CI and exact-SHA evidence;
- review PRs and regressions;
- synchronize documentation and current-state records;
- prepare changes for Human Owner acceptance/merge.

GPT has direct repository inspection and, where the connector permits it, repository write capability within the explicit scope of the active issue. This capability does not include access to credentials/secrets or authority over protected Owner actions.

### Grok — exceptional secondary executor

Grok is used only when the task is genuinely large, multi-stage, or architecturally substantial enough that delegation materially improves execution. Grok is not the default executor.

A Grok handoff must use the issue/task contract and must include exact file boundaries, acceptance criteria, protected-action prohibitions, and exact-SHA/CI evidence requirements.

### Human Owner — final authority

The Owner retains final authority for:

- merge into `main`;
- production deployment;
- creation/rotation/use of credentials, secrets and signing material;
- release tags and GitHub Releases;
- branch protection and required status checks;
- destructive repository cleanup;
- final product acceptance.

Agents may recommend these actions but do not perform them.

## 2. Current-state inspection

Before substantive work, GPT independently checks:

1. current `main` HEAD;
2. the exact issue body and acceptance criteria;
3. related open/merged PRs and branches;
4. `docs/WORKFLOW_CONTRACT.md`;
5. `docs/SENTINEL_CURRENT_STATE.md`;
6. `docs/RELEASE_GATES.md`;
7. `docs/SENTINEL_EVIDENCE_PROTOCOL.md`;
8. other task-relevant repository documentation and source.

The Human Owner does not need to paste a fresh `SENTINEL_CURRENT_STATE.md` when GPT can retrieve it directly. If the repository source cannot be inspected or evidence is unavailable, the affected fact is recorded as **UNVERIFIED** rather than inferred.

## 3. Normal engineering cycle

1. **Intake** — identify Goal, Change boundaries and Acceptance criteria.
2. **Inspect** — establish the exact current `main` baseline and relevant repository state.
3. **Plan** — choose the smallest coherent change set and verify non-goals.
4. **Branch** — work from current `main` using `<type>/<short-description>-<issue-number>`.
5. **Implement** — change only the declared scope.
6. **Verify** — run the applicable tests/checks and inspect their exact-SHA evidence.
7. **Review** — inspect the diff for scope drift, regressions, security issues and documentation impact.
8. **Synchronize** — update `README.md` and `docs/SENTINEL_CURRENT_STATE.md` when required by the Workflow Contract.
9. **PR** — open/update the PR with the exact logical change set and evidence.
10. **Owner gate** — Human Owner independently verifies `gh pr checks <PR> -R spenskoj90-sudo/alpha-0` against the exact PR head SHA and decides whether to merge.
11. **Post-merge** — re-read `main` and reconcile current-state documentation before starting the next substantive issue.

## 4. Scope discipline

- One issue = one logical change set = one PR.
- Do not silently expand file boundaries.
- If new work is discovered, create a separate issue or explicitly amend the current scope before implementation continues.
- Do not mix unrelated cleanup into an active issue.

## 5. Evidence discipline

Never treat a textual statement such as "done", "tests passed", or "CI green" as proof.

For CI/test acceptance, preserve:

- exact commit SHA;
- workflow name;
- numeric GitHub Actions Run ID;
- result/conclusion;
- relevant artifact or log evidence where required.

A green run on another SHA is not evidence for the current SHA. Use the status vocabulary from `docs/SENTINEL_EVIDENCE_PROTOCOL.md`, including **UNVERIFIED** where evidence is incomplete.

## 6. Security and protected actions

No agent may:

- read, print, modify, create or rotate credentials/secrets;
- access decrypted secret contents;
- alter signing keys/certificates or protected release signing configuration;
- merge into `main`;
- deploy to production or another live environment;
- create a release tag/GitHub Release;
- change branch protection or required status checks;
- perform destructive protected-branch operations.

Repository inspection must remain within the public/repository data exposed by the authorized connector. Secret values are never part of normal engineering evidence.

## 7. Grok delegation protocol

Delegate to Grok only when the task is genuinely large-scale. The handoff must state:

```text
ЗАДАНИЕ ДЛЯ GROK — Issue #<номер>

Исполнитель: Grok
Цель: <узкая формулировка>
Границы файлов: <конкретный список>
Запрещено: merge в main, deploy, изменение/чтение credentials и secrets
Обязательно по завершении:
1. Обновить docs/SENTINEL_CURRENT_STATE.md — новый HEAD, статус issue
2. Прислать отчёт: номер PR, точный SHA, ссылки на CI run ID для каждой обязательной проверки
Критерий приёмки: <конкретно, проверяемо>
```

After Grok reports completion, GPT independently verifies the reported PR, exact SHA, changed files and CI evidence. A textual completion claim is never sufficient.

## 8. Documentation as institutional memory

The repository is the durable record of engineering decisions. When a process, architecture, security invariant, capability, or acceptance rule changes, update the authoritative document rather than relying on conversation history.

At minimum:

- workflow/process changes → `docs/WORKFLOW_CONTRACT.md` and this playbook;
- canonical product/repository state → `docs/SENTINEL_CURRENT_STATE.md`;
- release/CI acceptance changes → `docs/RELEASE_GATES.md`;
- evidence semantics → `docs/SENTINEL_EVIDENCE_PROTOCOL.md`;
- user-facing repository orientation → `README.md`.

## 9. Conflict resolution

When information conflicts:

1. actual Git state/PR/commit evidence wins over conversation memory;
2. `main` wins over unmerged historical branches for current product state;
3. authoritative contracts win over informal notes;
4. exact-SHA evidence wins over generic status claims;
5. unresolved facts remain **UNVERIFIED** until independently established.

## 10. Current operating principle

**GPT is the normal engineering path. Grok is the exception for exceptional scale. Human Owner is the final authority. GitHub/main is the current-state source of truth. Evidence is tied to exact SHA. Secrets remain outside agent workflows.**
