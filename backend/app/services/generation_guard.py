"""Resolve project values only from verified snapshot references."""
import re

from ..schemas.chapter import ChapterBlock

FACT_TOKEN = re.compile(r"\{\{fact:([A-Za-z0-9_-]+)\}\}")


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
    blocks = generated.get("blocks", [])
    if not blocks:
        raise ValueError("模型未返回有效正文")

    def render(text):
        tokens = FACT_TOKEN.findall(text)
        if any(token not in facts for token in tokens):
            raise ValueError("模型引用了当前固定版本之外的事实")
        literal = FACT_TOKEN.sub("", text)
        if "{{fact:" in literal or re.search(r"\d|[零一二两三四五六七八九十百千万]+(?:平方米|立方米|米|吨|层|个|套|天)", literal):
            raise ValueError("模型输出含未通过事实库引用的项目数字或规格，已拒绝保存")
        references.update(tokens)
        return FACT_TOKEN.sub(lambda match: facts[match[1]]["value"], text)

    rendered = []
    for raw in blocks:
        block = ChapterBlock.model_validate(raw).model_dump()
        if block["type"] == "paragraph":
            block["text"] = render(block["text"])
        else:
            block["rows"] = [[render(cell) for cell in row] for row in block["rows"]]
        rendered.append(block)
    for citation in generated.get("citations", []):
        if citation.get("fact_id") and citation["fact_id"] not in facts:
            raise ValueError("模型引用了不存在的项目事实")
    if not references:
        raise ValueError("模型正文没有引用已固定项目事实，已拒绝保存")
    return {"blocks": rendered, "citations": [{"type": "fact_library", "snapshot_id": snapshot["snapshot_id"], "version": snapshot["version"], "fact_ids": sorted(references)}], "open_issues": generated.get("open_issues", []), "facts_version": snapshot["facts_version"]}
