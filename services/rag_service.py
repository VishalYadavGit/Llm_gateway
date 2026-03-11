from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from models.document import Document
from models.embedding_metadata import EmbeddingMetadata
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from utils.chunking import chunk_text
from utils.pdf import extract_text_from_pdf


class RAGService:
    def __init__(self, qdrant_service: QdrantService | None = None) -> None:
        self.qdrant = qdrant_service or QdrantService()

    async def process_document(self, db: AsyncSession, document: Document) -> None:
        await self.qdrant.ensure_collection()
        extension = Path(document.file_name).suffix.lower()
        if extension == ".pdf":
            text = extract_text_from_pdf(document.file_path)
        elif extension == ".txt":
            text = Path(document.file_path).read_text(encoding="utf-8", errors="ignore").strip()
        else:
            raise ValueError("Unsupported document format for indexing")

        if not text:
            raise ValueError("No extractable text content found in document")
        chunks = list(chunk_text(text))

        document.status = "processing"
        document.content_preview = text[:500]
        await db.flush()

        for index, chunk in enumerate(chunks):
            vector = await EmbeddingService.embed(chunk)
            vector_id = await self.qdrant.upsert_chunk(
                project_id=document.project_id,
                document_id=document.id,
                chunk_index=index,
                text=chunk,
                vector=vector,
            )
            db.add(
                EmbeddingMetadata(
                    project_id=document.project_id,
                    document_id=document.id,
                    vector_id=vector_id,
                    chunk_index=index,
                    chunk_text=chunk,
                )
            )

        document.status = "indexed"
        await db.commit()

    async def retrieve_context(self, project_id: int, query: str, top_k: int) -> list[str]:
        await self.qdrant.ensure_collection()
        query_vector = await EmbeddingService.embed(query)
        hits = await self.qdrant.search(project_id=project_id, query_vector=query_vector, limit=top_k)
        return [item.get("text", "") for item in hits if item.get("text")]
