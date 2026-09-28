# Control Bridge scoped agent instructions

Scope: `control-bridge/`.

- Follow root `AGENTS.md`.
- This is an evidence/control adapter, not a second source of truth.
- Return compact normalized state instead of raw provider payloads.
- Never serialize secrets, bearer tokens, credential-bearing database URLs, or provider credentials.
- Remote MCP traffic fails closed without a valid `SENTINEL_BRIDGE_TOKEN`.
- Initial tools are read-only. Future mutations require explicit allowlists and existing Owner/security gates.
- `OPENAI_API_KEY` belongs to the consuming orchestrator, not the bridge.
- Validate with install + compileall + pytest.
