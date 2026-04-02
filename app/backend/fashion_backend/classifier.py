"""
Multimodal classification: OpenAI vision when API key is set, else deterministic mock for local dev.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from fashion_backend.config import settings
from fashion_backend.parser import parse_model_output
from fashion_backend.schemas import ClassificationResult, StructuredGarmentMetadata

SYSTEM_PROMPT = """You are a fashion design assistant. Analyze the garment or outfit image and respond with ONLY valid JSON (no markdown) matching this shape:
{
  "description": "rich natural language description of the look, setting if visible, and design details",
  "structured": {
    "garment_type": "single primary garment or outfit type",
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
Infer location/time from visible cues if any; otherwise use null. Be specific and concise."""

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


async def classify_image_bytes(image_bytes: bytes, mime: str = "image/jpeg") -> ClassificationResult:
    if not settings.openai_api_key:
        return _mock_from_bytes(image_bytes)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Classify this fashion image and return JSON only."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        max_tokens=1200,
    )
    text = (resp.choices[0].message.content or "").strip()
    try:
        return parse_model_output(text)
    except (json.JSONDecodeError, ValueError):
        fallback = StructuredGarmentMetadata()
        return ClassificationResult(description=text or "Unable to parse structured output.", structured=fallback)
