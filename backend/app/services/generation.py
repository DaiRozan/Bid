import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..adapters.deepseek import DeepSeekClient
from ..models.chapter import Chapter
from ..models.fact import Fact
from ..models.knowledge_item import KnowledgeItem
from ..models.project import Project


def generate_chapter(*, session: Session, project: Project, chapter: Chapter, facts: list[dict], knowledge: list[dict]) -> dict:
    from pydantic import BaseModel, Field

    class Generated(BaseModel):
        blocks: list[dict] = Field(default_factory=list)
        citations: list[dict] = Field(default_factory=list)
        open_issues: list[str] = Field(default_factory=list)

    prompt = {
        "chapter": {"title": chapter.title},
        "facts": facts,
        "knowledge": knowledge,
    }
    return asyncio.run(
        DeepSeekClient().complete_json(
            "仅根据已确认项目事实和明确引用的资料生成章节；未知信息保持待确认。",
            prompt,
            Generated,
        )
    ).model_dump()


def confirmed_facts(session: Session, project_id: str) -> list[dict]:
    return [
        {"field_name": fact.field_name, "value": fact.confirmed_value}
        for fact in session.scalars(select(Fact).where(Fact.project_id == project_id, Fact.status == "confirmed"))
        if fact.confirmed_value
    ]

