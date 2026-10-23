from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.fact import Fact
from ..models.chapter import Chapter
from ..models.project import Project

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


@router.post("/manual")
def create_manual_fact(project_id: str, values: dict, session: Session = Depends(get_db)):
    fact = Fact(
        project_id=project_id,
        field_name=values.get("field_name", ""),
        raw_value=values.get("raw_value"),
        confirmed_value=values.get("confirmed_value"),
        status="confirmed" if values.get("confirmed_value") else "unconfirmed",
    )
    session.add(fact)
    if fact.status == "confirmed":
        session.get(Project, project_id).facts_version += 1
    session.commit()
    session.refresh(fact)
    return fact.__dict__ | {"_sa_instance_state": None}


@router.put("/{fact_id}")
def update_fact(project_id: str, fact_id: str, values: dict, session: Session = Depends(get_db)):
    fact = session.get(Fact, fact_id)
    if fact is None or fact.project_id != project_id:
        raise HTTPException(status_code=404, detail="事实不存在")
    fact.confirmed_value = values.get("confirmed_value")
    fact.status = "confirmed" if fact.confirmed_value else "unconfirmed"
    project = session.get(Project, project_id)
    project.facts_version += 1
    for chapter in session.scalars(select(Chapter).where(Chapter.project_id == project_id)):
        chapter.stale = True
    session.commit()
    session.refresh(fact)
    return fact.__dict__ | {"_sa_instance_state": None}

