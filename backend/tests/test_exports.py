from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_docx_contains_editable_paragraph_and_table_blocks(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"code":"E-1","name":"导出项目","engineering_type":"building"}).json()
        chapter = client.post(f"/api/projects/{project['id']}/chapters", json={"title":"施工部署","outline_position":1,"blocks":[{"type":"paragraph","text":"可编辑段落"},{"type":"table","rows":[["列1","列2"],["值1","值2"]]}]}).json()
        exported = client.post(f"/api/projects/{project['id']}/exports")
        assert exported.status_code == 201
        export_id = exported.json()["id"]
        download = client.get(f"/api/exports/{export_id}/download")
    path = tmp_path / "out.docx"
    path.write_bytes(download.content)
    doc = Document(path)
    assert "可编辑段落" in [p.text for p in doc.paragraphs]
    assert doc.tables[0].cell(0, 0).text == "列1"
    assert exported.json()["status"] == "审核稿"
    assert exported.json()["page_count"] == "未验证"
