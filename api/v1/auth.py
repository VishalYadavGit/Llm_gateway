from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from schemas.auth import TokenResponse
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/token", response_model=TokenResponse)
async def get_token(request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Returns a short-term access token (15 minutes) if the request Origin header
    matches a registered project origin in the database.
    No request body needed — the Origin header is read automatically.
    """
    return await AuthService.get_token_from_origin(request, db)
