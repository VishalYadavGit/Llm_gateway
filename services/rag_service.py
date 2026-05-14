import logging
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from models.document import Document
from models.embedding_metadata import EmbeddingMetadata
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from utils.chunking import chunk_text
from utils.pdf import extract_text_from_pdf

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, qdrant_service: QdrantService | None = None) -> None:
        self.qdrant = qdrant_service or QdrantService()

    async def process_document(self, db: AsyncSession, document: Document) -> None:
        logger.info(f"[RAG] Processing document {document.id}: {document.file_name}")
        
        logger.info(f"[RAG] Ensuring Qdrant collection exists...")
        await self.qdrant.ensure_collection()
        
        extension = Path(document.file_name).suffix.lower()
        logger.debug(f"[RAG] File extension: {extension}")
        
        if extension == ".pdf":
            logger.info(f"[RAG] Extracting text from PDF...")
            text = extract_text_from_pdf(document.file_path)
        elif extension == ".txt":
            logger.info(f"[RAG] Reading text file...")
            text = Path(document.file_path).read_text(encoding="utf-8", errors="ignore").strip()
        else:
            raise ValueError("Unsupported document format for indexing")

        if not text:
            logger.error(f"[RAG] No extractable text found in document")
            raise ValueError("No extractable text content found in document")
        
        logger.info(f"[RAG] Extracted {len(text)} characters")
        
        chunks = list(chunk_text(text))
        logger.info(f"[RAG] Document split into {len(chunks)} chunks")

        document.status = "processing"
        document.content_preview = text[:500]
        await db.flush()

        for index, chunk in enumerate(chunks):
            logger.debug(f"[RAG] Processing chunk {index+1}/{len(chunks)} ({len(chunk)} chars)")
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
        logger.info(f"[RAG] Document {document.id} successfully indexed with {len(chunks)} chunks")

    async def retrieve_context(self, project_id: int, query: str, top_k: int) -> list[str]:
        logger.info(f"[RAG] Retrieving context for project {project_id}, query: '{query[:50]}...', top_k={top_k}")
        await self.qdrant.ensure_collection()
        query_vector = await EmbeddingService.embed(query)
        logger.debug(f"[RAG] Generated query vector with {len(query_vector)} dimensions")
        hits = await self.qdrant.search(project_id=project_id, query_vector=query_vector, limit=top_k)
        results = [item.get("text", "") for item in hits if item.get("text")]
        logger.info(f"[RAG] Retrieved {len(results)} context chunks")
        return results
