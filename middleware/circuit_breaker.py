import redis
import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: redis.Redis, threshold=5, sleep_window=30):
        super().__init__(app)
        self.redis = redis_client
        self.threshold = threshold
        self.sleep_window = sleep_window

    async def dispatch(self, request: Request, call_next):
        key = "cb_status"
        if self.redis.get(key) == b"OPEN":
            raise HTTPException(status_code=503, detail="Circuit Breaker Open")
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Simple failure tracking for demo
            self.redis.incr("failure_count")
            if int(self.redis.get("failure_count") or 0) >= self.threshold:
                self.redis.set(key, "OPEN", ex=self.sleep_window)
            raise e
