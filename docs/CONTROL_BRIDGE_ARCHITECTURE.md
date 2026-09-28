# SENTINEL Control Bridge Architecture

**Status:** ACTIVE FOUNDATION  
**Tracking issue:** #382

SENTINEL uses a small Streamable HTTP MCP service as its project-specific evidence/control adapter.

The bridge does not replace GitHub, Render, Neon, PostHog, Google Drive or other authoritative systems. It normalizes high-frequency facts into compact schemas so agents spend fewer tool calls and tokens rediscovering the same state.

## Boundaries

- production repository and live providers remain authoritative;
- responses are bound to deployed `SENTINEL_SOURCE_SHA`;
- secret values are never returned;
- user-visible readiness remains governed by `USER_VISIBLE_ACCEPTANCE_CONTRACT.md`;
- remote MCP access is bearer-authenticated and fails closed;
- initial tools are read-only;
- production deployment remains Owner-gated.

## OpenAI integration

OpenAI Agents/Responses can consume a remote MCP server. The bridge itself does not need an OpenAI API key. The consuming orchestrator owns API credentials, model routing, approvals, tracing and caching.
