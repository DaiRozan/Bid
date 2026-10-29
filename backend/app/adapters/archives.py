"""Read archive members without ever using member names as disk paths."""
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat
import os
import subprocess
import tempfile
from zipfile import ZipFile

import rarfile


@contextmanager
def read_rar_member(path, info):
    # rarfile's temporary single-member optimization corrupts this real RAR5
    # archive for bsdtar. Read the original archive directly, with bounded
    # streaming supplied by material_import and without filesystem extraction.
    executable = shutil.which("bsdtar") or shutil.which("tar")
    if not executable:
        raise ValueError("读取 RAR 需要本机 tar/bsdtar")
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([executable, "-xOf", str(path), "--", info.filename], stdout=subprocess.PIPE, stderr=errors, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            yield process.stdout
            process.stdout.close()
            if process.wait(timeout=30):
                raise ValueError("RAR 成员读取失败")
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def validate_member_path(name: str) -> str:
    name = name.replace("\\", "/")
    path = PurePosixPath(name)
    if not name or "\x00" in name or path.is_absolute() or PureWindowsPath(name).drive or ".." in path.parts or ":" in name:
        raise ValueError("压缩包包含不安全的成员路径")
    return name.rstrip("/")


def decoded_zip_name(info) -> str:
    if not info.flag_bits & 0x800:
        try:
            return info.filename.encode("cp437").decode("gb18030")
        except (UnicodeError, LookupError):
            pass
    return info.filename


@contextmanager
def open_archive(path: Path):
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            members = []
            for info in archive.infolist():
                name = validate_member_path(decoded_zip_name(info))
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("压缩包包含符号链接")
                if info.flag_bits & 1:
                    raise ValueError("暂不支持加密压缩包")
                if not info.is_dir():
                    members.append((name, info.file_size, info))
            yield members, archive.open
    else:
        rarfile.BSDTAR_TOOL = shutil.which("bsdtar") or shutil.which("tar") or "bsdtar"
        with rarfile.RarFile(path) as archive:
            members = []
            for info in archive.infolist():
                name = validate_member_path(info.filename)
                if info.is_symlink() or getattr(info, "file_redir", None):
                    raise ValueError("压缩包包含链接")
                if info.needs_password():
                    raise ValueError("暂不支持加密压缩包")
                if info.is_file():
                    members.append((name, info.file_size, info))
            yield members, lambda info: read_rar_member(path, info)
