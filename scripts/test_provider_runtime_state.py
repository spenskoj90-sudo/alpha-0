#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    passed = 0

    def require(condition: bool, message: str) -> None:
        nonlocal passed
        if condition:
            passed += 1
            print(f"PASS  {message}")
        else:
            failures.append(message)
            print(f"FAIL  {message}")

    tasks = read("docs/TASKS.md")
    current = read("docs/SENTINEL_CURRENT_STATE.md")
    provider = read("docs/PROVIDER_SANDBOX_INTEGRATION_V1.md")

    for path in (
        "server/app/core/database_engine.py",
        "server/app/core/stripe_billing.py",
        "server/app/core/posthog_telemetry.py",
        "server/app/core/email_provider.py",
        "web/app/api/billing/checkout-sessions/route.ts",
    ):
        require((ROOT / path).is_file(), f"provider runtime implementation exists: {path}")

    stale_claims = (
        "does **not** claim Stripe",
        "not a claim of Stripe or another vendor-specific wire protocol",
        "PostHog delivery is disabled",
        "There is no PostHog SDK, credential or external delivery path",
    )
    for claim in stale_claims:
        require(claim not in tasks + current, f"orientation docs reject stale claim: {claim}")

    require("Stripe Billing adapter" in tasks, "task board records concrete Stripe adapter")
    require("/v1/billing/checkout-sessions" in current, "current-state guide records server-owned paid checkout")
    require("Stripe-Signature" in current, "current-state guide records native Stripe webhook verification")

    for document_name, document in (("TASKS", tasks), ("CURRENT_STATE", current)):
        require("PostHog" in document and "staging" in document, f"{document_name} records staging-only PostHog boundary")
        require("Resend" in document and "staging" in document, f"{document_name} records staging-only Resend boundary")
        require("transaction-local" in document and "FORCE RLS" in document, f"{document_name} records transaction-local RLS service role")

    for phrase in (
        "Stripe pre-release billing",
        "PostHog staging telemetry",
        "Resend email boundary",
        "PgBouncer service-role boundary",
    ):
        require(phrase in provider, f"provider contract retains {phrase}")

    require("production deployment" in provider, "provider contract preserves production non-claim")
    require("live charges" in provider, "provider contract preserves live-charge non-claim")

    print(f"\nPROVIDER_STATE_PASSED={passed} PROVIDER_STATE_FAILED={len(failures)}")
    if failures:
        print("Provider runtime state violations:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
