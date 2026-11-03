"""Resolve project values only from verified snapshot references."""
import re

from ..schemas.chapter import ChapterBlock
from ..schemas.generation import Generated

def available_fields(fact):
    fields = {"value": fact["value"]}
    if fact.get("source_type") == "boq":
        attributes = fact.get("attributes", {})
        scope = " / ".join(str(attributes.get(k) or "未载明") for k in ["unit_project", "name"])
        labels = {"name": "名称", "unit_project": "单位工程", "features": "项目特征", "quantity": "工程量", "unit": "单位"}
        for key in ["name", "unit_project", "features", "quantity", "unit"]:
            value = attributes.get(key)
            if value is not None and value != "":
                suffix = " " + str(attributes.get("unit") or "未载明单位") if key == "quantity" else ""
                fields[key] = f"{scope}；{labels[key]}：{value}{suffix}"
    return fields


def select_facts(snapshot, chapter):
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]+", chapter.title))
    title = chapter.title
    synonyms = {"土方": ["土石方", "挖土", "场地", "清底"], "基础": ["基础", "垫层", "地基"], "结构": ["混凝土", "钢筋", "钢结构"], "进度": ["工期", "施工范围"], "施工": ["工期", "建设规模", "项目名称"]}
    for key, words in synonyms.items():
        if key in title:
            terms.update(words)
    def score(fact):
        text = fact["field_name"] + " " + fact["value"]
        return sum(term in text for term in terms) * 5 + (3 if fact["source_type"] != "boq" else 0)
    ordered = sorted(snapshot["facts"], key=score, reverse=True)
    selected, chars = [], 0
    for fact in ordered:
        item = {k: fact[k] for k in ["id", "field_name", "value", "source_type"]}
        item["fields"] = available_fields(fact)
        if chars + len(item["value"]) > 22000 or len(selected) >= 60:
            continue
        selected.append(item)
        chars += len(item["value"])
    if not selected:
        raise ValueError("没有适合本章的已固定事实")
    return selected


def validate_generated(snapshot, generated, permitted_ids):
    facts = {f["id"]: f for f in snapshot["facts"] if f["id"] in permitted_ids}
    references = set()
    parsed = Generated.model_validate(generated)

    def render(parts):
        output = []
        for part in parts:
            if part.kind == "method":
                output.append(part.text)
                continue
            fact = facts.get(part.fact_id)
            if fact is None or part.field not in available_fields(fact):
                raise ValueError("模型引用了当前固定版本之外的事实或字段")
            references.add(part.fact_id)
            output.append(available_fields(fact)[part.field])
        return "".join(output)

    rendered = []
    for raw in parsed.blocks:
        if raw.type == "paragraph":
            block = {"type": "paragraph", "text": render(raw.parts)}
        else:
            block = {"type": "table", "rows": [[render(cell) for cell in row] for row in raw.rows]}
        rendered.append(ChapterBlock.model_validate(block).model_dump())
    if not references:
        raise ValueError("模型正文没有引用已固定项目事实，已拒绝保存")
    return {"blocks": rendered, "citations": [{"type": "fact_library", "snapshot_id": snapshot["snapshot_id"], "version": snapshot["version"], "fact_ids": sorted(references)}], "open_issues": parsed.open_issues, "facts_version": snapshot["facts_version"]}
