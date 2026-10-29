import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from ..config import get_settings


def libreoffice_executable() -> str:
    candidates = [get_settings().libreoffice_path, shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise ValueError("读取 DOC 需要安装 LibreOffice 或配置 LIBREOFFICE_PATH")


def convert_doc(path: Path) -> Path:
    destination = path.parent / "converted" / path.stem
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / (path.stem + ".docx")
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix="technical-bid-lo-") as profile:
            completed = subprocess.run(
                [libreoffice_executable(), "-env:UserInstallation=" + Path(profile).as_uri(), "--headless", "--convert-to", "docx", "--outdir", str(destination), str(path.resolve())],
                capture_output=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if completed.returncode or not target.exists():
                raise ValueError("DOC 转换失败，请检查原文件是否受密码保护或损坏")
    return target
