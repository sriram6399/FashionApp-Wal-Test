from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_backend.config import settings
from fashion_backend.db import get_session, init_db
from fashion_backend.schemas import FilterOptions, ImagePatch
from fashion_backend.services import images as image_service
from fashion_backend.tag_input import parse_tags_field


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Fashion Inspiration Library", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/images")
async def upload_image(
    session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    tags: str | None = Form(
        default=None,
        description="Comma-separated tags or JSON array string, e.g. market,linen or [\"streetwear\",\"Tokyo\"]",
    ),
    upload_metadata: str | None = Form(default=None),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(400, f"Image too large (max {settings.max_upload_mb}MB)")
    try:
        tag_list = parse_tags_field(tags)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(400, str(e)) from e
    meta_obj: dict[str, Any] | None = None
    if upload_metadata and upload_metadata.strip():
        try:
            parsed = json.loads(upload_metadata)
        except json.JSONDecodeError:
            raise HTTPException(400, "upload_metadata must be valid JSON")
        if not isinstance(parsed, dict):
            raise HTTPException(400, "upload_metadata must be a JSON object")
        meta_obj = parsed
    rec = await image_service.save_upload_and_classify(
        session,
        data,
        file.content_type,
        caption=caption,
        upload_metadata=meta_obj,
        tags=tag_list,
    )
    return rec.model_dump(mode="json")


@app.get("/api/images")
async def list_images(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = Query(default=None),
    garment_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    style: str | None = Query(default=None),
    material: str | None = Query(default=None),
    pattern: str | None = Query(default=None),
    season: str | None = Query(default=None),
    occasion: str | None = Query(default=None),
    consumer_profile: str | None = Query(default=None),
    trend_notes: str | None = Query(default=None),
    continent: str | None = Query(default=None),
    country: str | None = Query(default=None),
    city: str | None = Query(default=None),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    time_season: str | None = Query(default=None),
    designer_name: str | None = Query(default=None),
    designer_tags: str | None = Query(default=None),
    color_palette: list[str] | None = Query(default=None),
):
    filters: dict[str, Any] = {
        k: v
        for k, v in {
            "garment_type": garment_type,
            "category": category,
            "style": style,
            "material": material,
            "pattern": pattern,
            "season": season,
            "occasion": occasion,
            "consumer_profile": consumer_profile,
            "trend_notes": trend_notes,
            "continent": continent,
            "country": country,
            "city": city,
            "year": year,
            "month": month,
            "time_season": time_season,
            "designer_name": designer_name,
            "designer_tags": designer_tags,
            "color_palette": color_palette,
        }.items()
        if v is not None and v != []
    }
    listed = await image_service.list_filtered(session, q, filters)
    payload: dict[str, Any] = {
        "items": [image_service.row_to_response(r).model_dump(mode="json") for r in listed.rows],
        "search": listed.search.model_dump(mode="json") if listed.search else None,
    }
    return payload


@app.get("/api/filters")
async def get_filters(session: Annotated[AsyncSession, Depends(get_session)]):
    raw = await image_service.collect_filter_facets(session)
    return FilterOptions(**raw).model_dump(mode="json")


@app.patch("/api/images/{image_id}")
async def update_image(
    image_id: int,
    patch: ImagePatch,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    row = await image_service.patch_image(session, image_id, patch)
    if not row:
        raise HTTPException(404, "Image not found")
    return image_service.row_to_response(row).model_dump(mode="json")


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    safe = Path(filename).name
    path = settings.upload_dir / safe
    if not path.is_file() or not str(path.resolve()).startswith(str(settings.upload_dir.resolve())):
        raise HTTPException(404, "Not found")
    return FileResponse(path)


@app.get("/api/health")
async def health():
    if not settings.llm_api_key:
        provider = "mock"
    elif settings.uses_openrouter:
        provider = "openrouter"
    else:
        provider = "openai"
    return {
        "status": "ok",
        "classifier": provider,
        "model": settings.vision_model_resolved,
        "search": "vector" if settings.llm_api_key else "lexical",
        "embedding_model": settings.embedding_model_resolved if settings.llm_api_key else None,
    }
