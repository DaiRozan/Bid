"""Project-scoped drafts and checksum-verified, immutable writing snapshots."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from uuid import uuid4

from sqlalchemy import select, func

from ..config import get_settings
from ..models.chapter import Chapter
from ..models.document import SourceDocument
from ..models.fact import Fact
from ..models.fact_snapshot import FactAdoption, FactSnapshot
from ..models.material import MaterialRecord
from ..models.parse_block import ParseBlock
from ..models.requirement import Requirement


def boq_value(item):
    quantity = item["quantity"] if item["quantity"] is not None else "未载明（不得推测）"
    return f"{item['unit_project']} / {item['section']} / {item['name']}；项目编码：{item['code']}；项目特征：{item['features']}；工程量：{quantity} {item['unit']}"


def build_draft(session, project):
    documents = list(session.scalars(select(SourceDocument).where(SourceDocument.project_id == project.id).order_by(SourceDocument.created_at, SourceDocument.id)))
    records = {r.document_id: r for r in session.scalars(select(MaterialRecord).join(SourceDocument, SourceDocument.id == MaterialRecord.document_id).where(SourceDocument.project_id == project.id))}
    blocks = list(session.scalars(select(ParseBlock).join(SourceDocument, SourceDocument.id == ParseBlock.document_id).where(SourceDocument.project_id == project.id).order_by(ParseBlock.document_id, ParseBlock.ordinal)))
    per_document = defaultdict(list)
    locations = {}
    for block in blocks:
        per_document[block.document_id].append(block)
        locations[(block.document_id, json.dumps(block.location, sort_keys=True, ensure_ascii=False))] = block.id
    facts, review, issues = [], [], []
    document_paths = {d.id: records[d.id].archive_path if d.id in records else d.filename for d in documents}
    for fact in session.scalars(select(Fact).where(Fact.project_id == project.id)):
        if fact.status == "confirmed" and fact.confirmed_value:
            facts.append({"id": fact.id, "field_name": fact.field_name, "value": fact.confirmed_value, "unit": fact.unit, "source_type": "confirmed", "source_block_ids": fact.source_block_ids, "overrides": []})
    for document in documents:
        record = records.get(document.id)
        if document.status in {"failed", "needs_review", "uploaded", "parsing"}:
            issues.append({"document_id": document.id, "message": f"{document.filename}：{document.error_message or '尚未完成解析'}"})
        if not record:
            continue
        for warning in record.analysis.get("warnings", [])[:10]:
            issues.append({"document_id": document.id, "message": document.filename + "：" + warning})
        for item in record.analysis.get("items", []):
            source_id = locations.get((document.id, json.dumps(item["location"], sort_keys=True, ensure_ascii=False)))
            facts.append({"id": item["id"], "field_name": f"{item['unit_project']} / {item['name']}", "value": boq_value(item), "unit": item["unit"], "source_type": "boq", "source_block_ids": [source_id] if source_id else [], "document_id": document.id, "archive_path": record.archive_path, "location": item["location"], "attributes": item, "overrides": []})
        for measurement in record.analysis.get("measurements", []):
            review.append({**measurement, "document_id": document.id, "archive_path": record.archive_path, "record_type": "cad_measurement"})
        if record.kind == "drawing":
            for block in per_document[document.id]:
                if len(block.text.strip()) >= 4 and re.search(r"[\u4e00-\u9fffA-Za-z]", block.text):
                    review.append({"id": "drawing-" + block.id, "field_name": document.filename + " / 图纸原文", "value": block.text, "source_block_ids": [block.id], "document_id": document.id, "archive_path": record.archive_path, "location": block.location, "record_type": "drawing_note", "adoptable": True})
        elif record.kind == "supplement":
            # Whole clauses are source evidence, never guessed numeric overrides.
            issues.append({"document_id": document.id, "message": f"{document.filename}：补疑原文已归档，请核对其对清单/项目事实的明确修改并登记采用值"})
            for block in per_document[document.id]:
                if block.text.strip():
                    review.append({"id": "source-" + block.id, "field_name": document.filename + " / 补疑条款", "value": block.text, "source_block_ids": [block.id], "document_id": document.id, "archive_path": record.archive_path, "location": block.location, "record_type": "supplement_clause", "adoptable": True})
        elif document.extension in {".pdf", ".doc", ".docx"}:
            # Explicit labelled source lines are candidates, not inferred facts.
            for block in per_document[document.id]:
                for line in block.text.splitlines():
                    match = re.match(r"\s*(?:\d+(?:\.\d+)*[、.．]?\s*)?(项目名称|工程名称|建设地点|计划工期|质量标准|建设规模)\s*[:：]\s*(.{2,})", line)
                    if match:
                        review.append({"id": "source-" + block.id + "-" + hashlib.sha256(line.encode()).hexdigest()[:8], "field_name": match[1], "value": match[2].strip(), "source_block_ids": [block.id], "document_id": document.id, "archive_path": record.archive_path, "location": block.location, "record_type": "source_fact", "adoptable": True})
    from .fact_adoption import apply_explicit_changes
    issues.extend(apply_explicit_changes(facts, documents, records, per_document, boq_value))
    index = {f["id"]: f for f in facts}
    candidates = {f["id"]: f for f in review if f.get("adoptable")}
    for adoption in session.scalars(select(FactAdoption).where(FactAdoption.project_id == project.id).order_by(FactAdoption.created_at, FactAdoption.id)):
        fact = index.get(adoption.target_id)
        if fact is None and adoption.target_id in candidates:
            candidate = candidates[adoption.target_id]
            fact = {**candidate, "source_type": candidate["record_type"], "overrides": []}
            facts.append(fact)
            index[fact["id"]] = fact
        if fact is None:
            issues.append({"message": "采用记录的原始事实已不存在，请核对：" + adoption.target_id})
            continue
        fact["overrides"].append({"previous_value": fact["value"], "adopted_value": adoption.value, "reason": adoption.reason, "source_block_ids": adoption.source_block_ids, "adoption_id": adoption.id})
        fact["value"] = adoption.value
        fact["source_block_ids"] = adoption.source_block_ids
    return {"project_id": project.id, "project_name": project.name, "facts": facts, "review": review, "issues": issues, "documents": [{"id": d.id, "filename": d.filename, "archive_path": document_paths[d.id], "sha256": d.sha256, "status": d.status, "analysis_summary": records[d.id].analysis.get("summary", {}) if d.id in records else {}, "detail_file": records[d.id].analysis.get("detail_file") if d.id in records else None, "detail_sha256": records[d.id].analysis.get("detail_sha256") if d.id in records else None} for d in documents], "requirements": [{"id": r.id, "text": r.text, "category": r.category, "source_block_ids": r.source_block_ids} for r in session.scalars(select(Requirement).where(Requirement.project_id == project.id))], "_blocks": per_document}


def markdown_files(draft, include_details=False):
    files = {}
    lines = [f"# {draft['project_name']}：采用事实", "", "采用规则：最新明确补疑及清单为准；图纸计算仅作复核。", ""]
    grouped = defaultdict(list)
    for fact in draft["facts"]:
        lines.extend([f"## {fact['field_name']}", f"事实 ID：{fact['id']}", "", fact["value"], "", "出处片段：" + "、".join(fact.get("source_block_ids", [])), ""])
        for override in fact.get("overrides", []):
            lines.extend([f"覆盖记录：{override['previous_value']} → {override['adopted_value']}", f"采用原因：{override['reason']}", ""])
        if fact.get("source_type") == "boq":
            grouped[fact["attributes"]["unit_project"]].append(fact)
    files["采用事实.md"] = "\n".join(lines)
    for title, facts in grouped.items():
        name = "清单/" + hashlib.sha256(title.encode()).hexdigest()[:12] + ".md"
        files[name] = f"# {title}\n\n" + "\n\n".join(f"## {f['field_name']}\n\nID：{f['id']}\n\n{f['value']}\n\n出处：{f.get('archive_path')} / {json.dumps(f.get('location'), ensure_ascii=False)}" for f in facts)
    for document in draft["documents"]:
        blocks = draft["_blocks"][document["id"]]
        lines = ["# " + document["filename"], "", "原始路径：" + document["archive_path"], "SHA256：" + document["sha256"], ""]
        for block in blocks:
            lines.extend([f"## 片段 {block.id}", json.dumps(block.location, ensure_ascii=False), "", block.text, ""])
        files["资料/" + document["id"] + ".md"] = "\n".join(lines)
        if include_details and document.get("detail_file"):
            data = Path(document["detail_file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != document["detail_sha256"]:
                raise ValueError("图纸分析文件校验失败，请重新分析后发布")
            files["图纸明细/" + document["id"] + ".json.gz"] = data
    files["图纸算量复核.md"] = "# 图纸计算与待确认摘录\n\n所有计算仅作复核，不自动覆盖清单；实例统计不等于构件工程量。\n\n" + "\n\n".join(json.dumps(r, ensure_ascii=False) for r in draft["review"])
    files["待处理事项.md"] = "# 待处理事项\n\n" + "\n".join("- " + i["message"] for i in draft["issues"])
    return files


def write_draft(session, project):
    draft = build_draft(session, project)
    directory = get_settings().data_dir / "projects" / project.id / "facts" / "draft"
    for name, content in markdown_files(draft).items():
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return draft, directory.resolve()


def publish_snapshot(session, project, acknowledge_issues=False):
    draft = build_draft(session, project)
    if not draft["facts"]:
        raise ValueError("没有可采用事实，请先解析清单或确认项目事实")
    if draft["issues"] and not acknowledge_issues:
        raise ValueError("尚有待处理资料或补疑，请核对并明确确认后再发布")
    version = (session.scalar(select(func.max(FactSnapshot.version)).where(FactSnapshot.project_id == project.id)) or 0) + 1
    root = get_settings().data_dir / "projects" / project.id / "facts"
    staging = root / (".staging-" + uuid4().hex)
    directory = root / f"v{version:04d}"
    files = markdown_files(draft, include_details=True)
    payload = {k: v for k, v in draft.items() if not k.startswith("_")}
    payload.update(version=version, facts_version=project.facts_version + 1, created_at=datetime.now(timezone.utc).isoformat(), acknowledged_issues=draft["issues"])
    files["facts.json"] = json.dumps(payload, ensure_ascii=False, indent=2)
    manifest = {"project_id": project.id, "version": version, "files": {}}
    try:
        for name, content in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            target.write_bytes(data)
            manifest["files"][name] = hashlib.sha256(data).hexdigest()
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if directory.exists():
            raise ValueError("事实版本发生并发冲突，请重新发布")
        staging.rename(directory)
        project.facts_version += 1
        record = FactSnapshot(project_id=project.id, version=version, facts_version=project.facts_version, directory=str(directory.resolve()), manifest=manifest)
        session.add(record)
        for chapter in session.scalars(select(Chapter).where(Chapter.project_id == project.id)):
            chapter.stale = True
        session.commit()
        return load_snapshot(session, project)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def load_snapshot(session, project, version=None):
    query = select(FactSnapshot).where(FactSnapshot.project_id == project.id)
    query = query.where(FactSnapshot.version == version) if version else query.order_by(FactSnapshot.version.desc())
    record = session.scalar(query)
    if record is None:
        raise LookupError("请先核对并发布项目事实库，才能生成章节")
    directory = Path(record.directory)
    for name, digest in record.manifest["files"].items():
        path = directory / name
        if not path.resolve().is_relative_to(directory.resolve()) or path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("事实库文件校验失败，已拒绝读取被修改的固定版本：" + name)
    payload = json.loads((directory / "facts.json").read_text(encoding="utf-8"))
    if payload["project_id"] != project.id:
        raise RuntimeError("事实库项目归属校验失败")
    payload.update(snapshot_id=record.id, directory=str(directory), files=list(record.manifest["files"]))
    return payload


def adopt_fact(session, project, target_id, value, reason, source_block_ids):
    draft = build_draft(session, project)
    targets = {f["id"] for f in draft["facts"]} | {r["id"] for r in draft["review"] if r.get("adoptable")}
    if target_id not in targets:
        raise ValueError("采用目标不属于当前项目，或只是不可直接采用的图形测量")
    allowed = set(session.scalars(select(ParseBlock.id).join(SourceDocument, SourceDocument.id == ParseBlock.document_id).where(SourceDocument.project_id == project.id)))
    if not source_block_ids or any(source not in allowed for source in source_block_ids):
        raise ValueError("采用值必须提供当前项目有效来源片段，不能引用其他项目资料")
    record = FactAdoption(project_id=project.id, target_id=target_id, value=value, reason=reason, source_block_ids=source_block_ids)
    session.add(record)
    session.commit()
    return record
