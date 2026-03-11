from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMAdapter(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, api_key: str, model: str) -> str:
        raise NotImplementedError

    async def stream_response(self, prompt: str, api_key: str, model: str) -> AsyncGenerator[str, None]:
        result = await self.generate_response(prompt=prompt, api_key=api_key, model=model)
        yield result
