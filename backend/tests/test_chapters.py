from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def project(tmp_path: Path, client: TestClient, kind: str = "building") -> str:
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    return client.post(
        "/api/projects", json={"code": f"C-{kind}", "name": "章节项目", "engineering_type": kind}
    ).json()["id"]


def test_building_and_municipal_starter_templates_are_distinct(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        building = client.post(
            "/api/projects", json={"code": "B-1", "name": "建筑", "engineering_type": "building"}
        ).json()["id"]
        municipal = client.post(
            "/api/projects", json={"code": "M-1", "name": "市政", "engineering_type": "municipal"}
        ).json()["id"]
        first = client.get(f"/api/projects/{building}/outline").json()
        second = client.get(f"/api/projects/{municipal}/outline").json()
    assert first["engineering_type"] == "building"
    assert second["engineering_type"] == "municipal"
    assert first["items"] != second["items"]
    assert all(item["body"] == "" for item in [*first["items"], *second["items"]])


def test_outline_edits_persist(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = project(tmp_path, client)
        response = client.put(
            f"/api/projects/{project_id}/outline",
            json={"items": [{"title": "一、项目概况", "body": "", "required": True, "budget_pages": 2}]},
        )
        assert response.status_code == 200
        saved = client.get(f"/api/projects/{project_id}/outline")
    assert saved.json()["items"][0]["title"] == "一、项目概况"


def test_human_edit_appends_chapter_version(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        project_id = project(tmp_path, client)
        created = client.post(
            f"/api/projects/{project_id}/chapters",
            json={"title": "施工部署", "outline_position": 1, "blocks": [{"type": "paragraph", "text": "人工编辑"}]},
        )
        assert created.status_code == 201
        chapter_id = created.json()["id"]
        saved = client.put(
            f"/api/chapters/{chapter_id}",
            json={"blocks": [{"type": "paragraph", "text": "人工编辑后的正文"}]},
        )
        assert saved.status_code == 200
        versions = client.get(f"/api/projects/{project_id}/chapters").json()[0]["versions"]
    assert len(versions) == 2
    assert versions[-1]["source"] == "human"

