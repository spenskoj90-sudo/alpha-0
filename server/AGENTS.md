# Core scoped agent instructions

Review focus: server-authoritative entitlements, tenant/RLS isolation, migration/runtime role
separation, exact OAuth callbacks and audience, nonce/PKCE/replay, concurrent idempotency,
bounded consent and stale-state denial. AI/knowledge/catalog metadata grants no action authority.

Scope: server/ plus migrations and directly required contracts/tests.

- Follow root AGENTS.md.
- Auth, authorization, RLS, sessions, migrations, entitlements, and release/security invariants default to a single primary writer.
- Secondary agents may independently inspect or propose tests; no majority-vote security decisions.
- Preserve default deny and server-authoritative state.
- Never expose production credentials or weaken validation for green CI.
- Default validation uses the pinned Python environment and applicable pytest/Core/PostgreSQL coverage gates.
- PostgreSQL behavior must be tested against the repository's supported major-version contract when persistence changes.
