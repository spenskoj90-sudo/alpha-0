from __future__ import annotations

import json
import math
from typing import Any


def validate_bounded_json(
    value: Any,
    *,
    max_bytes: int,
    max_depth: int = 8,
    max_nodes: int = 4096,
    max_key_bytes: int = 128,
    max_string_bytes: int = 16_384,
) -> Any:
    """Validate decoded JSON without recursive traversal or implicit coercion."""
    if min(max_bytes, max_depth, max_nodes, max_key_bytes, max_string_bytes) <= 0:
        raise ValueError("JSON_LIMIT_CONFIGURATION_INVALID")

    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > max_nodes:
            raise ValueError("JSON_NODE_LIMIT")
        if depth > max_depth:
            raise ValueError("JSON_DEPTH_LIMIT")

        if current is None or isinstance(current, bool):
            continue
        if isinstance(current, int):
            continue
        if isinstance(current, float):
            if not math.isfinite(current):
                raise ValueError("JSON_NUMBER_INVALID")
            continue
        if isinstance(current, str):
            if len(current.encode("utf-8")) > max_string_bytes:
                raise ValueError("JSON_STRING_LIMIT")
            continue
        if isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
            continue
        if isinstance(current, dict):
            for key, item in current.items():
                if not isinstance(key, str):
                    raise ValueError("JSON_KEY_INVALID")
                if len(key.encode("utf-8")) > max_key_bytes:
                    raise ValueError("JSON_KEY_LIMIT")
                stack.append((item, depth + 1))
            continue
        raise ValueError("JSON_TYPE_INVALID")

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("JSON_ENCODING_INVALID") from exc
    if len(encoded) > max_bytes:
        raise ValueError("JSON_BYTE_LIMIT")
    return value
