from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    project_id: int
    query: str = Field(min_length=1, max_length=12000)
    stream: bool = False
    top_k: int = Field(default=6, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    context_chunks: list[str]
