from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..adapters.docx_parser import extract_docx
from ..adapters.pdf_parser import extract_pdf
from ..models.document import SourceDocument
from ..models.parse_block import ParseBlock


def parse_document(session: Session, document: SourceDocument) -> SourceDocument:
    document.status = "parsing"
    session.commit()
    try:
        path = Path(document.storage_path)
        if document.extension in {".zip", ".rar"}:
            from .material_import import import_materials
            import_materials(session, document.project_id, document)
            return document
        if document.extension in {".xls", ".xlsx", ".dwg", ".dxf"}:
            from .material_analysis import analyze_material
            analyze_material(session, document)
            return document
        if document.extension == ".doc":
            from ..adapters.legacy_doc import convert_doc
            path = convert_doc(path)
        if document.extension not in {".doc", ".docx", ".pdf"}:
            document.status = "needs_review"
            document.error_message = "暂不支持此文件格式，原文件已保留"
            session.commit()
            return document
        blocks = extract_docx(str(path)) if document.extension in {".docx", ".doc"} else extract_pdf(str(path))
        sync_blocks(session, document.id, blocks)
        document.status = "parsed" if blocks else "needs_review"
        document.error_message = None if blocks else "未提取到文字，可能是扫描件或图片型文件"
    except Exception as exc:
        document.status = "failed"
        document.error_message = f"解析失败：{exc}"
    session.commit()
    session.refresh(document)
    return document


def sync_blocks(session, document_id, blocks):
    from sqlalchemy import select
    existing = list(session.scalars(select(ParseBlock).where(ParseBlock.document_id == document_id).order_by(ParseBlock.ordinal)))
    for ordinal, (text, location) in enumerate(blocks):
        if ordinal < len(existing):
            item = existing[ordinal]
            item.text, item.location = text, location
        else:
            session.add(ParseBlock(document_id=document_id, ordinal=ordinal, text=text, location=location))
    for extra in existing[len(blocks):]:
        session.delete(extra)

