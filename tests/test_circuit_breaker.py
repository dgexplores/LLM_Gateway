import asyncio

import pytest
import redis
from fastapi import HTTPException

from middleware.circuit_breaker import CircuitBreakerMiddleware


class FakeRedis:
    def __init__(self, available: bool = True):
        self.store: dict[str, bytes | int] = {}
        self.available = available

    def ping(self):
        if not self.available:
            raise redis.RedisError("redis down")

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value if isinstance(value, bytes) else str(value).encode()
        return True

    def incr(self, key):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    def expire(self, key, seconds):
        return key in self.store


async def ok_next(request):
    return "ok"


async def failing_next(request):
    raise RuntimeError("boom")


def run_dispatch(middleware, next_fn):
    return asyncio.run(middleware.dispatch(request=None, call_next=next_fn))


def make_middleware(fake_redis, threshold=3, sleep_window=30):
    return CircuitBreakerMiddleware(app=object(), redis_client=fake_redis,
                                    threshold=threshold, sleep_window=sleep_window)


def test_opens_at_threshold_and_blocks():
    fake = FakeRedis()
    mw = make_middleware(fake, threshold=3)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            run_dispatch(mw, failing_next)

    assert fake.get("cb_status") == b"OPEN"
    with pytest.raises(HTTPException) as exc_info:
        run_dispatch(mw, ok_next)
    assert exc_info.value.status_code == 503


def test_success_resets_failure_count():
    fake = FakeRedis()
    mw = make_middleware(fake, threshold=3)

    with pytest.raises(RuntimeError):
        run_dispatch(mw, failing_next)
    assert int(fake.get("failure_count")) == 1

    assert run_dispatch(mw, ok_next) == "ok"
    assert fake.get("failure_count") == b"0"


def test_fail_open_when_redis_down():
    fake = FakeRedis(available=False)
    mw = make_middleware(fake, threshold=1)

    assert run_dispatch(mw, ok_next) == "ok"

    with pytest.raises(RuntimeError):
        run_dispatch(mw, failing_next)
    assert "cb_status" not in fake.store