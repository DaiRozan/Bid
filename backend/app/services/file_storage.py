import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from ..config import get_settings


ALLOWED_EXTENSIONS = {".docx", ".pdf"}


async def save_upload(project_id: str, upload: UploadFile) -> tuple[Path, str, int]:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 DOCX 和 PDF 文件")
    data = await upload.read()
    if len(data) > get_settings().max_upload_bytes:
        raise OverflowError("文件超过允许的大小限制")
    target_dir = get_settings().data_dir / "projects" / project_id / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{suffix}"
    target.write_bytes(data)
    return target, hashlib.sha256(data).hexdigest(), len(data)

