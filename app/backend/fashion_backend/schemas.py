from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LocationContext(BaseModel):
    continent: str | None = None
    country: str | None = None
    city: str | None = None


class TimeContext(BaseModel):
    year: int | None = None
    month: int | None = Field(default=None, ge=1, le=12)
    season: str | None = None


class StructuredGarmentMetadata(BaseModel):
    """AI-extracted attributes stored and used for filtering."""

    garment_type: str | None = None
    style: str | None = None
    material: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    pattern: str | None = None
    season: str | None = None
    occasion: str | None = None
    consumer_profile: str | None = None
    trend_notes: str | None = None
    location_context: LocationContext | None = None
    time_context: TimeContext | None = None


class ClassificationResult(BaseModel):
    description: str
    structured: StructuredGarmentMetadata


class ImageCreateResponse(BaseModel):
    id: int
    description: str
    structured: StructuredGarmentMetadata
    designer_tags: list[str]
    designer_notes: str | None
    designer_name: str | None
    file_url: str
    created_at: datetime


class ImagePatch(BaseModel):
    designer_tags: list[str] | None = None
    designer_notes: str | None = None
    designer_name: str | None = None


class FilterOptions(BaseModel):
    """Distinct values per facet, derived from stored rows."""

    garment_type: list[str]
    style: list[str]
    material: list[str]
    color_palette: list[str]
    pattern: list[str]
    season: list[str]
    occasion: list[str]
    consumer_profile: list[str]
    trend_notes: list[str]
    continent: list[str]
    country: list[str]
    city: list[str]
    year: list[int]
    month: list[int]
    time_season: list[str]
    designer_name: list[str]
    designer_tags: list[str]


def structured_to_dict(s: StructuredGarmentMetadata) -> dict[str, Any]:
    return s.model_dump(mode="json", exclude_none=False)


def structured_from_dict(d: dict[str, Any] | None) -> StructuredGarmentMetadata:
    if not d:
        return StructuredGarmentMetadata()
    return StructuredGarmentMetadata.model_validate(d)
