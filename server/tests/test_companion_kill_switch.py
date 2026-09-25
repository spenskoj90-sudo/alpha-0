import pytest

from app.core.companion_kill_switch import CompanionKillSwitch, CompanionKillSwitchState


def test_kill_switch_state_activation_and_explicit_reset() -> None:
    switch = CompanionKillSwitch()
    assert switch.state() == CompanionKillSwitchState(active=False)
    switch.require_clear()

    switch.activate()
    assert switch.active is True
    assert switch.state() == CompanionKillSwitchState(active=True)
    with pytest.raises(RuntimeError, match="kill switch is active"):
        switch.require_clear()

    switch.reset()
    assert switch.active is False
    switch.require_clear()


def test_kill_switch_can_start_fail_closed() -> None:
    switch = CompanionKillSwitch(active=True)
    with pytest.raises(RuntimeError, match="kill switch is active"):
        switch.require_clear()
