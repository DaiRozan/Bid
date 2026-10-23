from sqlalchemy.orm import Session

from ..models.job import Job


def create_job(session: Session, project_id: str, kind: str) -> Job:
    job = Job(project_id=project_id, kind=kind, status="queued")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

