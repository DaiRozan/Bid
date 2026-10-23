from pydantic import BaseModel, Field


class FactCandidate(BaseModel):
    field_name: str
    raw_value: str | None = None
    unit: str | None = None
    source_block_ids: list[str] = Field(default_factory=list)


class RequirementCandidate(BaseModel):
    text: str
    category: str | None = None
    score: str | None = None
    source_block_ids: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    facts: list[FactCandidate] = Field(default_factory=list)
    requirements: list[RequirementCandidate] = Field(default_factory=list)

