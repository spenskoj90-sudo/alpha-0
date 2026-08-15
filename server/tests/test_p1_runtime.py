from datetime import UTC, datetime, timedelta

import pytest

from app.core.p1_runtime import (
    BillingRuntime,
    BillingState,
    EntitlementEngine,
    OutboxEvent,
    OutboxManager,
    OutboxStatus,
    WorkerManager,
)


def test_entitlement_engine_is_fail_closed():
    engine = EntitlementEngine()
    now = datetime.now(UTC)
    assert engine.check(None).allowed is False
    assert engine.check({"status": "SUSPENDED", "valid_from": now, "valid_until": now}).reason == "ENTITLEMENT_SUSPENDED"
    assert engine.check({"status": "ACTIVE", "valid_from": now + timedelta(minutes=1), "valid_until": now + timedelta(hours=1)}, now=now).allowed is False
    assert engine.check({"status": "ACTIVE", "valid_from": now - timedelta(minutes=1), "valid_until": now - timedelta(seconds=1)}, now=now).reason == "ENTITLEMENT_EXPIRED"
    assert engine.check({"status": "ACTIVE", "valid_from": now - timedelta(minutes=1), "valid_until": now + timedelta(hours=1)}, now=now).allowed is True


def test_billing_runtime_accepts_only_valid_transitions():
    runtime = BillingRuntime()
    runtime.transition("sub-1", BillingState.ACTIVE, provider="test")
    runtime.transition("sub-1", BillingState.PAST_DUE, provider="test", external_reference="evt-1")
    runtime.transition("sub-1", BillingState.ACTIVE, provider="test", external_reference="evt-2")
    assert runtime.state("sub-1") is BillingState.ACTIVE
    assert [item.current for item in runtime.history("sub-1")] == [BillingState.ACTIVE, BillingState.PAST_DUE, BillingState.ACTIVE]
    with pytest.raises(ValueError, match="INVALID_BILLING_TRANSITION"):
        runtime.transition("sub-1", BillingState.PENDING, provider="test")


def test_outbox_and_worker_retry_then_complete():
    outbox = OutboxManager()
    worker = WorkerManager(outbox)
    outbox.enqueue(OutboxEvent("evt-1", "audit", {"value": 1}))
    attempts = {"count": 0}

    def flaky_handler(_event):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")

    assert worker.process_once("evt-1", flaky_handler) is OutboxStatus.PENDING
    assert outbox.events["evt-1"].attempts == 1
    assert worker.process_once("evt-1", flaky_handler) is OutboxStatus.DONE
    assert outbox.events["evt-1"].attempts == 2


def test_outbox_rejects_duplicate_enqueue_and_invalid_completion():
    outbox = OutboxManager()
    outbox.enqueue(OutboxEvent("evt-2", "audit", {}))
    with pytest.raises(ValueError, match="OUTBOX_DUPLICATE"):
        outbox.enqueue(OutboxEvent("evt-2", "audit", {}))
    with pytest.raises(ValueError, match="OUTBOX_NOT_PROCESSING"):
        outbox.complete("evt-2")
