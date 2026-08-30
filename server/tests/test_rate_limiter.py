from app.main import RateLimiter


def test_rate_limiter_evicts_expired_buckets_before_enforcing_capacity():
    limiter = RateLimiter(limit=2, window=60, max_buckets=2)

    assert limiter.allow("active") is True
    assert limiter.allow("expired") is True
    limiter._hits["expired"][0] -= 61

    assert limiter.allow("new") is True
    assert "expired" not in limiter._hits
    assert "active" in limiter._hits
    assert "new" in limiter._hits


def test_rate_limiter_does_not_evict_active_bucket_to_make_room():
    limiter = RateLimiter(limit=1, window=60, max_buckets=1)

    assert limiter.allow("active") is True
    assert limiter.allow("new") is False
    assert "active" in limiter._hits
    assert "new" not in limiter._hits


def test_rate_limiter_removes_expired_hits_before_allowing_again():
    limiter = RateLimiter(limit=1, window=60, max_buckets=2)

    assert limiter.allow("client") is True
    limiter._hits["client"][0] -= 61

    assert limiter.allow("client") is True
    assert len(limiter._hits["client"]) == 1
