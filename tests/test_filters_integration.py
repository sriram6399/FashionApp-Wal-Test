"""Integration tests: location and time filters over stored metadata."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_backend.db import SessionLocal
from fashion_backend.models import ImageRecord
from fashion_backend.schemas import (
    LocationContext,
    StructuredGarmentMetadata,
    TimeContext,
    structured_to_dict,
)
from fashion_backend.services.images import list_filtered


@pytest.mark.asyncio
async def test_filter_by_country_and_year(client: AsyncClient):
    async with SessionLocal() as session:
        await _seed_row(
            session,
            ai_metadata={
                "garment_type": "dress",
                "style": "bohemian",
                "material": "cotton",
                "color_palette": ["sage"],
                "pattern": "floral",
                "season": "summer",
                "occasion": "casual",
                "consumer_profile": "women",
                "trend_notes": "market",
                "location_context": {"continent": "Europe", "country": "Portugal", "city": "Lisbon"},
                "time_context": {"year": 2023, "month": 6, "season": "summer"},
            },
        )
        await _seed_row(
            session,
            ai_metadata={
                "garment_type": "coat",
                "style": "tailored",
                "material": "wool",
                "color_palette": ["black"],
                "pattern": "solid",
                "season": "winter",
                "occasion": "formal",
                "consumer_profile": "professional",
                "trend_notes": "office",
                "location_context": {"continent": "Asia", "country": "Japan", "city": "Tokyo"},
                "time_context": {"year": 2024, "month": 1, "season": "winter"},
            },
        )

    r = await client.get(
        "/api/images",
        params={"country": "Portugal", "year": 2023, "designer_name": "Alex"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["structured"]["garment_type"] == "dress"


@pytest.mark.asyncio
async def test_filter_month_and_continent(client: AsyncClient):
    async with SessionLocal() as session:
        await _seed_row(
            session,
            ai_metadata={
                "garment_type": "sandal",
                "location_context": {"continent": "Africa", "country": "Morocco", "city": "Marrakesh"},
                "time_context": {"year": 2022, "month": 8, "season": "summer"},
            },
        )

    r = await client.get(
        "/api/images",
        params={"continent": "Africa", "month": 8, "designer_name": "Alex"},
    )
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_filtered_unit_style():
    """Direct service-layer check for time_season filter."""
    async with SessionLocal() as session:
        meta = StructuredGarmentMetadata(
            garment_type="jacket",
            location_context=LocationContext(continent="North America", country="USA", city="NYC"),
            time_context=TimeContext(year=2024, month=10, season="fall"),
        )
        await _seed_row(session, ai_metadata=structured_to_dict(meta))

        result = await list_filtered(
            session,
            None,
            {"time_season": "fall", "city": "NYC", "designer_name": "Alex"},
        )
        assert len(result.rows) == 1


async def _seed_row(session: AsyncSession, ai_metadata: dict) -> None:
    from datetime import datetime, timezone

    rec = ImageRecord(
        file_path="/tmp/fake.jpg",
        description="seed",
        ai_metadata=ai_metadata,
        designer_tags=[],
        designer_notes=None,
        designer_name="Alex",
        user_caption=None,
        upload_metadata=None,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec)
    await session.commit()
