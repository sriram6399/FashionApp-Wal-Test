from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_backend.classifier import classify_image_bytes
from fashion_backend.config import settings
from fashion_backend.embeddings import embed_text
from fashion_backend.vector_store import query_similar, upsert_image_vector
from fashion_backend.models import ImageRecord
from fashion_backend.schemas import (
    ImageCreateResponse,
    ImageListSearchMeta,
    ImagePatch,
    StructuredGarmentMetadata,
    structured_from_dict,
    structured_to_dict,
)

@dataclass(frozen=True)
class ListFilteredResult:
    rows: list[ImageRecord]
    search: ImageListSearchMeta | None = None


# When every vector hit is above the "close match" distance, still cap how many we return.
SEMANTIC_FALLBACK_MAX = 10


def _read_structured(row: ImageRecord) -> StructuredGarmentMetadata:
    return structured_from_dict(row.ai_metadata or {})


def row_to_response(row: ImageRecord, base_url: str = "") -> ImageCreateResponse:
    path = Path(row.file_path).name
    url = f"{base_url}/api/files/{path}" if base_url else f"/api/files/{path}"
    return ImageCreateResponse(
        id=row.id,
        description=row.description,
        structured=_read_structured(row),
        designer_tags=list(row.designer_tags or []),
        designer_notes=row.designer_notes,
        designer_name=row.designer_name,
        user_caption=row.user_caption,
        upload_metadata=row.upload_metadata,
        file_url=url,
        created_at=row.created_at,
    )


def build_search_document(row: ImageRecord) -> str:
    """Text embedded for Chroma — AI description, user caption/metadata, structured fields, designer notes."""
    s = _read_structured(row)
    parts: list[str] = [
        f"A fashion image featuring a {s.garment_type or 'garment'} in a {s.style or 'general'} style.",
        f"Material: {s.material or 'unknown'}.",
        f"Pattern: {s.pattern or 'solid'}.",
        f"Season: {s.season or 'all-season'}.",
        f"Colors: {', '.join(s.color_palette) if s.color_palette else 'unknown'}.",
        f"Designed for: {s.consumer_profile or 'anyone'} on a {s.occasion or 'casual'} occasion."
    ]
    if row.user_caption:
        parts.append(f"User caption: {row.user_caption}")
    if row.description:
        parts.append(f"AI description: {row.description}")
    if row.designer_notes:
        parts.append(f"Designer notes: {row.designer_notes}")
    if row.designer_tags:
        parts.append("Designer tags: " + ", ".join(row.designer_tags))
    if row.designer_name:
        parts.append(f"Designer name: {row.designer_name}")
    if s.trend_notes:
        parts.append(f"Trend notes: {s.trend_notes}")
        
    return "\n".join(parts)


async def index_row_for_search(row: ImageRecord) -> None:
    """Embed and upsert into Chroma. No-op without API key; failures are swallowed (lexical search remains)."""
    if not settings.llm_api_key:
        return
    try:
        doc = build_search_document(row)
        vec = await embed_text(doc)
        await upsert_image_vector(row.id, doc, vec)
    except Exception:
        pass


async def save_upload_and_classify(
    session: AsyncSession,
    image_bytes: bytes,
    content_type: str,
    caption: str | None = None,
    upload_metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    *,
    llm_client: Any | None = None,
) -> ImageCreateResponse:
    ext = ".jpg"
    if "png" in content_type.lower():
        ext = ".png"
    elif "webp" in content_type.lower():
        ext = ".webp"
    name = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_dir / name
    dest.write_bytes(image_bytes)

    mime = content_type.split(";")[0].strip() or "image/jpeg"
    tag_list = list(tags or [])
    result = await classify_image_bytes(
        image_bytes,
        mime=mime,
        caption=caption,
        upload_metadata=upload_metadata,
        tags=tag_list or None,
        llm_client=llm_client,
    )

    meta = structured_to_dict(result.structured)
    cap = (caption or "").strip() or None
    rec = ImageRecord(
        file_path=str(dest),
        description=result.description,
        ai_metadata=meta,
        designer_tags=tag_list,
        designer_notes=None,
        designer_name=None,
        user_caption=cap,
        upload_metadata=upload_metadata,
        created_at=datetime.now(timezone.utc),
    )
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    await index_row_for_search(rec)
    return row_to_response(rec)


async def patch_image(session: AsyncSession, image_id: int, patch: ImagePatch) -> ImageRecord | None:
    row = await session.get(ImageRecord, image_id)
    if not row:
        return None
    if patch.designer_tags is not None:
        row.designer_tags = patch.designer_tags
    if patch.designer_notes is not None:
        row.designer_notes = patch.designer_notes
    if patch.designer_name is not None:
        row.designer_name = patch.designer_name
    await session.commit()
    await session.refresh(row)
    await index_row_for_search(row)
    return row


def _text_blob(row: ImageRecord) -> str:
    parts = [
        row.description or "",
        row.user_caption or "",
        json.dumps(row.upload_metadata or {}, default=str),
        row.designer_notes or "",
        " ".join(row.designer_tags or []),
    ]
    s = _read_structured(row)
    d = structured_to_dict(s)
    parts.append(json_dumps_safe(d))
    return " ".join(parts).lower()


def json_dumps_safe(d: dict[str, Any]) -> str:
    return json.dumps(d, default=str)


def _match_query(text: str, q: str | None) -> bool:
    if not q or not q.strip():
        return True
    words = [w.lower() for w in q.split() if w.strip()]
    if not words:
        return True
    return all(w in text for w in words)


def _scalar_eq(a: str | None, b: str | None) -> bool:
    if not b:
        return True
    return (a or "").strip().lower() == b.strip().lower()


def _list_intersect(item_colors: list[str], wanted: list[str]) -> bool:
    if not wanted:
        return True
    low = {c.lower() for c in item_colors}
    return any(w.lower() in low for w in wanted)


def row_matches_filters(row: ImageRecord, filters: dict[str, Any]) -> bool:
    s = _read_structured(row)
    loc = s.location_context
    tm = s.time_context

    if filters.get("garment_type") and not _scalar_eq(s.garment_type, filters["garment_type"]):
        return False
    if filters.get("category") and not _scalar_eq(s.category, filters["category"]):
        return False
    if filters.get("style") and not _scalar_eq(s.style, filters["style"]):
        return False
    if filters.get("material") and not _scalar_eq(s.material, filters["material"]):
        return False
    if filters.get("pattern") and not _scalar_eq(s.pattern, filters["pattern"]):
        return False
    if filters.get("season") and not _scalar_eq(s.season, filters["season"]):
        return False
    if filters.get("occasion") and not _scalar_eq(s.occasion, filters["occasion"]):
        return False
    if filters.get("consumer_profile") and not _scalar_eq(s.consumer_profile, filters["consumer_profile"]):
        return False
    if filters.get("trend_notes") and not _scalar_eq(s.trend_notes, filters["trend_notes"]):
        return False
    if filters.get("continent") and not (loc and _scalar_eq(loc.continent, filters["continent"])):
        return False
    if filters.get("country") and not (loc and _scalar_eq(loc.country, filters["country"])):
        return False
    if filters.get("city") and not (loc and _scalar_eq(loc.city, filters["city"])):
        return False
    if filters.get("year") is not None:
        y = filters["year"]
        if tm is None or tm.year != int(y):
            return False
    if filters.get("month") is not None:
        m = filters["month"]
        if tm is None or tm.month != int(m):
            return False
    if filters.get("time_season") and not (tm and _scalar_eq(tm.season, filters["time_season"])):
        return False
    if filters.get("designer_name") and not _scalar_eq(row.designer_name, filters["designer_name"]):
        return False
    if filters.get("designer_tags"):
        wanted = filters["designer_tags"]
        tags = row.designer_tags or []
        if not any(_scalar_eq(t, wanted) for t in tags):
            return False
    cp = filters.get("color_palette")
    if cp:
        wanted = cp if isinstance(cp, list) else [cp]
        if not _list_intersect(s.color_palette or [], wanted):
            return False
    return True


def _search_meta_top_matches() -> ImageListSearchMeta:
    return ImageListSearchMeta(
        kind="semantic",
        message="Matches for your search, ordered by relevance.",
    )


def _search_meta_fallback() -> ImageListSearchMeta:
    return ImageListSearchMeta(
        kind="semantic_fallback",
        message=(
            "No very close match for your search; showing up to "
            f"{SEMANTIC_FALLBACK_MAX} of the closest available results instead."
        ),
    )


def _search_meta_lexical() -> ImageListSearchMeta:
    return ImageListSearchMeta(
        kind="lexical",
        message="Text matches for your search.",
    )


def _search_meta_none() -> ImageListSearchMeta:
    return ImageListSearchMeta(
        kind="none",
        message="No results found for your search.",
    )


async def list_filtered(
    session: AsyncSession,
    q: str | None,
    filters: dict[str, Any],
) -> ListFilteredResult:
    stmt: Select[tuple[ImageRecord]] = select(ImageRecord).order_by(ImageRecord.created_at.desc())
    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    q_clean = (q or "").strip()
    if not q_clean:
        return ListFilteredResult(
            rows=[r for r in rows if row_matches_filters(r, filters)],
            search=None,
        )

    if settings.llm_api_key:
        try:
            q_vec = await embed_text(q_clean)
            ranked = await query_similar(q_vec, top_k=120)
            if ranked:
                row_map = {r.id: r for r in rows}
                out: list[ImageRecord] = []
                best_fallback: list[ImageRecord] = []

                for image_id, _dist in ranked:
                    r = row_map.get(image_id)
                    if r is None or not row_matches_filters(r, filters):
                        continue

                    best_fallback.append(r)

                    # Ignore vectors fundamentally unrelated to the search query
                    if _dist > 0.65:
                        continue

                    out.append(r)

                if out:
                    return ListFilteredResult(
                        rows=out,
                        search=_search_meta_top_matches(),
                    )
                if best_fallback:
                    return ListFilteredResult(
                        rows=best_fallback[:SEMANTIC_FALLBACK_MAX],
                        search=_search_meta_fallback(),
                    )
        except Exception:
            pass

    out_lex: list[ImageRecord] = []
    for row in rows:
        if not row_matches_filters(row, filters):
            continue
        blob = _text_blob(row)
        if _match_query(blob, q_clean):
            out_lex.append(row)
    if out_lex:
        return ListFilteredResult(
            rows=out_lex,
            search=_search_meta_lexical(),
        )
    return ListFilteredResult(rows=[], search=_search_meta_none())


async def collect_filter_facets(session: AsyncSession) -> dict[str, Any]:
    result = await session.execute(select(ImageRecord))
    rows = result.scalars().all()
    facets: dict[str, set[Any]] = {
        "garment_type": set(),
        "category": set(),
        "style": set(),
        "material": set(),
        "color_palette": set(),
        "pattern": set(),
        "season": set(),
        "occasion": set(),
        "consumer_profile": set(),
        "trend_notes": set(),
        "continent": set(),
        "country": set(),
        "city": set(),
        "year": set(),
        "month": set(),
        "time_season": set(),
        "designer_name": set(),
        "designer_tags": set(),
    }
    for row in rows:
        s = _read_structured(row)
        loc = s.location_context
        tm = s.time_context
        for key, val in [
            ("garment_type", s.garment_type),
            ("category", s.category),
            ("style", s.style),
            ("material", s.material),
            ("pattern", s.pattern),
            ("season", s.season),
            ("occasion", s.occasion),
            ("consumer_profile", s.consumer_profile),
            ("trend_notes", s.trend_notes),
        ]:
            if val:
                facets[key].add(val)
        for c in s.color_palette or []:
            if c:
                facets["color_palette"].add(c)
        if loc:
            if loc.continent:
                facets["continent"].add(loc.continent)
            if loc.country:
                facets["country"].add(loc.country)
            if loc.city:
                facets["city"].add(loc.city)
        if tm:
            if tm.year is not None:
                facets["year"].add(tm.year)
            if tm.month is not None:
                facets["month"].add(tm.month)
            if tm.season:
                facets["time_season"].add(tm.season)
        if row.designer_name:
            facets["designer_name"].add(row.designer_name)
        for t in row.designer_tags or []:
            if t:
                facets["designer_tags"].add(t)
    return {
        "garment_type": sorted(facets["garment_type"], key=str),
        "category": sorted(facets["category"], key=str),
        "style": sorted(facets["style"], key=str),
        "material": sorted(facets["material"], key=str),
        "color_palette": sorted(facets["color_palette"], key=str),
        "pattern": sorted(facets["pattern"], key=str),
        "season": sorted(facets["season"], key=str),
        "occasion": sorted(facets["occasion"], key=str),
        "consumer_profile": sorted(facets["consumer_profile"], key=str),
        "trend_notes": sorted(facets["trend_notes"], key=str),
        "continent": sorted(facets["continent"], key=str),
        "country": sorted(facets["country"], key=str),
        "city": sorted(facets["city"], key=str),
        "year": sorted(facets["year"], key=int),
        "month": sorted(facets["month"], key=int),
        "time_season": sorted(facets["time_season"], key=str),
        "designer_name": sorted(facets["designer_name"], key=str),
        "designer_tags": sorted(facets["designer_tags"], key=str),
    }
