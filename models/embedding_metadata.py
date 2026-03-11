from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from models.base_mixins import TimestampMixin


class EmbeddingMetadata(Base, TimestampMixin):
    __tablename__ = "embeddings_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    vector_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    chunk_index: Mapped[int] = mapped_column(index=True)
    chunk_text: Mapped[str] = mapped_column(Text)

    project = relationship("Project", back_populates="embeddings")
    document = relationship("Document", back_populates="embeddings")
