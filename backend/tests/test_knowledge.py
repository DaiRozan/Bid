from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_imported_standard_defaults_to_pending_verification(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        response = client.post(
            "/api/knowledge",
            json={
                "kind": "standard",
                "title": "施工组织设计规范",
                "body": "条文内容",
                "source": "用户导入",
                "standard_number": "GB/T-TEST",
            },
        )
        assert response.status_code == 201
        assert response.json()["verification_status"] == "待核验"


def test_cross_project_knowledge_is_not_returned_as_project_facts(tmp_path: Path):
    get_settings.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    settings.data_dir = tmp_path / "data"
    with TestClient(app) as client:
        first = client.post(
            "/api/knowledge",
            json={"kind": "case", "title": "外部项目", "body": "工期=999", "source": "其他项目"},
        )
        assert first.status_code == 201
        projects = [
            client.post(
                "/api/projects", json={"code": f"K-{i}", "name": f"项目{i}", "engineering_type": "building"}
            ).json()["id"]
            for i in range(2)
        ]
        facts = client.get(f"/api/projects/{projects[1]}/facts").json()
    assert facts == []
