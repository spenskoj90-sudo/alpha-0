# SENTINEL — Execution Routing Guide

**Status:** ACTIVE
**Effective:** 2026-09-29
**Authority:** `AI_ORCHESTRATION_OPERATING_SYSTEM.md`

## Goal

Minimize wall-clock time, token/credit use and Owner interruptions without reducing security or evidence quality.

## Routing matrix

| Task shape | Default route |
|---|---|
| Focused repo/service task | GPT + connected tool directly |
| Small/sequential/shared-file task | Single GPT writer |
| Auth, authorization, RLS, migrations, release lineage | Single GPT writer + optional read-only review |
| Long multi-step/browser/authenticated-site task | ChatGPT Work |
| Repository-local coding/testing needing dedicated compute | Codex / bounded same-family worker |
| Broad independent research | 2–4 bounded workers only when synthesis cost is justified |
| Independent Android/Web/Site/Companion lanes | Isolated workers, serial GPT integration |
| CI failure with multiple independent hypotheses | Parallel investigation, one writer fixes |
| Security/architecture challenge | Optional independent read-only reviewer |
| UX/design exploration | Lovable/Figma or independent reviewer under GPT control |
| Prototype/execution sandbox | Replit under GPT control |
| Release/production action | GPT prepares evidence; Owner gate remains |

## External-model rule

Different model families are optional diversity tools, not default engineers.

Use them only when scope is bounded, expected benefit is specific, least-privilege context is enough, protected credentials are unnecessary, and GPT will independently validate the result.

Default to read-only. External write work must be isolated and reviewed before production translation.

## Chat vs Work vs Codex

- **Chat:** focused decisions, connectors, repository/service actions, PR/CI/evidence.
- **Work:** long-running multi-step execution, cloud browser, authenticated websites, visual/browser acceptance, finished deliverables.
- **Codex:** repository-local implementation/debug/test execution when that environment materially helps.

Do not bounce the Owner between modes unnecessarily. When a mode switch is unavoidable, provide one complete copy-ready task with all context and acceptance criteria.

## Cost/latency rule

Parallelism is justified only when its expected wall-clock or independent-coverage gain exceeds duplicated context, extra credits, conflict risk, extra CI reruns and synthesis overhead.

No audit-of-the-audit loops. Reuse valid evidence and fix root causes in the same pass where practical.
