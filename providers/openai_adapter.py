from collections.abc import AsyncGenerator
import json

import httpx

from providers.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    base_url = "https://api.openai.com/v1"

    @staticmethod
    def _build_error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
        except json.JSONDecodeError:
            return response.text or "OpenAI returned a non-JSON error response"

        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message")
            if code and message:
                return f"{message} (code: {code})"
            if message:
                return str(message)
        return response.text or "OpenAI request failed"

    async def generate_response(self, prompt: str, api_key: str, model: str) -> str:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._build_error_message(exc.response)
                raise RuntimeError(f"OpenAI API error ({exc.response.status_code}): {detail}") from exc
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream_response(self, prompt: str, api_key: str, model: str) -> AsyncGenerator[str, None]:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detail = self._build_error_message(exc.response)
                    raise RuntimeError(f"OpenAI API error ({exc.response.status_code}): {detail}") from exc
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line.removeprefix("data:").strip()
                    if chunk == "[DONE]":
                        break
                    yield chunk
