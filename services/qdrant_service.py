import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models

from core.config import get_settings

settings = get_settings()


class QdrantService:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            check_compatibility=False,
        )
        self.collection = settings.qdrant_collection
        

    async def ensure_collection(self) -> None:
        collections = await self.client.get_collections()
        exists = any(c.name == self.collection for c in collections.collections)
        if not exists:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qdrant_models.VectorParams(
                    size=settings.embedding_dimension,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

        # Some Qdrant deployments require explicit payload indexing for filtered search.
        await self.client.create_payload_index(
            collection_name=self.collection,
            field_name="project_id",
            field_schema=qdrant_models.PayloadSchemaType.INTEGER,
            wait=True,
        )

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
        await self.client.upsert(
            collection_name=self.collection,
            points=[qdrant_models.PointStruct(id=vector_id, vector=vector, payload=payload)],
        )
        return vector_id

    async def search(self, project_id: int, query_vector: list[float], limit: int) -> list[dict]:
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
        if hasattr(self.client, "search"):
            hits = await self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
            )
            return [hit.payload for hit in hits if hit.payload]

        response = await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
        )
        points = getattr(response, "points", None) or []
        return [point.payload for point in points if getattr(point, "payload", None)]
