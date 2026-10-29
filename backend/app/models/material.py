from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class MaterialRecord(Base):
    __tablename__ = "material_records"

    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id"), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    archive_path: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(40), default="document")
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
