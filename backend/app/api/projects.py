from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas.project import ProjectCreate, ProjectRead
from ..services.projects import create_project, get_project, list_projects

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create(data: ProjectCreate, session: Session = Depends(get_db)) -> ProjectRead:
    return create_project(session, data)


@router.get("", response_model=list[ProjectRead])
def list_all(session: Session = Depends(get_db)) -> list[ProjectRead]:
    return list_projects(session)


@router.get("/{project_id}", response_model=ProjectRead)
def get_one(project_id: str, session: Session = Depends(get_db)) -> ProjectRead:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project

