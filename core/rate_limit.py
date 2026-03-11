import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.config import get_settings

settings = get_settings()


class InMemoryRateStore:
    def __init__(self) -> None:
        self.store: dict[str, deque[float]] = defaultdict(deque)

    async def increment(self, key: str, window_seconds: int) -> int:
        now = time.time()
        bucket = self.store[key]
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        bucket.append(now)
        return len(bucket)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str):
        super().__init__(app)
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.fallback_store = InMemoryRateStore()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in {"/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        identity = request.headers.get("authorization") or request.client.host or "anonymous"
        key = f"ratelimit:{identity}"

        count = 0
        try:
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, settings.rate_limit_window_seconds, nx=True)
            values = await pipeline.execute()
            count = int(values[0])
        except Exception:
            count = await self.fallback_store.increment(key, settings.rate_limit_window_seconds)

        if count > settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        return await call_next(request)
