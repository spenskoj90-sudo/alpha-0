from datetime import UTC, datetime, timedelta

from app.core.entitlements import Entitlement, EntitlementStatus
from app.core.game_catalog import DIABLO_CATALOG, get_game


def test_all_required_diablo_games_are_authoritative():
    ids = {game.id for game in DIABLO_CATALOG}
    assert ids == {
        "diablo-1-pc",
        "diablo-2-pc",
        "diablo-2-resurrected-pc",
        "diablo-3-pc",
        "diablo-4-pc",
        "diablo-immortal-android",
    }


def test_unknown_game_is_not_resolvable():
    assert get_game("diablo-5-pc") is None


def test_entitlement_is_time_and_status_bound():
    now = datetime.now(UTC)
    active = Entitlement("1", "u", "diablo-4-pc", "order", EntitlementStatus.ACTIVE, now - timedelta(minutes=1), now + timedelta(minutes=1))
    expired = Entitlement("2", "u", "diablo-4-pc", "order", EntitlementStatus.EXPIRED, now - timedelta(days=2), now - timedelta(days=1))
    assert active.is_active(now)
    assert not expired.is_active(now)
