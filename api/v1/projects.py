from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await ProjectService.create_project(db, user, payload)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    projects = await ProjectService.list_projects(db, user)
    return [ProjectResponse.model_validate(project) for project in projects]


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await ProjectService.update_project(db=db, user=user, project_id=project_id, payload=payload)
    return ProjectResponse.model_validate(project)
