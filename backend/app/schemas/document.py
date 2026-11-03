from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParseBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ordinal: int
    text: str
    location: dict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    media_type: str
    extension: str
    size_bytes: int
    status: str
    error_message: str | None
    created_at: datetime
    blocks: list[ParseBlockRead] = []
    block_count: int = 0
    archive_path: str | None = None
    origin_paths: list[str] = []
    parent_id: str | None = None
    kind: str = "document"
    analysis_summary: dict = {}

