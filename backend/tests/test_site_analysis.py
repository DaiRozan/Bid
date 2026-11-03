from io import BytesIO
import ezdxf
import pytest
import asyncio
import httpx
from pydantic import BaseModel
from app.adapters.deepseek import DeepSeekClient
from app.config import get_settings
from test_material_import import configured_client, project


def test_site_report_can_request_sufficient_structured_output_budget():
    class Answer(BaseModel):
        summary: str
    def handler(request):
        import json
        assert json.loads(request.content)['max_tokens'] == 8192
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"summary":"ok"}'}}]})
    settings=get_settings().model_copy(update={'deepseek_api_key':'test'})
    client=DeepSeekClient(settings,httpx.MockTransport(handler),max_tokens=8192)
    assert asyncio.run(client.complete_json('JSON',{},Answer)).summary == 'ok'


def drawing(client, pid, tmp_path):
    doc = ezdxf.new(); doc.units = 6
    doc.modelspace().add_text("现状水泥路", dxfattribs={"insert": (10, 20)})
    doc.modelspace().add_text("水塘", dxfattribs={"insert": (30, 20)})
    doc.modelspace().add_lwpolyline([(0, 0), (40, 0), (40, 40), (0, 40)], close=True)
    path = tmp_path / "总平面.dxf"; doc.saveas(path)
    item = client.post(f"/api/projects/{pid}/documents", files={"file": (path.name, path.read_bytes())}).json()
    client.post(f"/api/documents/{item['id']}/parse")
    return item


def test_site_analysis_is_evidenced_saved_and_requires_adoption_for_writing(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client); drawing(client, pid, tmp_path)
        async def complete(self, system, payload, schema):
            assert payload["drawings"][0]["geometry"][0]["points"]
            evidence = next(e for e in payload["evidence"] if "水塘" in e["text"])
            return schema(summary="临水施工及运输需重点核实", findings=[{"title":"临水作业", "observation":"图纸标注水塘", "impact":"塘边作业面及临时堆土需核实", "recommendation":"踏勘水位及边界，确定防护与运输路线", "uncertainty":"水位和岸坡稳定性尚未核实", "source_block_ids":[evidence["id"]]}, {"title":"补充占位", "observation":"占位", "impact":"占位", "recommendation":"占位", "uncertainty":"占位", "source_block_ids":[evidence["id"]]}], limitations=["图纸不代表实时现场"])
        monkeypatch.setattr("app.adapters.deepseek.DeepSeekClient.complete_json", complete)
        response = client.post(f"/api/projects/{pid}/site-analysis")
        assert response.status_code == 200
        report = response.json()
        assert len(report['findings']) == 1
        assert client.get(f"/api/projects/{pid}/site-analysis").json()["id"] == report["id"]
        draft = client.get(f"/api/projects/{pid}/fact-library?section=review").json()
        assert not draft["facts"]
        entry = next(e for e in draft["review"] if e["record_type"] == "site_analysis")
        assert entry["source_block_ids"]
        assert "现场条件与施工影响.md" in draft["files"]
        assert client.post(f"/api/projects/{pid}/site-analysis/adopt", json={"analysis_id":report["id"]}).status_code == 200
        snapshot = client.post(f"/api/projects/{pid}/fact-library/publish", json={"acknowledge_issues":True}).json()
        assert snapshot["site_analysis"]["id"] == report["id"]
        assert snapshot["facts"][0]["source_type"] == "site_analysis"
        assert "分析判断" in snapshot["facts"][0]["value"]


def test_site_analysis_rejects_foreign_evidence_without_replacing_existing_result(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client); drawing(client, pid, tmp_path)
        async def complete(self, system, payload, schema):
            return schema(summary="错误", findings=[{"title":"假数据", "observation":"未知", "impact":"未知", "recommendation":"未知", "uncertainty":"未知", "source_block_ids":["foreign"]}], limitations=[])
        monkeypatch.setattr("app.adapters.deepseek.DeepSeekClient.complete_json", complete)
        assert client.post(f"/api/projects/{pid}/site-analysis").status_code == 502
        assert client.get(f"/api/projects/{pid}/site-analysis").status_code == 404


def test_new_analysis_preserves_adopted_history_until_explicit_replacement(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client); drawing(client, pid, tmp_path)
        async def complete(self, system, payload, schema):
            return schema(summary="复核", findings=[{"title":"临水", "observation":"水塘标注", "impact":"作业条件待核实", "recommendation":"踏勘", "uncertainty":"水位未知", "source_block_ids":[payload['evidence'][0]['id']]}], limitations=[])
        monkeypatch.setattr("app.adapters.deepseek.DeepSeekClient.complete_json", complete)
        old = client.post(f"/api/projects/{pid}/site-analysis").json()
        client.post(f"/api/projects/{pid}/site-analysis/adopt", json={"analysis_id":old["id"]})
        new = client.post(f"/api/projects/{pid}/site-analysis").json()
        draft = client.get(f"/api/projects/{pid}/fact-library").json()
        assert draft['facts'][0]['analysis_id'] == old['id']
        assert client.post(f"/api/projects/{pid}/site-analysis/adopt", json={"analysis_id":old["id"]}).status_code == 409
        client.post(f"/api/projects/{pid}/site-analysis/adopt", json={"analysis_id":new["id"]})
        draft = client.get(f"/api/projects/{pid}/fact-library").json()
        assert len(draft['facts']) == 1
        assert draft['facts'][0]['analysis_id'] == new['id']
        client.post(f"/api/projects/{pid}/site-analysis")
        draft = client.get(f"/api/projects/{pid}/fact-library").json()
        assert len(draft['facts']) == 1 and draft['facts'][0]['analysis_id'] == new['id']
        # A new source invalidates current analysis; stale reports cannot be adopted.
        client.post(f"/api/projects/{pid}/documents", files={'file':('补疑.pdf',b'new source')})
        assert client.get(f"/api/projects/{pid}/site-analysis").json()['stale']
        assert client.post(f"/api/projects/{pid}/site-analysis/adopt", json={"analysis_id":new["id"]}).status_code == 409
