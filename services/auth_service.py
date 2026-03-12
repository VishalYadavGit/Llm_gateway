from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from models.project import Project
from schemas.auth import TokenResponse
from utils.origin import normalize_request_origin


class AuthService:
    @staticmethod
    async def get_token_from_origin(request: Request, db: AsyncSession) -> TokenResponse:
        """
        Read the Origin header from the incoming request, check it against the
        database, and return a short-term access token if the origin is registered.
        """
        raw_origin = request.headers.get("origin")

        normalized_origin = normalize_request_origin(raw_origin)

        if not normalized_origin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid Origin header"
            )

        result = await db.execute(
            select(Project).where(Project.allowed_origin == normalized_origin)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Origin not registered"
            )

        expires_delta = timedelta(minutes=15)
        token = create_access_token(f"project_{project.id}", expires_delta=expires_delta)

        return TokenResponse(
            access_token=token,
            expires_in=int(expires_delta.total_seconds())
        )
