from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    engineering_type: Literal["building", "municipal"]
    target_pages: int = Field(default=50, ge=1, le=500)


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    facts_version: int
    updated_at: datetime

