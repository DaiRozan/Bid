from io import BytesIO
import json
import math
import re

from docx import Document
import ezdxf
from openpyxl import Workbook
import pytest

from test_material_import import configured_client, project, zip_bytes
from test_fact_library import add_fact, publish


def boq_bytes():
    book = Workbook(); sheet = book.active
    sheet.append(["工程名称：A楼"])
    sheet.append(["项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"])
    sheet.append(["010101001001", "平整场地", "三类土", "m2", 6])
    output = BytesIO(); book.save(output)
    return output.getvalue()


def upload(client, pid, name, data):
    result = client.post(f"/api/projects/{pid}/documents", files={"file": (name, data)})
    assert result.status_code == 201
    parsed = client.post(f"/api/documents/{result.json()['id']}/parse")
    assert parsed.status_code == 200
    return parsed.json()


@pytest.mark.parametrize("clause,dated,expected", [
    ("工程量不应调整为9 m2，仍按6 m2执行", True, "6"),
    ("工程量调整为1,200 m2", True, "1200"),
    ("工程量调整为9 m2", False, "6"),
    ("工程量调整为1e3 m2", True, "6"),
    ("工程量是否调整为9 m2", True, "6"),
])
def test_supplement_only_adopts_complete_affirmative_dated_quantities(tmp_path, clause, dated, expected):
    with configured_client(tmp_path) as client:
        pid = project(client)
        upload(client, pid, "清单.xlsx", boq_bytes())
        doc = Document()
        if dated: doc.add_paragraph("发布日期：2026年10月12日")
        doc.add_paragraph("项目编码010101001001的" + clause + "。")
        output = BytesIO(); doc.save(output)
        upload(client, pid, "补疑.docx", output.getvalue())
        result = publish(client, pid).json()
        assert result["facts"][0]["attributes"]["quantity"] == expected
        if expected == "6":
            assert any("未自动" in item["message"] for item in result["issues"])


def test_boq_scope_changes_and_feature_continuations_retain_all_rows(tmp_path):
    from app.adapters.boq import analyze_boq
    book = Workbook(); sheet = book.active
    for row in [["工程名称：A楼"], ["项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"],
                ["010101001001", "平整场地", "首行特征", "m2", 6],
                [None, None, "续行特征"], ["工程名称：B楼"],
                ["项目名称", "工程量", "项目编码", "计量单位", "项目特征描述"],
                ["挖土方", 8, "010101002001", "m3", "另一单位工程"]]:
        sheet.append(row)
    path = tmp_path / "分页.xlsx"; book.save(path)
    items = analyze_boq(path)["items"]
    assert len(items) == 2
    assert items[0]["features"] == "首行特征\n续行特征"
    assert items[0]["location"]["continuation_rows"] == [4]
    assert items[1]["unit_project"] == "B楼"
    assert items[1]["name"] == "挖土方"


def test_duplicate_archive_workbooks_have_one_fact_and_all_occurrences(tmp_path):
    data = boq_bytes()
    archive = zip_bytes([("A/清单.xlsx", data), ("B/清单.xlsx", data)])
    with configured_client(tmp_path) as client:
        pid = project(client)
        upload(client, pid, "资料.zip", archive)
        snapshot = publish(client, pid).json()
        assert len(snapshot["facts"]) == 1
        document = next(d for d in snapshot["documents"] if d["filename"] == "清单.xlsx")
        assert set(document["origin_paths"]) == {"资料.zip!/A/清单.xlsx", "资料.zip!/B/清单.xlsx"}


def test_manual_override_preserves_original_evidence_and_consistent_adopted_quantity(tmp_path):
    with configured_client(tmp_path) as client:
        pid = project(client)
        upload(client, pid, "清单.xlsx", boq_bytes())
        original = client.get(f"/api/projects/{pid}/fact-library").json()["facts"][0]
        source = Document(); source.add_paragraph("补疑明确该项目工程量采用8 m2")
        output = BytesIO(); source.save(output)
        evidence = upload(client, pid, "补疑.docx", output.getvalue())["blocks"][0]["id"]
        body = {"target_id": original["id"], "value": "8 m2", "reason": "人工核对补疑", "source_block_ids": [evidence]}
        assert client.post(f"/api/projects/{pid}/fact-library/adoptions", json=body).status_code == 201
        adopted = publish(client, pid).json()["facts"][0]
        assert adopted["attributes"]["quantity"] == "8"
        assert "A楼" in adopted["value"] and "平整场地" in adopted["value"] and "工程量：8 m2" in adopted["value"]
        assert adopted["original_attributes"]["quantity"] == "6"
        assert adopted["original_source_block_ids"] == original["source_block_ids"]
        assert adopted["overrides"][-1]["previous_source_block_ids"] == original["source_block_ids"]


def test_multi_insert_array_expands_counts_geometry_and_cell_provenance(tmp_path):
    from app.adapters.cad import analyze_cad
    doc = ezdxf.new(); doc.units = 6
    block = doc.blocks.new("柱符号"); block.add_circle((0, 0), 1)
    doc.modelspace().add_blockref("柱符号", (0, 0), dxfattribs={"row_count": 2, "column_count": 3, "row_spacing": 5, "column_spacing": 5})
    path = tmp_path / "array.dxf"; doc.saveas(path)
    data = analyze_cad(path)
    count = next(m for m in data["measurements"] if m["type"] == "count")
    areas = [m for m in data["measurements"] if m["type"] == "area"]
    assert count["value"] == 6
    assert sum(a["value"] for a in areas) == pytest.approx(6 * math.pi)
    assert len({tuple(m["block_path"]) for m in areas}) == 6


def test_text_extraction_batches_without_sending_cad_or_boq(tmp_path):
    from app.db import get_session_factory
    from app.models.document import SourceDocument
    from app.models.parse_block import ParseBlock
    from app.models.project import Project
    from app.services.extraction import run_extraction
    with configured_client(tmp_path) as client:
        pid = project(client)
        with get_session_factory()() as session:
            for number, (extension, text) in enumerate([(".pdf", "正文甲" * 200), (".docx", "正文乙" * 200), (".dwg", "CAD不应发送" * 1000), (".xls", "BOQ不应发送" * 1000)]):
                source = SourceDocument(project_id=pid, filename=str(number)+extension, extension=extension, media_type="application/octet-stream", storage_path="unused", sha256=str(number), size_bytes=1, status="parsed")
                session.add(source); session.flush()
                session.add(ParseBlock(document_id=source.id, ordinal=0, text=text, location={"kind": "test"}))
            session.commit()
            class Provider:
                async def complete_json(self, system, payload, schema):
                    text = payload["source_text"]
                    assert len(text) <= 1000
                    assert "CAD" not in text and "BOQ" not in text
                    source_id = re.search(r"\[([^]]+)\]", text)[1]
                    return schema(facts=[{"field_name": "范围", "raw_value": "甲" if "正文甲" in text else "乙", "source_block_ids": [source_id]}], requirements=[])
            result = run_extraction(session, session.get(Project, pid), Provider(), chunk_chars=1000)
            assert {f["raw_value"] for f in result["facts"]} == {"甲", "乙"}


@pytest.mark.parametrize("text", ["本项目工期为九十日历天。", "本项目位于北京，主体采用木结构。", "组织本项目位于北京的施工作业。"])
def test_method_parts_cannot_add_project_parameters(text):
    from app.services.generation_guard import validate_generated
    snapshot = {"snapshot_id": "s", "version": 1, "facts_version": 1, "facts": [{"id": "f", "field_name": "工期", "value": "120日历天", "source_type": "confirmed"}], "requirements": []}
    generated = {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": "f", "field": "value"}, {"kind": "method", "text": text}]}]}
    with pytest.raises(ValueError):
        validate_generated(snapshot, generated, {"f"})


def test_valid_typed_project_reference_is_rendered_from_snapshot():
    from app.services.generation_guard import validate_generated
    snapshot = {"snapshot_id": "s", "version": 1, "facts_version": 1, "facts": [{"id": "f", "field_name": "工期", "value": "120日历天", "source_type": "confirmed"}], "requirements": []}
    generated = {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": "f", "field": "value"}, {"kind": "method", "text": "组织分区流水施工。"}]}]}
    result = validate_generated(snapshot, generated, {"f"})
    assert "120日历天" in result["blocks"][0]["text"]
    assert "组织分区流水施工。" in result["blocks"][0]["text"]


def test_legacy_free_text_cannot_smuggle_unfounded_project_properties():
    from app.services.generation_guard import validate_generated
    snapshot = {"snapshot_id": "s", "version": 1, "facts_version": 1, "facts": [{"id": "f", "value": "120日历天"}]}
    with pytest.raises(ValueError):
        validate_generated(snapshot, {"blocks": [{"type": "paragraph", "text": "{{fact:f}}，本项目位于北京，主体采用木结构。"}]}, {"f"})


def test_boq_field_reference_keeps_quantity_unit_and_unit_project_scope():
    from app.services.generation_guard import validate_generated
    snapshot = {"snapshot_id": "s", "version": 1, "facts_version": 1, "facts": [{"id": "f", "value": "原清单值", "source_type": "boq", "attributes": {"unit_project": "A楼", "name": "平整场地", "quantity": "6", "unit": "m2"}}]}
    result = validate_generated(snapshot, {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": "f", "field": "quantity"}]}]}, {"f"})
    text = result["blocks"][0]["text"]
    assert all(part in text for part in ["A楼", "平整场地", "6 m2"])


def test_generation_receives_only_published_requirements(tmp_path, monkeypatch):
    from app.db import get_session_factory
    from app.models.requirement import Requirement
    with configured_client(tmp_path) as client:
        pid = project(client); fact = add_fact(client, pid)
        requirement = client.post(f"/api/projects/{pid}/requirements/manual", json={"text": "严禁采用爆破开挖"}).json()
        publish(client, pid)
        with get_session_factory()() as session:
            session.get(Requirement, requirement["id"]).text = "后来修改的草稿要求"; session.commit()
        def generate(**kwargs):
            assert kwargs["requirements"][0]["text"] == "严禁采用爆破开挖"
            return {"blocks": [{"type": "paragraph", "parts": [{"kind": "fact", "fact_id": fact["id"], "field": "value"}, {"kind": "method", "text": "组织分区流水施工。"}]}]}
        monkeypatch.setattr("app.services.generation.generate_chapter", generate)
        chapter = client.post(f"/api/projects/{pid}/chapters", json={"title": "施工部署", "blocks": []}).json()
        assert client.post(f"/api/chapters/{chapter['id']}/generate").status_code == 200
