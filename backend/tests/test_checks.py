from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def setup(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"


def test_project_name_and_duration_mismatch_is_reported(tmp_path: Path):
    setup(tmp_path)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"code":"R-1","name":"甲项目","engineering_type":"building"}).json()
        client.post(f"/api/projects/{project['id']}/facts/manual", json={"field_name":"项目名称","confirmed_value":"乙项目"})
        response = client.post(f"/api/projects/{project['id']}/checks/run")
    assert response.status_code == 200
    assert any(item["code"] == "project_name_mismatch" for item in response.json()["issues"])


def test_requirement_mapping_does_not_mark_response_complete(tmp_path: Path):
    setup(tmp_path)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"code":"R-2","name":"项目","engineering_type":"building"}).json()
        created = client.post(f"/api/projects/{project['id']}/requirements/manual", json={"text":"必须说明安全措施"})
        assert created.status_code == 201
        response = client.post(f"/api/projects/{project['id']}/checks/run")
    assert any(item["code"] == "requirement_unmapped" for item in response.json()["issues"])


def test_missing_required_chapter_and_placeholder_are_reported(tmp_path: Path):
    setup(tmp_path)
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"code":"R-3","name":"项目","engineering_type":"building"}).json()
        chapter = client.post(f"/api/projects/{project['id']}/chapters", json={"title":"占位","outline_position":1,"blocks":[{"type":"paragraph","text":"{{待替换}}"}]}).json()
        response = client.post(f"/api/projects/{project['id']}/checks/run")
    codes = {item["code"] for item in response.json()["issues"]}
    assert "required_chapter_missing" in codes
    assert "placeholder_found" in codes

