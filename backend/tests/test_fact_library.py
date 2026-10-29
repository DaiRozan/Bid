from pathlib import Path

from test_material_import import configured_client, project, zip_bytes


def add_fact(client, pid, value="120日历天"):
    return client.post(f"/api/projects/{pid}/facts/manual", json={"field_name": "工期", "confirmed_value": value}).json()


def publish(client, pid):
    return client.post(f"/api/projects/{pid}/fact-library/publish", json={"acknowledge_issues": True})


def test_snapshot_freezes_markdown_and_adopted_values_until_new_publication(tmp_path):
    with configured_client(tmp_path) as client:
        pid = project(client)
        fact = add_fact(client, pid)
        first = publish(client, pid)
        assert first.status_code == 201
        assert first.json()["version"] == 1
        current = client.get(f"/api/projects/{pid}/fact-library/current").json()
        assert current["facts"][0]["value"] == "120日历天"
        path = Path(current["directory"]) / "采用事实.md"
        content = path.read_text(encoding="utf-8")
        assert "120日历天" in content
        client.put(f"/api/projects/{pid}/facts/{fact['id']}", json={"confirmed_value": "150日历天"})
        assert client.get(f"/api/projects/{pid}/fact-library/current").json()["facts"][0]["value"] == "120日历天"
        assert path.read_text(encoding="utf-8") == content
        assert publish(client, pid).json()["version"] == 2
        assert client.get(f"/api/projects/{pid}/fact-library/current").json()["facts"][0]["value"] == "150日历天"


def test_snapshot_tampering_and_empty_publication_are_rejected(tmp_path):
    with configured_client(tmp_path) as client:
        pid = project(client)
        assert publish(client, pid).status_code == 422
        add_fact(client, pid)
        assert publish(client, pid).status_code == 201
        current = client.get(f"/api/projects/{pid}/fact-library/current").json()
        (Path(current["directory"]) / "采用事实.md").write_text("被改写", encoding="utf-8")
        result = client.get(f"/api/projects/{pid}/fact-library/current")
        assert result.status_code == 409
        assert "校验" in result.json()["detail"]


def test_adoption_requires_project_scoped_evidence_and_retains_override_chain(tmp_path):
    from io import BytesIO
    from docx import Document
    with configured_client(tmp_path) as client:
        pid = project(client)
        original = add_fact(client, pid)
        other = client.post("/api/projects", json={"code": "OTHER", "name": "另一项目", "engineering_type": "building"}).json()["id"]
        def document_block(target_pid):
            source = Document()
            source.add_paragraph("补疑明确：计划工期调整为150日历天")
            output = BytesIO(); source.save(output)
            uploaded = client.post(f"/api/projects/{target_pid}/documents", files={"file": ("补疑.docx", output.getvalue())}).json()
            return client.post(f"/api/documents/{uploaded['id']}/parse").json()["blocks"][0]["id"]
        foreign_block = document_block(other)
        body = {"target_id": original["id"], "value": "150日历天", "reason": "采用最新明确补疑", "source_block_ids": [foreign_block]}
        assert client.post(f"/api/projects/{pid}/fact-library/adoptions", json=body).status_code == 422
        local_block = document_block(pid)
        body["source_block_ids"] = [local_block]
        assert client.post(f"/api/projects/{pid}/fact-library/adoptions", json=body).status_code == 201
        assert publish(client, pid).status_code == 201
        current = client.get(f"/api/projects/{pid}/fact-library/current").json()
        fact = next(f for f in current["facts"] if f["id"] == original["id"])
        assert fact["value"] == "150日历天"
        assert fact["overrides"][0]["previous_value"] == "120日历天"
        assert fact["source_block_ids"] == [local_block]


def test_reextraction_never_deletes_confirmed_facts_or_manual_requirements(tmp_path, monkeypatch):
    with configured_client(tmp_path) as client:
        pid = project(client)
        fact = add_fact(client, pid)
        client.post(f"/api/projects/{pid}/requirements/manual", json={"text": "保留人工要求"})
        monkeypatch.setattr("app.api.extraction.run_extraction", lambda *a, **kw: {"facts": [], "requirements": []})
        assert client.post(f"/api/projects/{pid}/extract").status_code == 200
        assert client.get(f"/api/projects/{pid}/facts").json()[0]["id"] == fact["id"]
        assert client.get(f"/api/projects/{pid}/requirements").json()[0]["text"] == "保留人工要求"


def test_latest_dated_explicit_supplement_overrides_boq_with_source_chain(tmp_path):
    from io import BytesIO
    from openpyxl import Workbook
    from docx import Document
    with configured_client(tmp_path) as client:
        pid = project(client)
        book = Workbook(); sheet = book.active
        sheet.append(["工程名称：1号楼"])
        sheet.append(["项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"])
        sheet.append(["010101001001", "平整场地", "三类土", "m2", 6])
        buffer = BytesIO(); book.save(buffer)
        def upload(name, data):
            uploaded = client.post(f"/api/projects/{pid}/documents", files={"file": (name, data)}).json()
            assert client.post(f"/api/documents/{uploaded['id']}/parse").json()["status"] in {"parsed", "analyzed"}
        upload("清单.xlsx", buffer.getvalue())
        for day, number in [(12, 9), (10, 8)]:  # Intentionally import newest first.
            doc = Document()
            doc.add_paragraph(f"发布日期：2026年10月{day}日")
            doc.add_paragraph(f"项目编码010101001001的工程量由6 m2调整为{number} m2。")
            buffer = BytesIO(); doc.save(buffer)
            upload(f"补疑{day}.docx", buffer.getvalue())
        current = publish(client, pid).json()
        fact = next(f for f in current["facts"] if f["source_type"] == "boq")
        assert fact["attributes"]["quantity"] == "9"
        assert "工程量：9 m2" in fact["value"]
        assert len(fact["overrides"]) == 2
        assert fact["overrides"][-1]["date"] == "2026-10-12"
