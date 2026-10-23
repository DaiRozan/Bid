from pydantic import BaseModel, Field, model_validator


class ChapterBlock(BaseModel):
    type: str
    text: str | None = None
    heading_level: int | None = Field(default=None, ge=1, le=6)
    rows: list[list[str]] | None = None

    @model_validator(mode="after")
    def validate_block(self):
        if self.type == "paragraph" and self.text is None:
            raise ValueError("段落必须包含文字")
        if self.type == "table" and self.rows is None:
            raise ValueError("表格必须包含行")
        if self.type not in {"paragraph", "table"}:
            raise ValueError("不支持的正文块类型")
        return self


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    outline_position: int = Field(default=0, ge=0)
    blocks: list[ChapterBlock] = Field(default_factory=list)


class ChapterUpdate(BaseModel):
    blocks: list[ChapterBlock]


class OutlineItem(BaseModel):
    title: str
    body: str = ""
    required: bool = False
    budget_pages: int = Field(default=1, ge=0)


class OutlineUpdate(BaseModel):
    items: list[OutlineItem]

