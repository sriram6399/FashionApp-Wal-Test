"""
Wipe local library data: SQLite `images` rows, files under uploads/, and Chroma (`data/chroma/`).

Uses paths from deploy/.env via fashion_backend.config. Stop the API server first to avoid DB locks.

  python eval/reset_local_library.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND))


async def main_async() -> None:
    from sqlalchemy import text

    from fashion_backend.config import settings
    from fashion_backend.db import engine
    from fashion_backend.vector_store import clear_cache

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    n_files = 0
    for f in settings.upload_dir.iterdir():
        if f.is_file():
            f.unlink(missing_ok=True)
            n_files += 1

    chroma_dir = settings.data_dir / "chroma"
    if chroma_dir.is_dir():
        shutil.rmtree(chroma_dir, ignore_errors=True)
    clear_cache()

    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM images"))

    print(f"Cleared images table, removed {n_files} file(s) from {settings.upload_dir}, removed Chroma at {chroma_dir}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
