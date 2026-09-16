from __future__ import annotations

import os

from app.core.database_security import validate_database_url
from app.core.request_limits import RequestBodyLimitMiddleware, request_body_limit_from_env

_environment = os.getenv("SENTINEL_ENV", "development").lower()
validate_database_url(os.getenv("DATABASE_URL"), _environment)

from app.main import app as core_app  # noqa: E402

app = RequestBodyLimitMiddleware(core_app, max_body_bytes=request_body_limit_from_env())
