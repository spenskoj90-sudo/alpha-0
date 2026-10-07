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

## Summary evidence limits

`provider_state` reports only whether canonical configuration names are present in the **Bridge process environment**. It does not prove that Core has credentials, that a provider is enabled, or that delivery works. `providerEnablementVerified=false` is explicit; query Core/provider-native evidence for those claims. No credential copying into Bridge is required. Resend/Brevo/Stripe/PostHog/Google use the same names as Core; values are never serialized.

`release_readiness` is a repository checklist summary. `checklistSatisfied` describes metadata only; `releaseReady=false` and `releaseEvidence.status=UNVERIFIED` remain until a separate exact-candidate canonical validator verifies signed bytes and protected-main attestations. Use `scripts/verify_final_release_acceptance_live.sh` and the final acceptance workflow for release evidence. Editing TASKS or UX flags cannot establish release acceptance.

## OpenAI integration

OpenAI Agents/Responses can consume a remote MCP server. The bridge itself does not need an OpenAI API key. The consuming orchestrator owns API credentials, model routing, approvals, tracing and caching.
