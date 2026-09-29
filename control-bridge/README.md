# SENTINEL Control Bridge

Compact authenticated MCP evidence plane for SENTINEL.

The bridge reduces repeated discovery across providers by returning small, normalized project-specific JSON contracts.

## Transport and security

- MCP Python SDK 2.2.0
- Streamable HTTP
- stateless JSON responses
- bearer authentication for MCP traffic
- public `/healthz` contains no secrets
- read-only initial tool surface
- no secret values are serialized

## Tools

- `sentinel_project_state`
- `sentinel_runtime_health`
- `sentinel_provider_state`
- `sentinel_release_readiness`
- `sentinel_design_state`

## Runtime configuration

Required for a remote deployment:

- `SENTINEL_BRIDGE_TOKEN`
- `SENTINEL_SOURCE_SHA` (optional explicit override; otherwise the bridge resolves Render `RENDER_GIT_COMMIT` or `GITHUB_SHA`)
- `SENTINEL_ENV`
- `SENTINEL_CORE_URL`
- `SENTINEL_WEB_URL`

`OPENAI_API_KEY` is not required by this bridge. It belongs to the agent/orchestrator that consumes the MCP server.

## Validate

```bash
cd control-bridge
python -m pip install -e '.[test]'
python -m compileall -q sentinel_bridge
pytest
```

Remote staging deployment is a separate environment step after merge and must be exact-SHA-bound.
