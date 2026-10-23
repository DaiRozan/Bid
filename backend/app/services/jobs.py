from sqlalchemy.orm import Session

from ..models.job import Job


def create_job(session: Session, project_id: str, kind: str, target_id: str | None = None) -> Job:
    job = Job(project_id=project_id, kind=kind, target_id=target_id, status="queued")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

