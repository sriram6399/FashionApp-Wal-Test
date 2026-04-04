"""
Multimodal classification: OpenRouter (OpenAI-compatible) or direct OpenAI when a key is set;
otherwise deterministic mock for local dev.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import io
from typing import Any

from fashion_backend.config import settings
from fashion_backend.parser import parse_model_output
from fashion_backend.schemas import ClassificationResult, StructuredGarmentMetadata

try:
    from PIL import Image
except ImportError:
    Image = None

SYSTEM_PROMPT = """You are a fashion design assistant. Analyze the garment or outfit image and respond with ONLY valid JSON (no markdown) matching this shape:
{
  "description": "rich natural language description of the look, setting if visible, and design details",
  "structured": {
    "garment_type": "HIGH LEVEL DEPARTMENT ONLY. Strictly use one of: 'Womenswear', 'Menswear', 'Unisex', 'Childrenswear', 'Costumes', 'Accessories'",
    "category": "The specific item category (e.g., 'Dress', 'Outerwear', 'Tops', 'Bottoms', 'Footwear', 'Bag')",
    "style": "e.g. streetwear, tailored, bohemian",
    "material": "dominant fabric or material",
    "color_palette": ["2-5 color names"],
    "pattern": "solid, stripe, floral, etc.",
    "season": "spring/summer/fall/winter or transitional",
    "occasion": "casual, formal, athletic, etc.",
    "consumer_profile": "who might wear this",
    "trend_notes": "short trend or market note",
    "location_context": { "continent": null or string, "country": null or string, "city": null or string },
    "time_context": { "year": null or integer, "month": null or 1-12, "season": null or string }
  }
}

Example JSON Response:
{
  "description": "A tailored charcoal wool overcoat worn over a cream turtleneck in a modern city setting.",
  "structured": {
    "garment_type": "Menswear",
    "category": "Outerwear",
    "style": "tailored",
    "material": "wool",
    "color_palette": ["charcoal", "cream"],
    "pattern": "solid",
    "season": "winter",
    "occasion": "smart casual",
    "consumer_profile": "professional",
    "trend_notes": "quiet luxury and sharp tailoring",
    "location_context": { "continent": null, "country": null, "city": null },
    "time_context": { "year": null, "month": null, "season": "winter" }
  }
}

Infer location/time from visible cues if any; otherwise use null. Be specific and concise.
When the user supplies a caption, tags, or structured metadata, treat them as ground truth for context and weave them in. Use valid JSON!"""

def _resize_image_for_llm(image_bytes: bytes, max_size: int = 2048) -> tuple[bytes, str]:
    if Image is None:
        return image_bytes, "image/jpeg"
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, "image/jpeg"

async def _maybe_close_llm_client(client: Any) -> None:
    """AsyncOpenAI.close is async; unit tests may use MagicMock without an awaitable close."""
    close_fn = getattr(client, "close", None)
    if not callable(close_fn):
        return
    out = close_fn()
    if asyncio.iscoroutine(out):
        await out


MOCK_POOL: list[dict[str, Any]] = [
    {
        "description": "Relaxed denim jacket layered over a cream knit, urban street setting.",
        "structured": {
            "garment_type": "jacket",
            "style": "streetwear",
            "material": "denim",
            "color_palette": ["indigo", "cream"],
            "pattern": "solid",
            "season": "fall",
            "occasion": "casual",
            "consumer_profile": "young adult",
            "trend_notes": "layered outerwear",
            "location_context": {"continent": "North America", "country": "USA", "city": "New York"},
            "time_context": {"year": 2024, "month": 10, "season": "fall"},
        },
    },
    {
        "description": "Flowing midi dress with botanical print, open-air market background.",
        "structured": {
            "garment_type": "dress",
            "style": "bohemian",
            "material": "cotton",
            "color_palette": ["sage", "ivory"],
            "pattern": "floral",
            "season": "summer",
            "occasion": "casual",
            "consumer_profile": "women 25-40",
            "trend_notes": "artisan market aesthetic",
            "location_context": {"continent": "Europe", "country": "Portugal", "city": "Lisbon"},
            "time_context": {"year": 2023, "month": 6, "season": "summer"},
        },
    },
    {
        "description": "Tailored wool coat, minimal silhouette, city sidewalk.",
        "structured": {
            "garment_type": "coat",
            "style": "tailored",
            "material": "wool",
            "color_palette": ["charcoal", "black"],
            "pattern": "solid",
            "season": "winter",
            "occasion": "smart casual",
            "consumer_profile": "professional",
            "trend_notes": "quiet luxury",
            "location_context": {"continent": "Asia", "country": "Japan", "city": "Tokyo"},
            "time_context": {"year": 2024, "month": 1, "season": "winter"},
        },
    },
]


def _mock_from_bytes(image_bytes: bytes) -> ClassificationResult:
    h = int(hashlib.sha256(image_bytes).hexdigest()[:8], 16)
    raw = MOCK_POOL[h % len(MOCK_POOL)]
    return parse_model_output(raw)


def _user_context_block(
    caption: str | None,
    upload_metadata: dict[str, Any] | None,
    tags: list[str] | None,
) -> str:
    cap = (caption or "").strip() or "(none)"
    meta = json.dumps(upload_metadata, ensure_ascii=False) if upload_metadata else "{}"
    tag_line = ", ".join(tags) if tags else "(none)"
    return (
        "User-provided context from capture (use with the image; explicit facts here override guesses):\n"
        f"Caption: {cap}\n"
        f"Tags: {tag_line}\n"
        f"Metadata (JSON): {meta}\n\n"
        "Classify this fashion image and return JSON only."
    )


async def classify_image_bytes(
    image_bytes: bytes,
    mime: str = "image/jpeg",
    caption: str | None = None,
    upload_metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    *,
    llm_client: Any | None = None,
) -> ClassificationResult:
    if not settings.llm_api_key:
        return _mock_from_bytes(image_bytes)

    from fashion_backend.llm_client import build_async_openai_client

    own_client = llm_client is None
    if llm_client is None:
        llm_client = build_async_openai_client()
    try:
        resized_bytes, resized_mime = _resize_image_for_llm(image_bytes)
        b64 = base64.standard_b64encode(resized_bytes).decode("ascii")
        data_url = f"data:{resized_mime};base64,{b64}"

        user_text = _user_context_block(caption, upload_metadata, tags)

        resp = await llm_client.chat.completions.create(
            model=settings.vision_model_resolved,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
        )
        text = (resp.choices[0].message.content or "").strip()
        try:
            return parse_model_output(text)
        except (json.JSONDecodeError, ValueError):
            fallback = StructuredGarmentMetadata()
            return ClassificationResult(description=text or "Unable to parse structured output.", structured=fallback)
    except Exception as e:
        # Wrap the API error cleanly for visibility instead of failing with 500 silently
        print(f"LLM backend error: {e}")
        fallback = StructuredGarmentMetadata()
        return ClassificationResult(description=f"AI Classification Error: {str(e)}", structured=fallback)
    finally:
        if own_client:
            await _maybe_close_llm_client(llm_client)
