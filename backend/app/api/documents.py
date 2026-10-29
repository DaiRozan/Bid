from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.document import SourceDocument
from ..models.parse_block import ParseBlock
from ..models.project import Project
from ..schemas.document import DocumentRead, ParseBlockRead
from ..services.file_storage import save_upload
from ..services.parsing import parse_document
from ..services.material_import import ensure_record
from ..models.material import MaterialRecord

router = APIRouter(prefix="/api", tags=["documents"])


def serialize_document(session: Session, document: SourceDocument) -> dict:
    blocks = list(session.scalars(select(ParseBlock).where(ParseBlock.document_id == document.id).order_by(ParseBlock.ordinal).limit(200)))
    result = DocumentRead.model_validate(document).model_dump()
    result["blocks"] = [ParseBlockRead.model_validate(block).model_dump() for block in blocks]
    result["block_count"] = session.scalar(select(func.count()).select_from(ParseBlock).where(ParseBlock.document_id == document.id))
    record = session.get(MaterialRecord, document.id)
    if record:
        result.update(archive_path=record.archive_path, parent_id=record.parent_id, kind=record.kind, analysis_summary=record.analysis.get("summary", {}))
    return result


@router.post("/projects/{project_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(project_id: str, file: UploadFile = File(...), session: Session = Depends(get_db)):
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        path, sha256, size = await save_upload(project_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    existing = session.scalar(select(SourceDocument).where(SourceDocument.project_id == project_id, SourceDocument.sha256 == sha256))
    if existing:
        path.unlink(missing_ok=True)
        return serialize_document(session, existing)
    document = SourceDocument(
        project_id=project_id,
        filename=file.filename or "未命名文件",
        media_type=file.content_type or "application/octet-stream",
        extension=Path(file.filename or "").suffix.lower(),
        storage_path=str(path),
        sha256=sha256,
        size_bytes=size,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    ensure_record(session, document)
    return serialize_document(session, document)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
def list_documents(project_id: str, session: Session = Depends(get_db)):
    documents = list(session.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id)))
    return [serialize_document(session, document) for document in documents]


@router.post("/documents/{document_id}/parse", response_model=DocumentRead)
def parse(document_id: str, session: Session = Depends(get_db)):
    document = session.get(SourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    parse_document(session, document)
    return serialize_document(session, document)

