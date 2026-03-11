import re

DANGEROUS_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+all\s+prior",
    r"system\s*:",
    r"assistant\s*:",
    r"user\s*:",
    r"```",
]


def sanitize_context(text: str, max_chars: int = 4000) -> str:
    cleaned = text
    for pattern in DANGEROUS_PATTERNS:
        cleaned = re.sub(pattern, "[redacted]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars]
