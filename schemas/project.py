from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from utils.origin import normalize_allowed_origin


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    allowed_origin: str | None = Field(default=None, min_length=1, max_length=255)
    provider: str = Field(pattern="^(openai|gemini|claude)$")
    api_key: str = Field(min_length=10, max_length=2048)
    system_prompt: str = Field(default="You are a helpful assistant.", min_length=1, max_length=8000)
    model_name: str | None = Field(default=None, max_length=100)

    @field_validator("allowed_origin")
    @classmethod
    def validate_allowed_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_allowed_origin(value)
        if normalized is None:
            raise ValueError("allowed_origin must be a valid site origin such as https://example.com")
        return normalized


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    allowed_origin: str | None = Field(default=None, min_length=1, max_length=255)
    provider: str | None = Field(default=None, pattern="^(openai|gemini|claude)$")
    api_key: str | None = Field(default=None, min_length=10, max_length=2048)
    system_prompt: str | None = Field(default=None, min_length=1, max_length=8000)
    model_name: str | None = Field(default=None, max_length=100)

    @field_validator("allowed_origin")
    @classmethod
    def validate_allowed_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_allowed_origin(value)
        if normalized is None:
            raise ValueError("allowed_origin must be a valid site origin such as https://example.com")
        return normalized


class ProjectResponse(BaseModel):
    id: int
    name: str
    allowed_origin: str | None
    provider: str
    system_prompt: str
    model_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True
