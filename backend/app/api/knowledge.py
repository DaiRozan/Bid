from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.knowledge_item import KnowledgeItem
from ..services.knowledge import search_knowledge

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeCreate(BaseModel):
    kind: str
    title: str
    body: str
    source: str
    standard_number: str | None = None
    applicability: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_knowledge(data: KnowledgeCreate, session: Session = Depends(get_db)):
    item = KnowledgeItem(**data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item.__dict__ | {"_sa_instance_state": None}


@router.get("")
def list_knowledge(keyword: str | None = None, session: Session = Depends(get_db)):
    return [item.__dict__ | {"_sa_instance_state": None} for item in search_knowledge(session, keyword)]

