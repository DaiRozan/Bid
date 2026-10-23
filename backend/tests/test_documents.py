from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.config import get_settings
from app.main import app


def setup_project(tmp_path: Path, client: TestClient) -> str:
    response = client.post(
        "/api/projects",
        json={"code": f"P-{tmp_path.name}", "name": "资料测试项目", "engineering_type": "building"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def make_docx() -> bytes:
    doc = Document()
    doc.add_paragraph("项目名称：测试工程")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "工期"
    table.cell(0, 1).text = "120日历天"
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_docx_preserves_paragraph_table_order_and_locations(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = setup_project(tmp_path, client)
        upload = client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("tender.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload.status_code == 201
        parsed = client.post(f"/api/documents/{upload.json()['id']}/parse")
        assert parsed.status_code == 200
        blocks = parsed.json()["blocks"]
        assert blocks[0]["location"] == {"kind": "paragraph", "index": 0}
        assert blocks[1]["location"] == {"kind": "table", "index": 0, "row": 0, "column": 0}


def test_pdf_blocks_keep_page_number(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = setup_project(tmp_path, client)
        upload = client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("tender.pdf", make_blank_pdf(), "application/pdf")},
        )
        assert upload.status_code == 201
        parsed = client.post(f"/api/documents/{upload.json()['id']}/parse")
        assert parsed.status_code == 200
        assert parsed.json()["status"] == "needs_review"


def test_unsupported_extension_is_rejected(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = setup_project(tmp_path, client)
        response = client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("tender.txt", b"not supported", "text/plain")},
        )
    assert response.status_code == 415


def test_file_over_configured_limit_is_rejected(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = setup_project(tmp_path, client)
        settings.max_upload_bytes = 4
        response = client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("tender.docx", b"12345", "application/octet-stream")},
        )
    assert response.status_code == 413


def test_scanned_pdf_keeps_source_and_needs_review(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = setup_project(tmp_path, client)
        content = make_blank_pdf()
        upload = client.post(
            f"/api/projects/{project_id}/documents",
            files={"file": ("scan.pdf", content, "application/pdf")},
        )
        parsed = client.post(f"/api/documents/{upload.json()['id']}/parse")
        assert parsed.json()["status"] == "needs_review"
        stored = Path(get_settings().data_dir) / "projects" / project_id / "uploads"
        assert list(stored.glob("*"))
