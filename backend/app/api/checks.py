from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.project import Project
from ..models.review_issue import ReviewIssue
from ..services.checks import run_checks

router = APIRouter(prefix="/api/projects/{project_id}", tags=["checks"])


@router.post("/checks/run")
def check_project(project_id: str, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    issues = run_checks(session, project)
    return {"status": "issues_found" if issues else "passed", "issues": issues}


@router.get("/issues")
def list_issues(project_id: str, session: Session = Depends(get_db)):
    return [
        {"id": issue.id, "code": issue.code, "severity": issue.severity, "message": issue.message, "location": issue.location, "status": issue.status}
        for issue in session.scalars(select(ReviewIssue).where(ReviewIssue.project_id == project_id).order_by(ReviewIssue.created_at.desc()))
    ]

