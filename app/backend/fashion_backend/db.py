from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from fashion_backend.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def _migrate_sqlite_images_columns(sync_conn) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(sync_conn)
    if not insp.has_table("images"):
        return
    cols = {c["name"] for c in insp.get_columns("images")}
    if "user_caption" not in cols:
        sync_conn.execute(text("ALTER TABLE images ADD COLUMN user_caption TEXT"))
    if "upload_metadata" not in cols:
        sync_conn.execute(text("ALTER TABLE images ADD COLUMN upload_metadata TEXT"))


async def init_db() -> None:
    from fashion_backend import models  # noqa: F401

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite_images_columns)
