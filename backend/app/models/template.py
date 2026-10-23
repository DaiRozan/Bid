from uuid import uuid4

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engineering_type: Mapped[str] = mapped_column(String(30), unique=True)
    items: Mapped[list] = mapped_column(JSON, default=list)

