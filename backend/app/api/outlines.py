from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.project import Project
from ..schemas.chapter import OutlineUpdate
from ..services.outlines import get_outline, save_outline

router = APIRouter(prefix="/api/projects/{project_id}/outline", tags=["outline"])


@router.get("")
def read_outline(project_id: str, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return get_outline(session, project)


@router.put("")
def update_outline(project_id: str, data: OutlineUpdate, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return save_outline(session, project, [item.model_dump() for item in data.items])

