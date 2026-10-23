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
        blocks = extract_docx(str(path)) if document.extension == ".docx" else extract_pdf(str(path))
        session.execute(delete(ParseBlock).where(ParseBlock.document_id == document.id))
        for ordinal, (text, location) in enumerate(blocks):
            session.add(ParseBlock(document_id=document.id, ordinal=ordinal, text=text, location=location))
        document.status = "parsed" if blocks else "needs_review"
        document.error_message = None if blocks else "未提取到文字，可能是扫描件或图片型文件"
    except Exception as exc:
        document.status = "failed"
        document.error_message = f"解析失败：{exc}"
    session.commit()
    session.refresh(document)
    return document

