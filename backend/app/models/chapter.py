from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    outline_position: Mapped[int] = mapped_column(Integer, default=0)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)


class ChapterVersion(Base):
    __tablename__ = "chapter_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(30), default="human")
    fact_version: Mapped[int] = mapped_column(Integer, default=1)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    open_issues: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

