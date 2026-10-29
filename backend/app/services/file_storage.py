import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from ..config import get_settings


ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".zip", ".rar", ".xls", ".xlsx", ".dwg", ".dxf"}


async def save_upload(project_id: str, upload: UploadFile) -> tuple[Path, str, int]:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("支持 ZIP/RAR、DOC/DOCX/PDF、XLS/XLSX 和 DWG/DXF 文件")
    target_dir = get_settings().data_dir / "projects" / project_id / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{suffix}"
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > get_settings().max_upload_bytes:
                    raise OverflowError("文件超过允许的大小限制")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target, digest.hexdigest(), size

