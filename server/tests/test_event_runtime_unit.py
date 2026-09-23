from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.core.event_runtime import ClaimedEvent, PostgresEventRuntime


def claimed(*, attempts: int = 1) -> ClaimedEvent:
    return ClaimedEvent(
        id="11111111-1111-1111-1111-111111111111",
        event_type="runtime.test",
        payload={"safe": True},
        attempts=attempts,
        locked_by="lease-token",
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"lease_seconds": 0}, "INVALID_RUNTIME_LIMITS"),
        ({"max_attempts": 0}, "INVALID_RUNTIME_LIMITS"),
        ({"backoff_base_seconds": 0}, "INVALID_RUNTIME_LIMITS"),
    ],
)
def test_runtime_rejects_invalid_limits_before_database_open(kwargs, message):
    with pytest.raises(ValueError, match=message):
        PostgresEventRuntime("postgresql://unused", **kwargs)


def runtime_for(claim: ClaimedEvent | None, *, completion: bool = True, max_attempts: int = 3):
    runtime = object.__new__(PostgresEventRuntime)
    runtime.max_attempts = max_attempts
    runtime.claim_outbox = Mock(return_value=claim)
    runtime.complete_outbox = Mock(return_value=completion)
    runtime.fail_outbox = Mock(return_value=True)
    return runtime


def test_run_once_returns_none_when_queue_is_empty():
    runtime = runtime_for(None)
    handler = Mock()

    assert runtime.run_outbox_once("worker-a", handler) is None

    handler.assert_not_called()
    runtime.complete_outbox.assert_not_called()
    runtime.fail_outbox.assert_not_called()


def test_run_once_completes_only_with_owned_lease():
    event = claimed()
    runtime = runtime_for(event)
    handler = Mock()

    assert runtime.run_outbox_once("worker-a", handler) == "DONE"

    handler.assert_called_once_with(event)
    runtime.complete_outbox.assert_called_once_with(event.id, event.locked_by)
    runtime.fail_outbox.assert_not_called()


def test_run_once_retries_handler_failure_before_attempt_limit():
    event = claimed(attempts=1)
    runtime = runtime_for(event, max_attempts=3)
    handler = Mock(side_effect=RuntimeError("transient"))

    assert runtime.run_outbox_once("worker-a", handler) == "RETRY"

    runtime.fail_outbox.assert_called_once_with(event.id, event.locked_by, retry=True)
    runtime.complete_outbox.assert_not_called()


def test_run_once_reports_failed_at_attempt_limit():
    event = claimed(attempts=3)
    runtime = runtime_for(event, max_attempts=3)
    handler = Mock(side_effect=RuntimeError("terminal"))

    assert runtime.run_outbox_once("worker-a", handler) == "FAILED"

    runtime.fail_outbox.assert_called_once_with(event.id, event.locked_by, retry=True)


def test_run_once_fails_closed_when_completion_loses_lease():
    event = claimed()
    runtime = runtime_for(event, completion=False)

    with pytest.raises(RuntimeError, match="OUTBOX_COMPLETION_LOST_LEASE"):
        runtime.run_outbox_once("worker-a", lambda _: None)
