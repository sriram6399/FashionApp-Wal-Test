"""End-to-end: upload image, receive classification, filter library."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_then_filter_by_garment_type(client: AsyncClient, tiny_png: bytes):
    up = await client.post(
        "/api/images",
        files={"file": ("x.png", tiny_png, "image/png")},
    )
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["id"] >= 1
    assert body["description"]
    assert "structured" in body
    gt = body["structured"].get("garment_type")
    assert gt

    r = await client.get("/api/images", params={"garment_type": gt})
    assert r.status_code == 200
    listed = r.json()
    rows = listed["items"]
    assert len(rows) >= 1
    assert any(x["id"] == body["id"] for x in rows)

    fq = await client.get("/api/filters")
    assert fq.status_code == 200
    facets = fq.json()
    assert "garment_type" in facets
    assert isinstance(facets["garment_type"], list)
