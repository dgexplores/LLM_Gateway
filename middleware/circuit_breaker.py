import redis
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: redis.Redis, threshold=5, sleep_window=30):
        super().__init__(app)
        self.redis = redis_client
        self.threshold = threshold
        self.sleep_window = sleep_window
        self.failure_key = "failure_count"
        self.status_key = "cb_status"

    def _redis_available(self) -> bool:
        try:
            self.redis.ping()
            return True
        except redis.RedisError:
            return False

    async def dispatch(self, request: Request, call_next):
        # Fail open when Redis is unreachable: availability over breaker protection.
        if self._redis_available() and self.redis.get(self.status_key) == b"OPEN":
            raise HTTPException(status_code=503, detail="Circuit Breaker Open")

        try:
            response = await call_next(request)
        except Exception as e:
            if self._redis_available():
                failures = self.redis.incr(self.failure_key)
                self.redis.expire(self.failure_key, self.sleep_window)
                if failures >= self.threshold:
                    self.redis.set(self.status_key, "OPEN", ex=self.sleep_window)
            raise e

        if self._redis_available():
            self.redis.set(self.failure_key, 0, ex=self.sleep_window)
        return response
