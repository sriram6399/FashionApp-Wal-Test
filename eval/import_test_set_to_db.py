"""
Load eval/test_images into the app's library database (same pipeline as POST /api/images).

Uses keys and paths from deploy/.env via fashion_backend.config (run from repo root).

  pip install -r app/backend/requirements.txt
  python eval/import_test_set_to_db.py

Each image triggers one vision classification (OpenRouter/OpenAI when configured).
Imports one DB row per entry in eval/ground_truth.json (often ~50 after prepare). If you see fewer,
re-run: python eval/prepare_color_test_set.py.

Optional in deploy/.env for flaky Windows TLS (see deploy/.env.example):
  HTTPX_TRUST_ENV=0  — ignore system proxy env (often fixes SSLV3_ALERT_BAD_RECORD_MAC behind broken proxies)
  HTTPX_NO_KEEPALIVE=1  — new TCP+TLS per request (helps some antivirus / middleboxes)
  EVAL_IMPORT_DELAY_SEC=1.5  — small pause between imports to reduce burst load

Images are read from disk before each API call. Retries cover TLS, connection drops, HTTP 5xx, and rate limits from OpenRouter.
This script reuses one LLM client for the whole run so connections are not leaked across 50 imports.

Re-run after a crash: by default rows with caption eval:<filename> are skipped so you can resume without duplicates.
Force re-import everything: python eval/import_test_set_to_db.py --no-skip

Scan every file in test_images (not only ground_truth.json):

  python eval/import_test_set_to_db.py --all-images

If you only need accuracy metrics and not the DB, use eval/evaluate.py alone instead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import ssl
import sys
from pathlib import Path

from openai import APIConnectionError, InternalServerError, RateLimitError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND))

EVAL_DIR = Path(__file__).resolve().parent
_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def _list_all_images(img_dir: Path) -> list[Path]:
    if not img_dir.is_dir():
        return []
    out = [p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES]
    return sorted(out, key=lambda p: p.name.lower())


def _ground_truth_by_filename(gt_path: Path) -> dict[str, dict]:
    if not gt_path.is_file():
        return {}
    data = json.loads(gt_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return {}
    return {str(r["file"]): r for r in data if isinstance(r, dict) and r.get("file")}


def _content_type(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".png":
        return "image/png"
    if suf in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suf == ".webp":
        return "image/webp"
    return "image/jpeg"


async def _save_with_retries(
    session,
    data: bytes,
    ct: str,
    cap: str,
    meta: dict,
    tags: list[str],
    *,
    llm_client: object | None = None,
) -> None:
    delays = (3.0, 10.0, 25.0, 45.0)
    from fashion_backend.services.images import save_upload_and_classify

    for attempt in range(len(delays) + 1):
        try:
            await save_upload_and_classify(
                session,
                data,
                ct,
                caption=cap,
                upload_metadata=meta,
                tags=tags,
                llm_client=llm_client,
            )
            return
        except (APIConnectionError, InternalServerError, RateLimitError, ssl.SSLError) as e:
            if attempt >= len(delays):
                raise
            d = delays[attempt]
            print(f"  transient LLM/network error, retry in {d:.0f}s… ({type(e).__name__})")
            await asyncio.sleep(d)


async def main_async(*, skip_existing: bool, all_images: bool) -> None:
    gt_path = EVAL_DIR / "ground_truth.json"
    img_dir = EVAL_DIR / "test_images"

    from sqlalchemy import select

    from fashion_backend.config import settings
    from fashion_backend.db import SessionLocal, init_db
    from fashion_backend.models import ImageRecord

    if not settings.llm_api_key:
        print(
            "No OPENROUTER_API_KEY or OPENAI_API_KEY in deploy/.env — add a key for real classifications, "
            "or this import will use the mock classifier."
        )

    await init_db()

    gt_by_file = _ground_truth_by_filename(gt_path)
    if all_images:
        paths = _list_all_images(img_dir)
        if not paths:
            print(f"No images found in {img_dir}")
            sys.exit(1)
        if not gt_path.is_file():
            print("Note: ground_truth.json missing — importing from folder only (no eval label merge).")
        print(f"Scanning test_images: {len(paths)} file(s) to process.")
    else:
        if not gt_path.is_file():
            print("Missing ground_truth.json — run: python eval/prepare_color_test_set.py")
            print("Or use: python eval/import_test_set_to_db.py --all-images")
            sys.exit(1)
        records = json.loads(gt_path.read_text(encoding="utf-8"))
        paths = []
        for rec in records:
            fname = rec.get("file")
            if not isinstance(fname, str):
                continue
            p = img_dir / fname
            if p.is_file():
                paths.append(p)
            else:
                print(f"Skip missing: {p}")
        print(f"ground_truth.json lists {len(records)} image(s); {len(paths)} file(s) found on disk to import.")
        if len(records) < 50:
            print("For ~50 images: run `python eval/prepare_color_test_set.py` (wait for completion).")

    n_new = 0
    n_skip = 0
    delay_between = settings.eval_import_delay_sec

    from fashion_backend.llm_client import build_async_openai_client

    llm = build_async_openai_client() if settings.llm_api_key else None
    try:
        async with SessionLocal() as session:
            for path in paths:
                fname = path.name
                data = path.read_bytes()
                ct = _content_type(path)
                cap = f"eval:{fname}"
                rec = gt_by_file.get(fname, {})
                meta: dict = {"source": "eval_test_set", "file": fname}
                if rec:
                    meta["source"] = rec.get("source") or meta["source"]
                    for k in ("source_title", "source_url"):
                        if rec.get(k) is not None:
                            meta[k] = rec[k]
                if skip_existing:
                    q = await session.execute(select(ImageRecord.id).where(ImageRecord.user_caption == cap).limit(1))
                    if q.scalar_one_or_none() is not None:
                        n_skip += 1
                        print(f"Skip (already in DB) {fname} ({n_skip} skipped)")
                        continue
                await _save_with_retries(
                    session,
                    data,
                    ct,
                    cap,
                    meta,
                    ["eval"],
                    llm_client=llm,
                )
                n_new += 1
                print(f"Imported {fname} ({n_new} new this run, {len(paths)} in this run)")
                if delay_between > 0:
                    await asyncio.sleep(delay_between)
    finally:
        if llm is not None:
            await llm.close()

    print(f"Done. {n_new} imported, {n_skip} skipped. DB: {settings.database_url}")


def main() -> None:
    p = argparse.ArgumentParser(description="Import eval/test_images into the library DB.")
    p.add_argument(
        "--no-skip",
        action="store_true",
        help="Import every file even if eval:<filename> already exists (duplicates).",
    )
    p.add_argument(
        "--all-images",
        action="store_true",
        help="Process every .jpg/.jpeg/.png/.webp in eval/test_images (OpenRouter when key set). "
        "Optional ground_truth.json merges source/source_url for matching filenames.",
    )
    args = p.parse_args()
    asyncio.run(main_async(skip_existing=not args.no_skip, all_images=args.all_images))


if __name__ == "__main__":
    main()
