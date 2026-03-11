from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.documents import router as document_router
from api.v1.projects import router as project_router
from api.v1.query import router as query_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(project_router)
api_router.include_router(document_router)
api_router.include_router(query_router)
