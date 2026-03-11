import asyncio

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select

from core.config import get_settings
from core.db import AsyncSessionLocal
from models.document import Document
from services.rag_service import RAGService

settings = get_settings()
redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)


async def _process_document_async(document_id: int) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            return

        rag_service = RAGService()
        try:
            await rag_service.process_document(db=db, document=document)
        except Exception:
            document.status = "failed"
            await db.commit()
            raise


@dramatiq.actor(max_retries=2)
def process_document(document_id: int) -> None:
    asyncio.run(_process_document_async(document_id))
