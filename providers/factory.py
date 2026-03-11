from providers.base import LLMAdapter
from providers.claude_adapter import ClaudeAdapter
from providers.gemini_adapter import GeminiAdapter
from providers.openai_adapter import OpenAIAdapter


def get_adapter(provider: str) -> LLMAdapter:
    match provider.lower():
        case "openai":
            return OpenAIAdapter()
        case "gemini":
            return GeminiAdapter()
        case "claude":
            return ClaudeAdapter()
        case _:
            raise ValueError(f"Unsupported provider: {provider}")
