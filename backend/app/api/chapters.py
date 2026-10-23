from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.chapter import Chapter
from ..models.project import Project
from ..schemas.chapter import ChapterCreate, ChapterUpdate
from ..services.chapters import append_version, serialize_chapter
from ..services import generation as generation_service
from ..services.jobs import create_job

router = APIRouter(prefix="/api", tags=["chapters"])


@router.post("/projects/{project_id}/chapters", status_code=status.HTTP_201_CREATED)
def create_chapter(project_id: str, data: ChapterCreate, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    chapter = Chapter(project_id=project_id, title=data.title, outline_position=data.outline_position)
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    append_version(session, chapter, [block.model_dump() for block in data.blocks], "human")
    return serialize_chapter(session, chapter)


@router.get("/projects/{project_id}/chapters")
def list_chapters(project_id: str, session: Session = Depends(get_db)):
    chapters = session.scalars(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.outline_position))
    return [serialize_chapter(session, chapter) for chapter in chapters]


@router.put("/chapters/{chapter_id}")
def update_chapter(chapter_id: str, data: ChapterUpdate, session: Session = Depends(get_db)):
    chapter = session.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")
    append_version(session, chapter, [block.model_dump() for block in data.blocks], "human")
    chapter.stale = False
    session.commit()
    return serialize_chapter(session, chapter)


@router.post("/chapters/{chapter_id}/generate")
def generate(chapter_id: str, session: Session = Depends(get_db)):
    chapter = session.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")
    project = session.get(Project, chapter.project_id)
    job = create_job(session, project.id, "章节生成", chapter.id)
    job.status = "running"
    job.progress = 20
    session.commit()
    try:
        generated = generation_service.generate_chapter(session=session, project=project, chapter=chapter, facts=generation_service.confirmed_facts(session, project.id), knowledge=[])
        append_version(session, chapter, generated["blocks"], "model", generated.get("citations"), generated.get("open_issues"))
        chapter.stale = False
        job.status = "succeeded"
        job.progress = 100
        session.commit()
        return {"job": job.__dict__ | {"_sa_instance_state": None}, "chapter": serialize_chapter(session, chapter)}
    except Exception as exc:
        session.rollback()
        job = session.get(type(job), job.id)
        job.status = "failed"
        job.error_message = str(exc)
        session.commit()
        raise HTTPException(status_code=502, detail=f"章节生成失败：{exc}") from exc

