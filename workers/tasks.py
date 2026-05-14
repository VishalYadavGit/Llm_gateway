import asyncio
import logging
import traceback

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select

from core.config import get_settings
from core.db import AsyncSessionLocal
from models.document import Document
from services.rag_service import RAGService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

settings = get_settings()
redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)


async def _process_document_async(document_id: int) -> None:
    logger.info(f"[WORKER] Starting document processing for ID: {document_id}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            logger.error(f"[WORKER] Document {document_id} not found in database")
            return

        logger.info(f"[WORKER] Found document: {document.file_name} (project={document.project_id})")
        logger.info(f"[WORKER] File path: {document.file_path}")
        
        rag_service = RAGService()
        try:
            logger.info(f"[WORKER] Starting RAG processing...")
            await rag_service.process_document(db=db, document=document)
            logger.info(f"[WORKER] Document {document_id} processed successfully. Status: {document.status}")
        except Exception as exc:
            logger.error(f"[WORKER] Document {document_id} processing failed: {str(exc)}")
            logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")
            document.status = "failed"
            await db.commit()
            raise


@dramatiq.actor(max_retries=2)
def process_document(document_id: int) -> None:
    asyncio.run(_process_document_async(document_id))
