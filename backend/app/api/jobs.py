from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.job import Job
from ..models.chapter import Chapter
from ..models.project import Project
from ..services import generation as generation_service
from ..services.chapters import append_version, serialize_chapter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str, session: Session = Depends(get_db)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job.__dict__ | {"_sa_instance_state": None}


@router.post("/{job_id}/retry")
def retry_job(job_id: str, session: Session = Depends(get_db)):
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    chapter = session.get(Chapter, job.target_id) if job.target_id else None
    if chapter is None:
        raise HTTPException(status_code=422, detail="该任务不支持重试")
    project = session.get(Project, chapter.project_id)
    job.status = "running"
    job.progress = 20
    session.commit()
    try:
        generated = generation_service.run_generation(session, project, chapter)
        append_version(session, chapter, generated["blocks"], "model", generated.get("citations"), generated.get("open_issues"), generated["facts_version"])
        chapter.stale = project.facts_version != generated["facts_version"]
        job.status = "succeeded"
        job.progress = 100
        session.commit()
        return {"job": job.__dict__ | {"_sa_instance_state": None}, "chapter": serialize_chapter(session, chapter)}
    except Exception as exc:
        session.rollback()
        job = session.get(Job, job_id)
        job.status = "failed"
        job.error_message = str(exc)
        session.commit()
        raise HTTPException(status_code=502, detail=f"重试失败：{exc}") from exc

