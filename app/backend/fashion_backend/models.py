from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from fashion_backend.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ImageRecord(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    ai_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    designer_tags: Mapped[list] = mapped_column(JSON, default=list)
    designer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    designer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    user_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
