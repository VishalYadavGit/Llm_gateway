import uuid
import logging

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
VECTOR_NAME = "embeddings"


class QdrantService:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            check_compatibility=False,
        )
        self.collection = settings.qdrant_collection
        

    async def ensure_collection(self) -> None:
        logger.debug(f"[QDRANT] Checking collection '{self.collection}'...")
        collections = await self.client.get_collections()
        logger.debug(f"[QDRANT] Available collections: {[c.name for c in collections.collections]}")
        
        exists = any(c.name == self.collection for c in collections.collections)
        if not exists:
            logger.info(f"[QDRANT] Creating collection '{self.collection}' with vector_size={settings.embedding_dimension}")
            try:
                await self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config={
                        VECTOR_NAME: qdrant_models.VectorParams(
                            size=settings.embedding_dimension,
                            distance=qdrant_models.Distance.COSINE,
                        )
                    },
                )
                logger.info(f"[QDRANT] Collection '{self.collection}' created successfully")
            except Exception as e:
                logger.error(f"[QDRANT] Failed to create collection: {str(e)}")
                raise
        else:
            logger.debug(f"[QDRANT] Collection '{self.collection}' already exists")

        # Some Qdrant deployments require explicit payload indexing for filtered search.
        try:
            logger.debug(f"[QDRANT] Creating payload index for project_id...")
            await self.client.create_payload_index(
                collection_name=self.collection,
                field_name="project_id",
                field_schema=qdrant_models.PayloadSchemaType.INTEGER,
                wait=True,
            )
            logger.debug(f"[QDRANT] Payload index created successfully")
        except Exception as e:
            logger.warning(f"[QDRANT] Could not create payload index: {str(e)}")

    async def upsert_chunk(
        self,
        project_id: int,
        document_id: int,
        chunk_index: int,
        text: str,
        vector: list[float],
    ) -> str:
        vector_id = str(uuid.uuid4())
        payload = {
            "project_id": project_id,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "text": text,
        }
        logger.debug(f"[QDRANT] Upserting chunk - doc_id={document_id}, chunk={chunk_index}, vector_id={vector_id}")
        try:
            await self.client.upsert(
                collection_name=self.collection,
                points=[qdrant_models.PointStruct(id=vector_id, vector={VECTOR_NAME: vector}, payload=payload)],
            )
            logger.debug(f"[QDRANT] Chunk upserted successfully")
        except Exception as e:
            logger.error(f"[QDRANT] Upsert failed: {str(e)}")
            raise
        return vector_id

    async def search(self, project_id: int, query_vector: list[float], limit: int) -> list[dict]:
        logger.debug(f"[QDRANT] Searching collection '{self.collection}' for project_id={project_id}, limit={limit}")
        query_filter = qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id),
                )
            ]
        )

        # qdrant-client API differs by version: older releases expose `search`,
        # newer releases expose `query_points`.
        try:
            if hasattr(self.client, "search"):
                logger.debug(f"[QDRANT] Using search() method")
                hits = await self.client.search(
                    collection_name=self.collection,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                )
                results = [hit.payload for hit in hits if hit.payload]
                logger.debug(f"[QDRANT] Search returned {len(results)} results")
                return results
            else:
                logger.debug(f"[QDRANT] Using query_points() method")
                response = await self.client.query_points(
                    collection_name=self.collection,
                    query=query_vector,
                    limit=limit,
                    query_filter=query_filter,
                )
                points = getattr(response, "points", None) or []
                results = [point.payload for point in points if getattr(point, "payload", None)]
                logger.debug(f"[QDRANT] query_points returned {len(results)} results")
                return results
        except Exception as e:
            logger.error(f"[QDRANT] Search failed: {str(e)}")
            raise
