"""Shared OpenAI-compatible async client (OpenRouter or OpenAI)."""

from __future__ import annotations

import ssl
from typing import Any

import certifi
import httpx

from fashion_backend.config import settings


def build_async_openai_client() -> Any:
    from openai import AsyncOpenAI

    api_key = settings.llm_api_key
    if not api_key:
        raise RuntimeError("No LLM API key configured")

    base_url = settings.llm_base_url_resolved
    default_headers: dict[str, str] = {}
    if settings.uses_openrouter:
        if settings.openrouter_site_url:
            default_headers["HTTP-Referer"] = settings.openrouter_site_url
        # OpenRouter docs: X-OpenRouter-Title (X-Title still accepted for backwards compatibility)
        default_headers["X-OpenRouter-Title"] = settings.openrouter_app_name
        default_headers["X-Title"] = settings.openrouter_app_name

    # Explicit client: http2=False, certifi bundle, optional no keep-alive (see deploy/.env).
    ka = 0 if settings.httpx_no_keepalive else 10
    mc = 8 if settings.httpx_no_keepalive else 20
    _ssl = ssl.create_default_context(cafile=certifi.where())
    http_client = httpx.AsyncClient(
        http2=False,
        verify=_ssl,
        trust_env=settings.httpx_trust_env,
        timeout=httpx.Timeout(180.0, connect=45.0),
        limits=httpx.Limits(max_keepalive_connections=ka, max_connections=mc),
    )

    client_kw: dict[str, Any] = {
        "api_key": api_key,
        "http_client": http_client,
    }
    if base_url:
        client_kw["base_url"] = base_url
    if default_headers:
        client_kw["default_headers"] = default_headers

    return AsyncOpenAI(**client_kw)
