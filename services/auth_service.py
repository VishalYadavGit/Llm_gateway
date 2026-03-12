from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, hash_password, verify_password
from models.project import Project
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from utils.origin import normalize_request_origin


ADMIN_TOKEN_EXPIRES_MINUTES = 60 * 8
ORIGIN_TOKEN_EXPIRES_MINUTES = 15


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, payload: RegisterRequest) -> TokenResponse:
        existing = await db.execute(select(User).where(User.email == payload.email.lower()))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        expires_delta = timedelta(minutes=ADMIN_TOKEN_EXPIRES_MINUTES)
        token = create_access_token(str(user.id), expires_delta=expires_delta)
        return TokenResponse(access_token=token, expires_in=int(expires_delta.total_seconds()))

    @staticmethod
    async def login(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == payload.email.lower()))
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        expires_delta = timedelta(minutes=ADMIN_TOKEN_EXPIRES_MINUTES)
        token = create_access_token(str(user.id), expires_delta=expires_delta)
        return TokenResponse(access_token=token, expires_in=int(expires_delta.total_seconds()))

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

        expires_delta = timedelta(minutes=ORIGIN_TOKEN_EXPIRES_MINUTES)
        token = create_access_token(f"project_{project.id}", expires_delta=expires_delta)

        return TokenResponse(
            access_token=token,
            expires_in=int(expires_delta.total_seconds())
        )
