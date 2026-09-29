# SENTINEL — AI Orchestration Routing Guide

**Status:** ACTIVE
**Effective:** 2026-09-29
**Authority:** AI_ORCHESTRATION_OPERATING_SYSTEM.md
**Tracking issue:** #377

## Objective

Use secondary agents only where they materially reduce wall-clock time, expand independent coverage, provide a needed specialist surface, or expose different failure modes. GPT/ChatGPT remains the sole Owner-facing orchestrator.

## Default routing matrix

| Task shape | Default execution |
|---|---|
| Small, sequential, same-file | Single GPT |
| Auth, authorization, RLS, migrations, release lineage | Single primary writer plus optional read-only independent review |
| Broad audit or research | Single GPT first; add up to 2 bounded workers only when sectioning has measurable value |
| Independent Android/Web/Site/Companion changes | Isolated workers/worktrees, serial integration |
| Independent tests/docs/evidence | Parallel workers only when they do not duplicate discovery/context work |
| CI failure with several plausible causes | Parallel hypothesis investigation, one writer applies fix |
| High-risk code review | Primary review plus optional different-model adversarial review |
| UX/design critique | Independent reviewer may use a different model family |
| Shared cross-cutting refactor | Single writer unless file ownership is proven disjoint |
| Release/production action | GPT prepares evidence; Owner gate remains |

## External-model rule

Different model families are optional diversity/review tools, not the default source of repository mutations and never an independent Owner-facing channel.

Never use majority vote as proof. A reviewer claim becomes actionable only after source, test, or runtime evidence supports it.

## Parallel implementation contract

Each writing lane declares:
- issue/task;
- base SHA;
- owned files or subsystem;
- acceptance checks;
- branch/worktree identity;
- dependencies on other lanes.

A lane that discovers it must edit another lane's owned files stops writing and reports the dependency to the coordinator.

## Integration queue

Finished lanes do not merge themselves.

GPT final integrator:
1. chooses landing order;
2. refreshes against current main;
3. reconciles dependency drift;
4. reruns applicable validation;
5. opens or updates the PR;
6. verifies required checks on exact PR HEAD;
7. merges only after canonical merge gate passes.

## Efficiency measurement

Do not claim a productivity percentage without measured project data.

When secondary-agent use is material, record:
- start/end timestamps per lane;
- total parallel wall-clock;
- sequential-equivalent estimate;
- credits/tokens when available;
- retries and failed attempts;
- conflict/rebase count;
- CI reruns;
- defects found by independent review and confirmed by executable evidence.

Keep secondary-agent routing only for task classes where the evidence supports it. If coordination/token/credit/rework cost exceeds the benefit, route the next comparable task to one GPT-led pass.
