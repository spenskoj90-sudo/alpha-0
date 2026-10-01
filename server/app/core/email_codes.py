from __future__ import annotations

import re
from app.core.auth import hash_password

EMAIL_CODE_TTL_SECONDS = 900
EMAIL_CODE_MAX_ATTEMPTS = 5
EMAIL_CODE_REQUESTS_PER_HOUR = 3
EMAIL_CODE_PATTERN = re.compile(r"[0-9]{8}")
# Non-secret work factor for unknown, expired or exhausted challenges.
DUMMY_CODE_HASH = hash_password("00000000")


def normalize_action_code(value: str) -> str:
    compact = "".join(value.split())
    return compact if EMAIL_CODE_PATTERN.fullmatch(compact) else value.strip()
