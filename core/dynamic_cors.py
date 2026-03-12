from collections.abc import Callable

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

from core.db import AsyncSessionLocal
from services.project_service import ProjectService
from utils.origin import normalize_allowed_origin, normalize_request_origin


def _append_vary(existing: str | None, value: str) -> str:
    if not existing:
        return value

    parts = [item.strip() for item in existing.split(",") if item.strip()]
    if value not in parts:
        parts.append(value)
    return ", ".join(parts)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        static_origins: list[str],
        allow_credentials: bool = True,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        max_age: int = 600,
    ) -> None:
        super().__init__(app)
        self.static_origins = {
            origin
            for item in static_origins
            if (origin := normalize_allowed_origin(item)) is not None
        }
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["Authorization", "Content-Type"]
        self.max_age = max_age

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], StarletteResponse],
    ) -> StarletteResponse:
        origin_header = request.headers.get("origin")
        origin = normalize_request_origin(origin_header)
        is_preflight = (
            request.method == "OPTIONS" and request.headers.get("access-control-request-method") is not None
        )

        if origin is None:
            if is_preflight and origin_header:
                return Response(status_code=400)
            return await call_next(request)

        if not await self._is_allowed_origin(origin):
            if is_preflight:
                return Response(status_code=403)
            return await call_next(request)

        if is_preflight:
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        self._apply_cors_headers(response, request, origin)
        return response

    async def _is_allowed_origin(self, origin: str) -> bool:
        if origin in self.static_origins:
            return True

        async with AsyncSessionLocal() as session:
            return await ProjectService.is_origin_allowed(session, origin)

    def _apply_cors_headers(self, response: StarletteResponse, request: Request, origin: str) -> None:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        requested_headers = request.headers.get("access-control-request-headers")
        response.headers["Access-Control-Allow-Headers"] = requested_headers or ", ".join(self.allow_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        response.headers["Vary"] = _append_vary(response.headers.get("Vary"), "Origin")
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"