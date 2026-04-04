"""Text embeddings for semantic search (same OpenAI-compatible endpoint as chat)."""

from __future__ import annotations

_MAX_CHARS = 12000


async def embed_text(text: str) -> list[float]:
    """Single text → embedding vector. Raises if no API key or API error."""
    from fashion_backend.config import settings
    from fashion_backend.llm_client import build_async_openai_client

    if not settings.llm_api_key:
        raise RuntimeError("embeddings require LLM_API_KEY / OPENROUTER_API_KEY")

    t = (text or "").strip()
    if not t:
        t = " "

    client = build_async_openai_client()
    resp = await client.embeddings.create(
        model=settings.embedding_model_resolved,
        input=t[:_MAX_CHARS],
    )
    return list(resp.data[0].embedding)
