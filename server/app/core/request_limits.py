from __future__ import annotations

import json
import os
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

ASGIApp = Callable[[dict[str, Any], Callable[[], Awaitable[dict[str, Any]]], Callable[[dict[str, Any]], Awaitable[None]]], Awaitable[None]]
DEFAULT_MAX_REQUEST_BODY_BYTES = 1_048_576
MIN_REQUEST_BODY_BYTES = 65_536
MAX_REQUEST_BODY_BYTES = 8_388_608


class RequestBodyTooLarge(Exception):
    pass


def request_body_limit_from_env(value: str | None = None) -> int:
    raw = value if value is not None else os.getenv("MAX_REQUEST_BODY_BYTES", str(DEFAULT_MAX_REQUEST_BODY_BYTES))
    try:
        limit = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("MAX_REQUEST_BODY_BYTES must be an integer") from exc
    if not MIN_REQUEST_BODY_BYTES <= limit <= MAX_REQUEST_BODY_BYTES:
        raise RuntimeError("MAX_REQUEST_BODY_BYTES is outside the allowed safety range")
    return limit


def _request_id(scope: dict[str, Any]) -> str:
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == b"x-request-id":
            try:
                value = raw_value.decode("ascii")
            except UnicodeDecodeError:
                break
            if 0 < len(value) <= 128 and all(32 <= ord(ch) < 127 for ch in value):
                return value
            break
    return str(uuid.uuid4())


class RequestBodyLimitMiddleware:
    """Bound HTTP request bodies before framework JSON/form parsing."""

    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        if not MIN_REQUEST_BODY_BYTES <= max_body_bytes <= MAX_REQUEST_BODY_BYTES:
            raise ValueError("INVALID_REQUEST_BODY_LIMIT")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        content_length: int | None = None
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                content_length = int(value.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                await self._reject(scope, send, 400, "INVALID_CONTENT_LENGTH")
                return
            if content_length < 0:
                await self._reject(scope, send, 400, "INVALID_CONTENT_LENGTH")
                return
            break
        if content_length is not None and content_length > self.max_body_bytes:
            await self._reject(scope, send, 413, "REQUEST_BODY_TOO_LARGE")
            return

        consumed = 0
        response_started = False

        async def limited_receive() -> dict[str, Any]:
            nonlocal consumed
            message = await receive()
            if message.get("type") == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    raise RequestBodyTooLarge
            return message

        async def tracked_send(message: dict[str, Any]) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except RequestBodyTooLarge:
            if response_started:
                raise
            await self._reject(scope, send, 413, "REQUEST_BODY_TOO_LARGE")

    @staticmethod
    async def _reject(scope: dict[str, Any], send: Callable, status: int, code: str) -> None:
        payload = json.dumps(
            {"code": code, "message": "Request rejected", "request_id": _request_id(scope)},
            separators=(",", ":"),
        ).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": payload})
