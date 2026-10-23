from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.fact import Fact

router = APIRouter(prefix="/api/projects/{project_id}/facts", tags=["facts"])


@router.get("")
def list_facts(project_id: str, session: Session = Depends(get_db)):
    return [fact.__dict__ | {"_sa_instance_state": None} for fact in session.scalars(select(Fact).where(Fact.project_id == project_id))]


@router.post("/confirm")
def confirm_facts(project_id: str, values: dict[str, str], session: Session = Depends(get_db)):
    facts = list(session.scalars(select(Fact).where(Fact.project_id == project_id)))
    for fact in facts:
        if fact.id in values:
            fact.confirmed_value = values[fact.id]
            fact.status = "confirmed"
    session.commit()
    return list_facts(project_id, session)

