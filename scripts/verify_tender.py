"""Reproducible real-material acceptance; never changes the source archive.

python scripts/verify_tender.py PATH --project-code ACCEPTANCE-20261029
Add --publish-test-snapshot and optionally --live-generation for a marked
acceptance project. Publication acknowledges parser warnings for this test;
it is not professional approval of the project data.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db import get_session_factory
from app.models.document import SourceDocument
from app.models.material import MaterialRecord


def main():
    parser = argparse.ArgumentParser(description="招标资料包真实验收")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--project-code", default="ACCEPTANCE-20261029")
    parser.add_argument("--name", default="招标资料验收项目")
    parser.add_argument("--publish-test-snapshot", action="store_true")
    parser.add_argument("--live-generation", action="store_true")
    parser.add_argument("--reanalyze-materials", action="store_true", help="使用当前适配器重新分析清单和图纸，不修改旧固定版本")
    args = parser.parse_args()
    source = args.archive.resolve(strict=True)
    os.chdir(ROOT)
    started = time.monotonic()
    with TestClient(app) as client:
        projects = client.get("/api/projects").json()
        project = next((p for p in projects if p["code"] == args.project_code), None)
        if project is None:
            response = client.post("/api/projects", json={"code": args.project_code, "name": args.name, "engineering_type": "building"})
            response.raise_for_status()
            project = response.json()
        pid = project["id"]
        with source.open("rb") as stream:
            response = client.post(f"/api/projects/{pid}/documents", files={"file": (source.name, stream, "application/zip")})
        response.raise_for_status()
        response = client.post(f"/api/documents/{response.json()['id']}/parse")
        response.raise_for_status()
        if args.reanalyze_materials:
            materials = client.get(f"/api/projects/{pid}/documents").json()
            for item in materials:
                if item["extension"] in {".xls", ".xlsx", ".dwg", ".dxf"}:
                    print("重新分析：" + item["filename"], flush=True)
                    checked = client.post(f"/api/documents/{item['id']}/parse")
                    checked.raise_for_status()
        documents = client.get(f"/api/projects/{pid}/documents").json()
        draft = client.get(f"/api/projects/{pid}/fact-library"); draft.raise_for_status()
        draft = draft.json()
        failures = [d for d in documents if d["status"] in {"failed", "needs_review", "uploaded", "parsing"}]
        report = {"project_id": pid, "project_code": args.project_code, "source": str(source), "document_count": len(documents), "facts": draft["fact_count"], "review_entries": draft["review_count"], "draft_directory": draft["directory"], "issues": draft["issues"], "failures": [{"name": d["filename"], "error": d["error_message"]} for d in failures], "documents": [{k: d.get(k) for k in ["filename", "status", "archive_path", "block_count", "analysis_summary"]} for d in documents]}
        # Independently count original XLS rows by serial number and unit, not
        # by the production adapter's item-code recognition.
        with get_session_factory()() as session:
            sources = session.execute(select(SourceDocument, MaterialRecord).join(MaterialRecord, MaterialRecord.document_id == SourceDocument.id).where(SourceDocument.project_id == pid)).all()
            independent = 0
            for document, material in sources:
                if document.extension != ".xls" or not material.analysis.get("summary", {}).get("bill_sheet_count"):
                    continue
                import xlrd
                book = xlrd.open_workbook(document.storage_path, on_demand=True)
                try:
                    for sheet in book.sheets():
                        if "E.1" not in sheet.name:
                            continue
                        for row in range(5, sheet.nrows):
                            if str(sheet.cell_value(row, 0)).strip().isdigit() and all(str(sheet.cell_value(row, col)).strip() for col in [1, 2, 4]):
                                independent += 1
                finally:
                    book.release_resources()
            report["independent_boq_item_count"] = independent
            parsed_count = sum(d["analysis_summary"].get("item_count", 0) for d in documents)
            report["boq_count_matches"] = independent == parsed_count if independent else None
        if args.publish_test_snapshot:
            response = client.post(f"/api/projects/{pid}/fact-library/publish?summary=true", json={"acknowledge_issues": True})
            response.raise_for_status()
            report["snapshot"] = response.json()
        if args.live_generation:
            response = client.post(f"/api/projects/{pid}/chapters", json={"title": "土石方工程施工部署：仅写一小段，引用平整场地事实，不列编号", "blocks": []})
            response.raise_for_status()
            chapter_id = response.json()["id"]
            generated = client.post(f"/api/chapters/{chapter_id}/generate")
            report["generation"] = {"status_code": generated.status_code, "result": generated.json()}
        report["seconds"] = round(time.monotonic() - started, 2)
        output = ROOT / "data" / "acceptance"
        output.mkdir(parents=True, exist_ok=True)
        (output / "acceptance-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        rows = ["# 真实招标资料验收报告", "", f"项目：{project['name']}（{args.project_code}，验收项目）", f"原始资料：{source}", f"导入文件：{len(documents)}；失败/未处理：{len(failures)}", f"采用事实：{draft['fact_count']}；原文与测量复核：{draft['review_count']}", f"独立核对分部分项条数：{independent}；与解析结果一致：{report['boq_count_matches']}", "", "## 文件处理", ""]
        for d in documents:
            rows.append(f"- {d['filename']}：{d['status']}；{d['block_count']} 个文字片段；{json.dumps(d['analysis_summary'], ensure_ascii=False)}")
        rows += ["", "## 事实版本", "", "草稿目录：" + draft["directory"]]
        if "snapshot" in report:
            rows.append("验收固定版本目录：" + report["snapshot"]["directory"])
        rows += ["", "## 图纸读取与算量边界", "", "已验证块变换、闭合区域面积、块实例计数，以及明确长宽高属性的体积计算。图纸测量保留图元和公式，尚未核定图例、多视图、楼层和施工计量范围，不能当成已核准构件工程量。原图单位不明或代理对象信息不完整的内容保留待复核；真实图纸缺少明确高度时不生成体积。", "", "## 待处理事项", ""]
        rows += ["- " + issue["message"] for issue in draft["issues"]]
        rows += ["", "## 写作验证", "", "生成接口和重试均要求固定事实版本；项目事实通过类型化引用由服务端插入，通用叙述只能选择预设语句，越界引用、任意项目属性和自由文本被拒绝。编制要求来自同一固定版本。验收发布仅用于测试机制，不表示专业人员已审核本项目的补疑和工程量。"]
        if "generation" in report:
            rows.append(f"当前协议真实模型生成 HTTP：{report['generation']['status_code']}")
        (output / "验收报告.md").write_text("\n".join(rows), encoding="utf-8")
        print(json.dumps({"report": str(output / "验收报告.md"), "files": len(documents), "facts": draft["fact_count"], "independent_boq_items": independent, "failures": len(failures), "seconds": report["seconds"]}, ensure_ascii=False))
        if failures or report["boq_count_matches"] is False or ("generation" in report and report["generation"]["status_code"] != 200):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
