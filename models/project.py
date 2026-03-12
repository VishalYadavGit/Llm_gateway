from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from models.base_mixins import TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    allowed_origin: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful assistant.")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    owner = relationship("User", back_populates="projects")
    api_key = relationship("APIKey", back_populates="project", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    embeddings = relationship("EmbeddingMetadata", back_populates="project", cascade="all, delete-orphan")
