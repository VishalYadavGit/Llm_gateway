from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await AuthService.register(db, payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await AuthService.login(db, payload)


@router.get("/token", response_model=TokenResponse)
async def get_token(request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Returns a short-term access token (15 minutes) if the request Origin header
    matches a registered project origin in the database.
    No request body needed — the Origin header is read automatically.
    """
    return await AuthService.get_token_from_origin(request, db)
