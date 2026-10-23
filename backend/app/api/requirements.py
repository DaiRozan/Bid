from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.requirement import Requirement

router = APIRouter(prefix="/api/projects/{project_id}/requirements", tags=["requirements"])


class RequirementInput(BaseModel):
    text: str
    category: str | None = None
    score: str | None = None


@router.get("")
def list_requirements(project_id: str, session: Session = Depends(get_db)):
    return [item.__dict__ | {"_sa_instance_state": None} for item in session.scalars(select(Requirement).where(Requirement.project_id == project_id))]


@router.post("/manual", status_code=status.HTTP_201_CREATED)
def create_requirement(project_id: str, data: RequirementInput, session: Session = Depends(get_db)):
    item = Requirement(project_id=project_id, **data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item.__dict__ | {"_sa_instance_state": None}

