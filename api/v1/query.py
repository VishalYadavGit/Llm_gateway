from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.dependencies import get_current_project
from models.project import Project
from schemas.query import QueryRequest, QueryResponse
from services.query_service import QueryService

router = APIRouter(tags=["query"])
query_service = QueryService()


@router.post("/query", response_model=QueryResponse)
@router.post("/query/", response_model=QueryResponse, include_in_schema=False)
async def query(
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db),
    project: Project = Depends(get_current_project),
):
    if payload.stream:
        stream, context_chunks = await query_service.stream_query(
            db=db,
            project=project,
            user_query=payload.query,
            top_k=payload.top_k,
        )

        async def sse_wrapper() -> AsyncGenerator[str, None]:
            yield f"event: context\\ndata: {context_chunks}\\n\\n"
            async for chunk in stream:
                yield f"data: {chunk}\\n\\n"

        return StreamingResponse(sse_wrapper(), media_type="text/event-stream")

    answer, chunks = await query_service.query(
        db=db,
        project=project,
        user_query=payload.query,
        top_k=payload.top_k,
    )
    return QueryResponse(answer=answer, context_chunks=chunks)
