from collections.abc import AsyncGenerator

import httpx

from providers.base import LLMAdapter


class GeminiAdapter(LLMAdapter):
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_response(self, prompt: str, api_key: str, model: str) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        url = f"{self.base_url}/{model}:generateContent?key={api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def stream_response(self, prompt: str, api_key: str, model: str) -> AsyncGenerator[str, None]:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        url = f"{self.base_url}/{model}:streamGenerateContent?key={api_key}"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            for item in response.json():
                text = item.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text:
                    yield text
