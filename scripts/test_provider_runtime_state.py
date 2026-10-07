#!/usr/bin/env python3
from __future__ import annotations

import sys
import re
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
    provider_matrix = read("docs/PROVIDER_STATUS_MATRIX.md")
    federated = read("docs/FEDERATED_AUTH_V1.md")
    free_strategy = read("docs/FREE_TESTING_INFRASTRUCTURE_STRATEGY.md")

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
        require("Resend" in document and "Brevo" in document and "staging" in document, f"{document_name} records staging-only multi-provider email boundary")
        require("transaction-local" in document and "FORCE RLS" in document, f"{document_name} records transaction-local RLS service role")

    for phrase in (
        "Stripe pre-release billing",
        "PostHog staging telemetry",
        "Transactional email boundary",
        "PgBouncer service-role boundary",
    ):
        require(phrase in provider, f"provider contract retains {phrase}")

    require("production deployment" in provider, "provider contract preserves production non-claim")
    require("live charges" in provider, "provider contract preserves live-charge non-claim")
    require("prod_VKsUERZXQrdT93" in provider and "livemode=false" in provider, "provider contract records sandbox-only Stripe catalog")
    require("price_1UKCjxHDnOpHCmiXzQg7aFXf" in provider, "provider contract records exact non-live Core Plus price")
    require("credential-manager-siwg" in federated, "federated contract links current Google Credential Manager guidance")
    require("core.telegram.org/bots/telegram-login" in federated, "federated contract links current Telegram OIDC guidance")
    require("zero-cost" in provider_matrix.lower(), "provider matrix records zero-cost pre-release posture")
    require("artifact" in provider_matrix.lower() and "VK application identity" in provider_matrix, "provider matrix records Android provider identity binding")
    require("## Canonical acceptance queue" in tasks and "#371" in tasks and "#314" in tasks and "#375" in tasks and "#277" in tasks and "#315" in tasks and "#316" in tasks and "#317" in tasks, "task board exposes one issue-linked acceptance queue")
    acceptance = tasks.split("## Canonical acceptance queue", 1)[-1].split("\n## ", 1)[0]
    acceptance_ids = re.findall(r"^- \[ \] \*\*#(\d+)\b", acceptance, re.M)
    require(sorted(acceptance_ids) == sorted(('371', '314', '375', '277', '315', '316', '317')),
            "acceptance section has exactly seven non-duplicated active issue gates; engineering queue is independent")
    require("Render Free" in free_strategy and "Stripe test/sandbox mode" in free_strategy, "free strategy keeps test infrastructure distinct from production")

    print(f"\nPROVIDER_STATE_PASSED={passed} PROVIDER_STATE_FAILED={len(failures)}")
    if failures:
        print("Provider runtime state violations:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
