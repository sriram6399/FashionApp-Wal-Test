"""Unit tests: parsing multimodal JSON into structured attributes."""

import pytest

from fashion_backend.parser import normalize_raw_payload, parse_model_output
from fashion_backend.schemas import StructuredGarmentMetadata


def test_parse_nested_structured():
    raw = """
    {
      "description": "Linen sundress at a coastal market.",
      "structured": {
        "garment_type": "dress",
        "style": "resort",
        "material": "linen",
        "color_palette": ["white", "sand"],
        "pattern": "solid",
        "season": "summer",
        "occasion": "vacation",
        "consumer_profile": "women",
        "trend_notes": "artisan market",
        "location_context": {"continent": "Europe", "country": "Greece", "city": "Athens"},
        "time_context": {"year": 2024, "month": 7, "season": "summer"}
      }
    }
    """
    out = parse_model_output(raw)
    assert "linen" in out.description.lower()
    assert out.structured.garment_type == "dress"
    assert out.structured.color_palette == ["white", "sand"]
    assert out.structured.location_context is not None
    assert out.structured.location_context.country == "Greece"
    assert out.structured.time_context is not None
    assert out.structured.time_context.year == 2024


def test_parse_markdown_fenced_json():
    raw = """```json
{"description": "Test", "structured": {"garment_type": "coat", "color_palette": "navy, black"}}
```"""
    out = parse_model_output(raw)
    assert out.structured.garment_type == "coat"
    assert set(out.structured.color_palette) >= {"navy", "black"}


def test_normalize_raw_payload_dict():
    d = {"description": "x", "structured": {"garment_type": "bag"}}
    assert normalize_raw_payload(d) == d


def test_flat_keys_fallback():
    raw = {
        "description": "Flat",
        "garment_type": "boot",
        "country": "Italy",
        "year": 2023,
    }
    out = parse_model_output(raw)
    assert out.structured.garment_type == "boot"
    assert out.structured.location_context is not None
    assert out.structured.location_context.country == "Italy"
    assert out.structured.time_context is not None
    assert out.structured.time_context.year == 2023


def test_invalid_json_raises():
    with pytest.raises(Exception):
        parse_model_output("not json {{{")
