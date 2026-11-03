import asyncio
import httpx
import pytest
from pydantic import BaseModel

from app.adapters.deepseek import DeepSeekClient
from app.config import get_settings
from test_material_import import configured_client, project
from test_fact_library import add_fact, publish


def chapter(client, pid):
    return client.post(f"/api/projects/{pid}/chapters", json={"title": "施工部署", "blocks": []}).json()


def test_generation_requires_published_snapshot_before_calling_model(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client)
        add_fact(client, pid)
        ch = chapter(client, pid)
        monkeypatch.setattr("app.services.generation.generate_chapter", lambda **kw: {"blocks": [{"type": "paragraph", "text": "不应调用"}]})
        response = client.post(f"/api/chapters/{ch['id']}/generate")
        assert response.status_code == 409
        assert "发布" in response.json()["detail"]


def test_generation_uses_frozen_fact_value_and_rejects_unsupported_numbers(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client)
        fact = add_fact(client, pid)
        publish(client, pid)
        client.put(f"/api/projects/{pid}/facts/{fact['id']}", json={"confirmed_value": "150日历天"})
        ch = chapter(client, pid)
        def generate(**kwargs):
            assert kwargs["facts"][0]["value"] == "120日历天"
            return {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": fact["id"], "field": "value"}]}]}
        monkeypatch.setattr("app.services.generation.generate_chapter", generate)
        response = client.post(f"/api/chapters/{ch['id']}/generate")
        assert response.status_code == 200
        assert response.json()["chapter"]["versions"][-1]["blocks"][0]["text"] == "120日历天"
        monkeypatch.setattr("app.services.generation.generate_chapter", lambda **kw: {"blocks": [{"type": "paragraph", "text": "工期{{fact:" + fact["id"] + "}}，建筑面积999平方米。"}]})
        rejected = client.post(f"/api/chapters/{ch['id']}/generate")
        assert rejected.status_code == 502
        current = client.get(f"/api/projects/{pid}/chapters").json()[0]
        assert len(current["versions"]) == 2


def test_unknown_fact_and_retry_cannot_bypass_fact_library(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client)
        fact = add_fact(client, pid)
        publish(client, pid)
        ch = chapter(client, pid)
        monkeypatch.setattr("app.services.generation.generate_chapter", lambda **kw: {"blocks": [{"type": "paragraph", "text": "{{fact:foreign-project-fact}}"}]})
        assert client.post(f"/api/chapters/{ch['id']}/generate").status_code == 502
        from app.db import get_session_factory
        from app.models.job import Job
        from sqlalchemy import select
        with get_session_factory()() as session:
            job_id = session.scalar(select(Job.id).where(Job.project_id == pid))
        assert client.post(f"/api/jobs/{job_id}/retry").status_code == 502
        assert len(client.get(f"/api/projects/{pid}/chapters").json()[0]["versions"]) == 1


def test_deepseek_prompts_for_json_schema_when_callers_do_not_mention_json():
    class Answer(BaseModel):
        value: str
    def handler(request):
        import json
        body = json.loads(request.content)
        prompt = body["messages"][0]["content"]
        assert "json" in prompt.lower()
        assert "properties" in prompt and "value" in prompt
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"value":"ok"}'}}]})
    settings = get_settings().model_copy(update={"deepseek_api_key": "test-key"})
    result = asyncio.run(DeepSeekClient(settings, httpx.MockTransport(handler)).complete_json("提取事实", {}, Answer))
    assert result.value == "ok"
