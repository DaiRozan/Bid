from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_retry_does_not_duplicate_chapter_or_export(tmp_path: Path, monkeypatch):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = client.post(
            "/api/projects", json={"code": "J-1", "name": "任务项目", "engineering_type": "building"}
        ).json()["id"]
        fact = client.post(f"/api/projects/{project_id}/facts/manual", json={"field_name": "工期", "confirmed_value": "120日历天"}).json()
        client.post(f"/api/projects/{project_id}/fact-library/publish", json={"acknowledge_issues": True})
        chapter = client.post(
            f"/api/projects/{project_id}/chapters",
            json={"title": "质量管理", "outline_position": 1, "blocks": []},
        ).json()
        monkeypatch.setattr("app.services.generation.generate_chapter", lambda *args, **kwargs: {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": fact["id"], "field": "value"}]}]})
        first = client.post(f"/api/chapters/{chapter['id']}/generate").json()
        retried = client.post(f"/api/jobs/{first['job']['id']}/retry")
        chapters = client.get(f"/api/projects/{project_id}/chapters").json()
    assert retried.status_code == 200
    assert len(chapters) == 1
    assert len(chapters[0]["versions"]) == 3


def test_fact_change_marks_dependent_chapter_stale_without_overwrite(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = client.post(
            "/api/projects", json={"code": "J-2", "name": "复核项目", "engineering_type": "building"}
        ).json()["id"]
        fact = client.post(
            f"/api/projects/{project_id}/facts/manual",
            json={"field_name": "工期", "raw_value": "120日历天", "confirmed_value": "120日历天"},
        ).json()
        chapter = client.post(
            f"/api/projects/{project_id}/chapters",
            json={"title": "进度", "outline_position": 1, "blocks": [{"type": "paragraph", "text": "保留正文"}]},
        ).json()
        updated = client.put(
            f"/api/projects/{project_id}/facts/{fact['id']}",
            json={"confirmed_value": "150日历天"},
        )
        current = client.get(f"/api/projects/{project_id}/chapters").json()[0]
    assert updated.status_code == 200
    assert current["stale"] is True
    assert current["versions"][0]["blocks"][0]["text"] == "保留正文"
