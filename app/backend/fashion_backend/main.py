from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from fashion_backend.config import settings
from fashion_backend.db import get_session, init_db
from fashion_backend.schemas import FilterOptions, ImagePatch
from fashion_backend.services import images as image_service


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
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 20MB)")
    rec = await image_service.save_upload_and_classify(session, data, file.content_type)
    return rec.model_dump(mode="json")


@app.get("/api/images")
async def list_images(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = Query(default=None),
    garment_type: str | None = Query(default=None),
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
    color_palette: list[str] | None = Query(default=None),
):
    filters: dict[str, Any] = {
        k: v
        for k, v in {
            "garment_type": garment_type,
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
            "color_palette": color_palette,
        }.items()
        if v is not None and v != []
    }
    rows = await image_service.list_filtered(session, q, filters)
    return [image_service.row_to_response(r).model_dump(mode="json") for r in rows]


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
    return {"status": "ok", "classifier": "openai" if settings.openai_api_key else "mock"}
