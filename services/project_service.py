from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import decrypt_api_key, encrypt_api_key
from models.api_key import APIKey
from models.project import Project
from models.user import User
from schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from utils.origin import normalize_allowed_origin


class ProjectService:
    @staticmethod
    async def create_project(db: AsyncSession, user: User, payload: ProjectCreateRequest) -> Project:
        allowed_origin = payload.allowed_origin or normalize_allowed_origin(payload.name)

        project = Project(
            user_id=user.id,
            name=payload.name,
            allowed_origin=allowed_origin,
            provider=payload.provider,
            system_prompt=payload.system_prompt,
            model_name=payload.model_name,
        )
        db.add(project)
        await db.flush()

        encrypted_key = encrypt_api_key(payload.api_key.strip())
        project_key = APIKey(project_id=project.id, encrypted_key=encrypted_key)
        db.add(project_key)

        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def list_projects(db: AsyncSession, user: User) -> list[Project]:
        result = await db.execute(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_project_or_404(db: AsyncSession, user: User, project_id: int) -> Project:
        result = await db.execute(
            select(Project).where(and_(Project.id == project_id, Project.user_id == user.id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    @staticmethod
    async def get_project_api_key(db: AsyncSession, project_id: int) -> str:
        result = await db.execute(select(APIKey).where(APIKey.project_id == project_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project API key missing")
        return decrypt_api_key(item.encrypted_key).strip()

    @staticmethod
    async def is_origin_allowed(db: AsyncSession, origin: str) -> bool:
        result = await db.execute(select(Project.id).where(Project.allowed_origin == origin).limit(1))
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def update_project(
        db: AsyncSession,
        user: User,
        project_id: int,
        payload: ProjectUpdateRequest,
    ) -> Project:
        project = await ProjectService.get_project_or_404(db=db, user=user, project_id=project_id)

        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return project

        if "name" in updates and payload.name is not None:
            project.name = payload.name
        if "allowed_origin" in updates:
            project.allowed_origin = payload.allowed_origin
        if "provider" in updates and payload.provider is not None:
            project.provider = payload.provider
        if "system_prompt" in updates and payload.system_prompt is not None:
            project.system_prompt = payload.system_prompt
        if "model_name" in updates:
            project.model_name = payload.model_name

        if "api_key" in updates and payload.api_key is not None:
            result = await db.execute(select(APIKey).where(APIKey.project_id == project.id))
            project_key = result.scalar_one_or_none()
            encrypted_key = encrypt_api_key(payload.api_key.strip())

            if project_key:
                project_key.encrypted_key = encrypted_key
            else:
                db.add(APIKey(project_id=project.id, encrypted_key=encrypted_key))

        await db.commit()
        await db.refresh(project)
        return project
