from app.core.rate_limit import SlidingWindowLimiter


def test_sliding_window_limit_and_expiry():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=10)
    assert limiter.allow("client-a", now=0)
    assert limiter.allow("client-a", now=1)
    assert not limiter.allow("client-a", now=2)
    assert limiter.allow("client-a", now=10.1)


def test_rate_limits_are_isolated_by_client():
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)
    assert limiter.allow("client-a", now=0)
    assert not limiter.allow("client-a", now=1)
    assert limiter.allow("client-b", now=1)
