from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_real_workflow_project_to_docx(tmp_path: Path, monkeypatch):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'workflow.sqlite'}"
    settings.data_dir = tmp_path / "data"

    source = Document()
    source.add_paragraph("项目名称：示例建筑工程")
    source.add_paragraph("计划工期：120日历天")
    source_buffer = BytesIO()
    source.save(source_buffer)

    with TestClient(app) as client:
        project = client.post("/api/projects", json={"code": "WF-1", "name": "示例建筑工程", "engineering_type": "building"}).json()
        uploaded = client.post(
            f"/api/projects/{project['id']}/documents",
            files={"file": ("招标文件.docx", source_buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert uploaded.status_code == 201
        parsed = client.post(f"/api/documents/{uploaded.json()['id']}/parse")
        assert parsed.status_code == 200
        block_id = parsed.json()["blocks"][0]["id"]
        assert parsed.json()["blocks"][0]["location"] == {"kind": "paragraph", "index": 0}

        monkeypatch.setattr(
            "app.api.extraction.run_extraction",
            lambda *args, **kwargs: {"facts": [{"field_name": "工期", "raw_value": "120日历天", "source_block_ids": [block_id]}], "requirements": []},
        )
        extracted = client.post(f"/api/projects/{project['id']}/extract")
        assert extracted.status_code == 200
        fact = client.get(f"/api/projects/{project['id']}/facts").json()[0]
        confirmed = client.put(f"/api/projects/{project['id']}/facts/{fact['id']}", json={"confirmed_value": "120日历天"})
        assert confirmed.status_code == 200
        assert client.post(f"/api/projects/{project['id']}/fact-library/publish", json={"acknowledge_issues": True}).status_code == 201

        outline = client.put(
            f"/api/projects/{project['id']}/outline",
            json={"items": [{"title": "施工总体部署", "body": "", "required": True, "budget_pages": 2}]},
        )
        assert outline.status_code == 200
        chapter = client.post(
            f"/api/projects/{project['id']}/chapters",
            json={"title": "施工总体部署", "outline_position": 1, "blocks": []},
        ).json()
        monkeypatch.setattr(
            "app.api.chapters.generation_service.generate_chapter",
            lambda **kwargs: {"blocks": [{"type": "paragraph", "text": "根据{{fact:" + fact["id"] + "}}编制施工部署。"}], "citations": [], "open_issues": []},
        )
        generated = client.post(f"/api/chapters/{chapter['id']}/generate")
        assert generated.status_code == 200
        assert generated.json()["chapter"]["versions"][-1]["source"] == "model"
        checks = client.post(f"/api/projects/{project['id']}/checks/run")
        assert checks.status_code == 200
        assert checks.json()["status"] == "passed"

        exported = client.post(f"/api/projects/{project['id']}/exports")
        assert exported.status_code == 201
        download = client.get(f"/api/exports/{exported.json()['id']}/download")
        assert download.status_code == 200

    document = Document(BytesIO(download.content))
    assert "施工总体部署" in [paragraph.text for paragraph in document.paragraphs]
    assert "根据120日历天编制施工部署。" in [paragraph.text for paragraph in document.paragraphs]
