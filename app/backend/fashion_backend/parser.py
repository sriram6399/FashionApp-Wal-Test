"""
Parse raw model output (JSON string or dict) into StructuredGarmentMetadata + description.
Used by the classifier and unit tests.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fashion_backend.schemas import ClassificationResult, StructuredGarmentMetadata


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,;/|]", value)
        return [p.strip() for p in parts if p.strip()]
    return [str(value).strip()] if str(value).strip() else []


def normalize_raw_payload(raw: str | dict[str, Any]) -> dict[str, Any]:
    """Accept JSON string or dict; strip markdown code fences if present."""
    if isinstance(raw, dict):
        return raw
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return json.loads(text)


def parse_model_output(raw: str | dict[str, Any]) -> ClassificationResult:
    """
    Parse multimodal model JSON into ClassificationResult.

    Supports:
    - Top-level keys: description, structured (nested object)
    - Flat keys matching StructuredGarmentMetadata fields
    - location_context / time_context as nested objects or flat location_*
    """
    data = normalize_raw_payload(raw)

    description = (
        data.get("description")
        or data.get("summary")
        or data.get("caption")
        or ""
    )
    if not isinstance(description, str):
        description = str(description)

    structured_src = data.get("structured")
    if structured_src is None and isinstance(data.get("garment_type"), (str, type(None))):
        structured_src = {k: v for k, v in data.items() if k not in ("description", "summary", "caption")}
    if not isinstance(structured_src, dict):
        structured_src = {}

    loc = structured_src.get("location_context")
    if not isinstance(loc, dict):
        loc = {
            "continent": structured_src.get("continent") or data.get("continent"),
            "country": structured_src.get("country") or data.get("country"),
            "city": structured_src.get("city") or data.get("city"),
        }
    time_ctx = structured_src.get("time_context")
    if not isinstance(time_ctx, dict):
        time_ctx = {
            "year": structured_src.get("year") or data.get("year"),
            "month": structured_src.get("month") or data.get("month"),
            "season": structured_src.get("time_season") or structured_src.get("capture_season") or data.get("time_season"),
        }

    colors = structured_src.get("color_palette")
    if colors is None:
        colors = structured_src.get("colors")

    structured = StructuredGarmentMetadata(
        garment_type=_scalar(structured_src.get("garment_type")),
        style=_scalar(structured_src.get("style")),
        material=_scalar(structured_src.get("material")),
        color_palette=_coerce_list(colors),
        pattern=_scalar(structured_src.get("pattern")),
        season=_scalar(structured_src.get("season")),
        occasion=_scalar(structured_src.get("occasion")),
        consumer_profile=_scalar(structured_src.get("consumer_profile")),
        trend_notes=_scalar(structured_src.get("trend_notes")),
        location_context=_location_from(loc),
        time_context=_time_from(time_ctx),
    )

    return ClassificationResult(description=description.strip(), structured=structured)


def _scalar(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _location_from(loc: dict[str, Any] | None):
    from fashion_backend.schemas import LocationContext

    if not loc:
        return None
    return LocationContext(
        continent=_scalar(loc.get("continent")),
        country=_scalar(loc.get("country")),
        city=_scalar(loc.get("city")),
    )


def _time_from(t: dict[str, Any] | None):
    from fashion_backend.schemas import TimeContext

    if not t:
        return None
    year = t.get("year")
    month = t.get("month")
    try:
        yi = int(year) if year is not None else None
    except (TypeError, ValueError):
        yi = None
    try:
        mi = int(month) if month is not None else None
    except (TypeError, ValueError):
        mi = None
    return TimeContext(
        year=yi,
        month=mi if mi is not None and 1 <= mi <= 12 else None,
        season=_scalar(t.get("season")),
    )
