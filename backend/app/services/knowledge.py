from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models.knowledge_item import KnowledgeItem


def search_knowledge(session: Session, keyword: str | None = None) -> list[KnowledgeItem]:
    query = select(KnowledgeItem)
    if keyword:
        query = query.where(or_(KnowledgeItem.title.contains(keyword), KnowledgeItem.body.contains(keyword)))
    return list(session.scalars(query.order_by(KnowledgeItem.title)))

