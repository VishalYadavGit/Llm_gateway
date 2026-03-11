from collections.abc import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.request_log import RequestLog
from models.user import User
from providers.factory import get_adapter
from services.project_service import ProjectService
from services.rag_service import RAGService
from utils.context_sanitizer import sanitize_context

settings = get_settings()


class QueryService:
    def __init__(self, rag_service: RAGService | None = None) -> None:
        self.rag_service = rag_service or RAGService()

    async def build_prompt(self, system_prompt: str, query: str, context_chunks: list[str]) -> str:
        safe_chunks = [sanitize_context(chunk) for chunk in context_chunks]
        context = "\n\n".join(f"- {chunk}" for chunk in safe_chunks)
        return (
            f"System Instructions:\n{system_prompt}\n\n"
            f"Retrieved Context:\n{context}\n\n"
            f"User Query:\n{query}\n\n"
            "Answer grounded in the context. If unsure, say you do not know."
        )

    def resolve_model_name(self, provider: str, model_name: str | None) -> str:
        provider_name = provider.lower()
        if model_name:
            selected = model_name
        else:
            match provider_name:
                case "openai":
                    selected = settings.default_openai_model
                case "gemini":
                    selected = settings.default_gemini_model
                case "claude":
                    selected = settings.default_claude_model
                case _:
                    selected = "default"

        if provider_name == "openai" and selected.lower().startswith("text-embedding-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Configured model is an embeddings model and cannot be used for /v1/query. "
                    "Use a chat model such as 'gpt-4o-mini' or 'gpt-4.1-mini'."
                ),
            )

        return selected

    async def query(
        self,
        db: AsyncSession,
        user: User,
        project_id: int,
        user_query: str,
        top_k: int,
    ) -> tuple[str, list[str]]:
        project = await ProjectService.get_project_or_404(db=db, user=user, project_id=project_id)
        api_key = await ProjectService.get_project_api_key(db=db, project_id=project.id)
        adapter = get_adapter(project.provider)
        model_name = self.resolve_model_name(project.provider, project.model_name)
        context_chunks: list[str] = []

        try:
            context_chunks = await self.rag_service.retrieve_context(project.id, user_query, top_k)
            prompt = await self.build_prompt(project.system_prompt, user_query, context_chunks)
            answer = await adapter.generate_response(prompt=prompt, api_key=api_key, model=model_name)
            db.add(
                RequestLog(
                    user_id=user.id,
                    project_id=project.id,
                    provider=project.provider,
                    model_name=model_name,
                    status="success",
                )
            )
            await db.commit()
            return answer, context_chunks
        except HTTPException:
            raise
        except Exception as exc:
            db.add(
                RequestLog(
                    user_id=user.id,
                    project_id=project.id,
                    provider=project.provider,
                    model_name=model_name,
                    status="error",
                    error_message=str(exc),
                )
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    async def stream_query(
        self,
        db: AsyncSession,
        user: User,
        project_id: int,
        user_query: str,
        top_k: int,
    ) -> tuple[AsyncGenerator[str, None], list[str]]:
        project = await ProjectService.get_project_or_404(db=db, user=user, project_id=project_id)
        api_key = await ProjectService.get_project_api_key(db=db, project_id=project.id)
        adapter = get_adapter(project.provider)
        model_name = self.resolve_model_name(project.provider, project.model_name)

        try:
            context_chunks = await self.rag_service.retrieve_context(project.id, user_query, top_k)
            prompt = await self.build_prompt(project.system_prompt, user_query, context_chunks)
            return adapter.stream_response(prompt=prompt, api_key=api_key, model=model_name), context_chunks
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
