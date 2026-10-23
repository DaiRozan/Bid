from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_session_factory
from app.main import app
from app.models.project import Project


def test_project_create_and_list_persist_across_sessions(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"

    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={"code": "P-001", "name": "新建项目", "engineering_type": "municipal"},
        )
        assert created.status_code == 201
        payload = created.json()
        assert payload["target_pages"] == 50
        assert payload["facts_version"] == 1
        assert client.get("/api/projects").json()[0]["id"] == payload["id"]
        project_id = payload["id"]

    session = get_session_factory()()
    try:
        persisted = session.get(Project, project_id)
        assert persisted is not None
        assert persisted.name == "新建项目"
    finally:
        session.close()


def test_invalid_engineering_type_is_rejected(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        response = client.post(
            "/api/projects",
            json={"code": "P-002", "name": "项目", "engineering_type": "other"},
        )
    assert response.status_code == 422
