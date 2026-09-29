from __future__ import annotations

import contextlib
import hmac
import os

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from sentinel_bridge.state import design_state, project_state, provider_state, release_readiness, runtime_health, source_sha

mcp = MCPServer("SENTINEL Control Bridge")

@mcp.tool()
def sentinel_project_state() -> dict:
    """Return compact exact-build, design and user-visible product state."""
    return project_state()

@mcp.tool()
def sentinel_runtime_health() -> dict:
    """Probe configured SENTINEL Core and Web runtime endpoints."""
    return runtime_health()

@mcp.tool()
def sentinel_provider_state() -> dict:
    """Return provider configuration booleans without exposing secret values."""
    return provider_state()

@mcp.tool()
def sentinel_release_readiness() -> dict:
    """Return active acceptance gates and Owner-visible release-readiness state."""
    return release_readiness()

@mcp.tool()
def sentinel_design_state() -> dict:
    """Return production design-reference synchronization state."""
    return design_state()

async def healthz(request):
    return JSONResponse({"status":"ok","service":"sentinel-control-bridge","sourceSha":source_sha()})

class BearerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") == "/healthz":
            await self.app(scope, receive, send)
            return
        expected = os.getenv("SENTINEL_BRIDGE_TOKEN", "")
        if not expected:
            response = JSONResponse({"error":"bridge authentication is not configured"}, status_code=503)
            await response(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw = headers.get(b"authorization", b"").decode("latin1")
        supplied = raw[7:] if raw.startswith("Bearer ") else ""
        if not hmac.compare_digest(supplied, expected):
            response = JSONResponse({"error":"unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

mcp_app = mcp.streamable_http_app(json_response=True, stateless_http=True)

@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield

app = Starlette(
    routes=[
        Route("/healthz", endpoint=healthz, methods=["GET"]),
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan,
)
app = BearerAuthMiddleware(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
