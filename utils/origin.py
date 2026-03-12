from urllib.parse import urlsplit


def _add_default_scheme(origin: str) -> str:
    if "://" in origin:
        return origin
    return f"https://{origin}"


def normalize_allowed_origin(value: str | None) -> str | None:
    if value is None:
        return None

    raw_value = value.strip()
    if not raw_value or raw_value.lower() == "null":
        return None

    try:
        parsed = urlsplit(_add_default_scheme(raw_value))
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return None

    if parsed.username or parsed.password or not parsed.hostname:
        return None

    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None

    host = parsed.hostname.lower()
    port = parsed.port
    if port == 80 and scheme == "http":
        port = None
    if port == 443 and scheme == "https":
        port = None

    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    if port is None:
        return f"{scheme}://{display_host}"
    return f"{scheme}://{display_host}:{port}"


def normalize_request_origin(value: str | None) -> str | None:
    if value is None or "://" not in value:
        return None
    return normalize_allowed_origin(value)