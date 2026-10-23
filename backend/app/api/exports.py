from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.chapter import Chapter, ChapterVersion
from ..models.export import ExportRecord
from ..models.project import Project
from ..adapters.docx_export import export_docx

router = APIRouter(prefix="/api", tags=["exports"])


def export_payload(session: Session, project: Project, record: ExportRecord) -> dict:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "status": record.status,
        "page_count": record.page_count,
        "chapter_version_ids": record.chapter_version_ids,
        "created_at": record.created_at,
    }


@router.post("/projects/{project_id}/exports", status_code=201)
def create_export(project_id: str, session: Session = Depends(get_db)):
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    chapters = list(session.scalars(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.outline_position)))
    content: list[tuple[str, list[dict]]] = []
    version_ids: list[str] = []
    for chapter in chapters:
        version = session.scalar(select(ChapterVersion).where(ChapterVersion.chapter_id == chapter.id).order_by(ChapterVersion.version_number.desc()))
        if version:
            content.append((chapter.title, version.blocks))
            version_ids.append(version.id)
    path = get_settings().data_dir / "projects" / project_id / "exports" / f"review-{project_id}.docx"
    export_docx(path, project.name, content)
    record = ExportRecord(project_id=project_id, storage_path=str(path), chapter_version_ids=version_ids)
    session.add(record)
    session.commit()
    session.refresh(record)
    return export_payload(session, project, record)


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, session: Session = Depends(get_db)):
    record = session.get(ExportRecord, export_id)
    if record is None or not Path(record.storage_path).exists():
        raise HTTPException(status_code=404, detail="导出文件不存在")
    return FileResponse(record.storage_path, filename="技术标审核稿.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

