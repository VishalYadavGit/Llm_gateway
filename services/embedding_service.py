import hashlib

from core.config import get_settings

settings = get_settings()


class EmbeddingService:
    @staticmethod
    async def embed(text: str) -> list[float]:
        # Deterministic lightweight embedding fallback for self-hosted deployments.
        # Replace with provider-native embeddings for higher semantic quality.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        base = [byte / 255.0 for byte in digest]

        vector: list[float] = []
        while len(vector) < settings.embedding_dimension:
            vector.extend(base)

        return vector[: settings.embedding_dimension]
