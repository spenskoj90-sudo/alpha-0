"""Character and game catalog read routes (issue #107 Phase 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from fastapi import FastAPI, Header, HTTPException, Request

from app.core.entitlements import EntitlementStatus
from app.core.game_catalog import DIABLO_CATALOG, get_game
from app.core.security import Principal


def install_game_state_routes(
    app: FastAPI,
    *,
    store: Any,
    principal_from_token: Callable[[str], Principal],
    require_bearer: Callable[[str], str],
    authorize_request: Callable[[Principal, str, str, str], None],
    request_id: Callable[..., str],
) -> None:
    @app.get("/v1/characters")
    def list_characters(
        request: Request,
        authorization_header: str = Header(..., alias="Authorization"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ) -> dict[str, list[dict[str, Any]]]:
        rid = request_id(request, x_request_id)
        principal = principal_from_token(require_bearer(authorization_header))
        authorize_request(principal, "character:read", "character:*", rid)
        return {"characters": store.list_characters(principal.user_id)}

    @app.get("/v1/characters/{character_id}")
    def get_character(
        character_id: str,
        request: Request,
        authorization_header: str = Header(..., alias="Authorization"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ) -> dict[str, Any]:
        rid = request_id(request, x_request_id)
        principal = principal_from_token(require_bearer(authorization_header))
        authorize_request(principal, "character:read", f"character:{character_id}", rid)
        item = store.get_character(character_id)
        if not item:
            raise HTTPException(status_code=404, detail="CHARACTER_NOT_FOUND")
        if item.get("user_id") != principal.user_id:
            raise HTTPException(status_code=403, detail="CHARACTER_SCOPE_MISMATCH")
        return item

    @app.get("/v1/games")
    def list_games(
        request: Request,
        authorization_header: str = Header(..., alias="Authorization"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ) -> dict[str, list[dict[str, Any]]]:
        rid = request_id(request, x_request_id)
        principal = principal_from_token(require_bearer(authorization_header))
        authorize_request(principal, "game:read", "game:*", rid)
        games = [
            {
                "id": game.id,
                "name": game.name,
                "family": game.family,
                "platform": game.platform.value,
                "versioning": game.versioning,
                "launcher_supported": game.launcher_supported,
                "interaction_mode": game.interaction_mode,
            }
            for game in DIABLO_CATALOG
        ]
        return {"games": games}

    @app.get("/v1/games/{game_id}")
    def get_game_detail(
        game_id: str,
        request: Request,
        authorization_header: str = Header(..., alias="Authorization"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ) -> dict[str, Any]:
        rid = request_id(request, x_request_id)
        principal = principal_from_token(require_bearer(authorization_header))
        authorize_request(principal, "game:read", f"game:{game_id}", rid)
        game = get_game(game_id)
        if game is None:
            raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
        return {
            "id": game.id,
            "name": game.name,
            "family": game.family,
            "platform": game.platform.value,
            "versioning": game.versioning,
            "launcher_supported": game.launcher_supported,
            "interaction_mode": game.interaction_mode,
        }

    @app.get("/v1/games/{game_id}/access")
    def get_game_access(
        game_id: str,
        request: Request,
        authorization_header: str = Header(..., alias="Authorization"),
        x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    ) -> dict[str, Any]:
        rid = request_id(request, x_request_id)
        principal = principal_from_token(require_bearer(authorization_header))
        authorize_request(principal, "game:read", f"game:{game_id}", rid)
        game = get_game(game_id)
        if game is None:
            raise HTTPException(status_code=404, detail="GAME_NOT_FOUND")
        now = datetime.now(UTC)
        entitlements = store.list_entitlements(principal.user_id)
        active = []
        for item in entitlements:
            if item.get("game_id") != game_id:
                continue
            status = item.get("status")
            if status not in (EntitlementStatus.ACTIVE, "ACTIVE", EntitlementStatus.ACTIVE.value if hasattr(EntitlementStatus, "ACTIVE") else "ACTIVE"):
                if str(status) != "ACTIVE":
                    continue
            valid_until = item.get("valid_until")
            if valid_until is not None:
                if hasattr(valid_until, "tzinfo") and valid_until.tzinfo is None:
                    valid_until = valid_until.replace(tzinfo=UTC)
                if isinstance(valid_until, datetime) and valid_until < now:
                    continue
            active.append(item)
        return {
            "game_id": game_id,
            "allowed": len(active) > 0,
            "entitlements": active,
        }
