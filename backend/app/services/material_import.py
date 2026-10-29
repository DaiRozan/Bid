import hashlib
from pathlib import Path, PurePosixPath
from uuid import uuid4

from sqlalchemy import select

from ..adapters.archives import open_archive
from ..config import get_settings
from ..models.document import SourceDocument
from ..models.material import MaterialRecord


def material_kind(name: str) -> str:
    lower = name.lower()
    if lower.endswith((".zip", ".rar")):
        return "archive"
    if lower.endswith((".dwg", ".dxf")):
        return "drawing"
    if "补疑" in name or "补遗" in name or "答疑" in name:
        return "supplement"
    if lower.endswith((".xls", ".xlsx")):
        return "drawing_index" if "图纸目录" in name else "boq"
    return "document"


def ensure_record(session, document, parent_id=None, archive_path=None):
    record = session.get(MaterialRecord, document.id)
    if record is None:
        record = MaterialRecord(document_id=document.id, parent_id=parent_id, archive_path=archive_path or document.filename, kind=material_kind(archive_path or document.filename))
        session.add(record)
        session.commit()
    return record


def import_materials(session, project_id, document, budget=None, depth=0):
    from .parsing import parse_document
    settings = get_settings()
    budget = budget if budget is not None else {"bytes": 0, "members": 0}
    if depth >= settings.max_archive_depth:
        raise ValueError("压缩包嵌套层数超过限额")
    record = ensure_record(session, document)
    with open_archive(Path(document.storage_path)) as (members, reader):
        budget["bytes"] += sum(size for _, size, _ in members)
        budget["members"] += len(members)
        if budget["bytes"] > settings.max_archive_bytes or budget["members"] > settings.max_archive_members:
            raise ValueError("压缩包解压总量或文件数量超过限额")
        for name, size, info in members:
            archive_path = record.archive_path + "!/" + name
            existing = session.scalar(select(SourceDocument).join(MaterialRecord, MaterialRecord.document_id == SourceDocument.id).where(MaterialRecord.parent_id == document.id, MaterialRecord.archive_path == archive_path))
            if existing is not None:
                child = existing
            else:
                suffix = PurePosixPath(name).suffix.lower()
                target = Path(document.storage_path).parent / (uuid4().hex + suffix)
                digest = hashlib.sha256()
                written = 0
                try:
                    with reader(info) as source, target.open("wb") as output:
                        while chunk := source.read(1024 * 1024):
                            written += len(chunk)
                            if written > size or written > settings.max_archive_bytes:
                                raise ValueError("压缩成员大小超出声明或限额")
                            digest.update(chunk)
                            output.write(chunk)
                    if written != size:
                        raise ValueError("压缩成员内容不完整")
                except Exception:
                    target.unlink(missing_ok=True)
                    raise
                child = SourceDocument(project_id=project_id, filename=PurePosixPath(name).name, media_type="application/octet-stream", extension=suffix, storage_path=str(target), sha256=digest.hexdigest(), size_bytes=written)
                session.add(child)
                session.commit()
                ensure_record(session, child, document.id, archive_path)
            if child.extension in {".zip", ".rar"}:
                import_materials(session, project_id, child, budget, depth + 1)
            elif child.status not in {"parsed", "analyzed"}:
                parse_document(session, child)
        document.status = "unpacked"
        document.error_message = None
        session.commit()
