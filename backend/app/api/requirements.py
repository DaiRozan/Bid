from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.requirement import Requirement

router = APIRouter(prefix="/api/projects/{project_id}/requirements", tags=["requirements"])


@router.get("")
def list_requirements(project_id: str, session: Session = Depends(get_db)):
    return [item.__dict__ | {"_sa_instance_state": None} for item in session.scalars(select(Requirement).where(Requirement.project_id == project_id))]

