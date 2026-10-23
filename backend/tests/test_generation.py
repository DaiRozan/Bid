from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_generation_uses_only_confirmed_facts_and_cited_knowledge(tmp_path: Path, monkeypatch):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    captured: dict = {}
    with TestClient(app) as client:
        project_id = client.post(
            "/api/projects", json={"code": "G-1", "name": "生成项目", "engineering_type": "building"}
        ).json()["id"]
        facts = client.post(
            f"/api/projects/{project_id}/facts/manual",
            json={"field_name": "工期", "raw_value": "120日历天", "confirmed_value": "120日历天"},
        ).json()
        client.post(
            f"/api/projects/{project_id}/facts/manual",
            json={"field_name": "未知数量", "raw_value": "", "confirmed_value": None},
        )
        chapter = client.post(
            f"/api/projects/{project_id}/chapters",
            json={"title": "进度计划", "outline_position": 1, "blocks": []},
        ).json()

        def fake_generate(*args, **kwargs):
            captured.update(kwargs)
            return {"blocks": [{"type": "paragraph", "text": "依据已确认工期编制"}], "citations": [], "open_issues": []}

        monkeypatch.setattr("app.services.generation.generate_chapter", fake_generate)
        response = client.post(f"/api/chapters/{chapter['id']}/generate")
        assert response.status_code == 200
    assert captured["facts"] == [{"field_name": "工期", "value": "120日历天"}]
    assert captured["facts"] != [{"field_name": "未知数量", "value": ""}]


def test_generation_failure_keeps_chapter_version_unchanged(tmp_path: Path, monkeypatch):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = client.post(
            "/api/projects", json={"code": "G-2", "name": "失败项目", "engineering_type": "building"}
        ).json()["id"]
        chapter = client.post(
            f"/api/projects/{project_id}/chapters",
            json={"title": "安全管理", "outline_position": 1, "blocks": [{"type": "paragraph", "text": "旧版本"}]},
        ).json()
        monkeypatch.setattr("app.services.generation.generate_chapter", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("真实模型失败")))
        response = client.post(f"/api/chapters/{chapter['id']}/generate")
        assert response.status_code == 502
        current = client.get(f"/api/projects/{project_id}/chapters").json()[0]
    assert len(current["versions"]) == 1
    assert current["versions"][0]["blocks"][0]["text"] == "旧版本"

