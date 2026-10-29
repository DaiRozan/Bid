from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from docx import Document
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def zip_bytes(files):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in files:
            archive.writestr(name, data)
    return buffer.getvalue()


def configured_client(tmp_path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    return TestClient(app)


def project(client):
    return client.post("/api/projects", json={"code": "ARCH", "name": "资料包测试", "engineering_type": "building"}).json()["id"]


def test_nested_zip_import_keeps_sources_and_deduplicates(tmp_path):
    doc = Document()
    doc.add_paragraph("项目名称：资料包测试")
    output = BytesIO()
    doc.save(output)
    data = zip_bytes([("正文.docx", output.getvalue()), ("发投标人资料.zip", zip_bytes([("说明/其他.txt", b"unsupported")]))])
    with configured_client(tmp_path) as client:
        pid = project(client)
        uploaded = client.post(f"/api/projects/{pid}/documents", files={"file": ("招标资料.zip", data)})
        assert uploaded.status_code == 201
        root_id = uploaded.json()["id"]
        parsed = client.post(f"/api/documents/{root_id}/parse")
        assert parsed.status_code == 200
        assert parsed.json()["status"] == "unpacked"
        documents = client.get(f"/api/projects/{pid}/documents").json()
        assert len(documents) == 4
        source = next(d for d in documents if d["filename"] == "正文.docx")
        assert source["blocks"][0]["text"] == "项目名称：资料包测试"
        assert source["archive_path"] == "招标资料.zip!/正文.docx"
        unsupported = next(d for d in documents if d["filename"] == "其他.txt")
        assert unsupported["status"] == "needs_review"
        assert "格式" in unsupported["error_message"]
        assert client.post(f"/api/documents/{root_id}/parse").status_code == 200
        assert len(client.get(f"/api/projects/{pid}/documents").json()) == 4
        again = client.post(f"/api/projects/{pid}/documents", files={"file": ("招标资料.zip", data)})
        assert again.json()["id"] == root_id


def test_archive_rejects_traversal_before_importing_any_member(tmp_path):
    data = zip_bytes([("normal.pdf", b"pdf"), ("../escaped.pdf", b"escape")])
    with configured_client(tmp_path) as client:
        pid = project(client)
        root = client.post(f"/api/projects/{pid}/documents", files={"file": ("bad.zip", data)})
        assert root.status_code == 201
        parsed = client.post(f"/api/documents/{root.json()['id']}/parse").json()
        assert parsed["status"] == "failed"
        assert "路径" in parsed["error_message"]
        assert len(client.get(f"/api/projects/{pid}/documents").json()) == 1
        assert not (tmp_path / "escaped.pdf").exists()


def test_archive_rejects_symlink_and_expansion_limit(tmp_path):
    entry = ZipInfo("linked.pdf")
    entry.create_system = 3
    entry.external_attr = 0o120777 << 16
    with configured_client(tmp_path) as client:
        pid = project(client)
        for data in [zip_bytes([(entry, b"target")]), zip_bytes([("large.pdf", b"x" * 100)])]:
            get_settings().max_archive_bytes = 50
            root = client.post(f"/api/projects/{pid}/documents", files={"file": ("bad.zip", data)})
            assert root.status_code == 201
            parsed = client.post(f"/api/documents/{root.json()['id']}/parse").json()
            assert parsed["status"] == "failed"
            assert any(word in parsed["error_message"] for word in ["链接", "限额"])


def test_archive_rejects_windows_absolute_path(tmp_path):
    from app.adapters.archives import validate_member_path
    import pytest
    for name in ["C:/outside.pdf", "\\\\server\\share\\a.pdf", "x/../../a.pdf", "/a.pdf"]:
        with pytest.raises(ValueError, match="路径"):
            validate_member_path(name)
