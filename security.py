from __future__ import annotations

import html
from urllib.parse import urlparse


def validate_company_name(value: str) -> str:
    if value is None:
        raise ValueError("Company name is required.")

    normalized = str(value).strip()
    if not normalized:
        raise ValueError("Company name cannot be blank.")
    if len(normalized) > 200:
        raise ValueError("Company name is too long.")
    return normalized


def sanitize_text(value: str) -> str:
    text = str(value or "")
    text = html.escape(text, quote=False)
    return " ".join(text.split())


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(str(url))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
