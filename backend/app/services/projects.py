from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.project import Project
from ..schemas.project import ProjectCreate


def create_project(session: Session, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def list_projects(session: Session) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.updated_at.desc())))


def get_project(session: Session, project_id: str) -> Project | None:
    return session.get(Project, project_id)

