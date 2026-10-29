"""Only explicit, uniquely targeted, dated quantity changes may auto-override."""
from collections import defaultdict
from datetime import date
import re


def document_date(blocks):
    for block in blocks[:30]:
        for line in block.text.splitlines():
            match = re.fullmatch(r"\s*(?:(?:发布日期|补疑日期|日期)\s*[:：]\s*)?(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?\s*", line)
            if match:
                try:
                    return date(*map(int, match.groups())).isoformat()
                except ValueError:
                    pass
    return None


def explicit_quantity_changes(facts, documents, records, blocks):
    changes = defaultdict(list)
    issues = []
    codes = defaultdict(list)
    for fact in facts:
        if fact.get("source_type") == "boq":
            codes[fact["attributes"]["code"]].append(fact)
    for document in documents:
        record = records.get(document.id)
        if not record or record.kind != "supplement":
            continue
        document_blocks = blocks[document.id]
        published = document_date(document_blocks)
        for block in document_blocks:
            for clause in re.split(r"[。；]", block.text):
                mentioned = set(re.findall(r"(?<![A-Za-z0-9])(?:[A-Za-z]{0,5})?\d{12,}(?!\d)", clause))
                change = re.search(r"工程量[^。；\n]{0,80}?(?:调整为|更改为|改为|修改为|变更为|修正为|应为)\s*(\d+(?:\.\d+)?)\s*(m[23²³]?|㎡|吨|t|个|套|根|项)?", clause, re.I)
                if not change or len(mentioned) != 1:
                    continue
                candidates = codes.get(next(iter(mentioned)), [])
                if len(candidates) > 1:
                    candidates = [f for f in candidates if f["attributes"]["unit_project"] in clause]
                if len(candidates) != 1:
                    issues.append({"document_id": document.id, "message": "补疑中的编码不能唯一对应单位工程，需人工登记采用值"})
                    continue
                target = candidates[0]
                unit = (change[2] or "").lower().replace("²", "2").replace("³", "3").replace("㎡", "m2")
                original_unit = target["unit"].lower().replace("²", "2").replace("³", "3").replace("㎡", "m2")
                if unit and unit != original_unit:
                    issues.append({"document_id": document.id, "message": "补疑工程量单位与清单不一致，未自动换算或覆盖"})
                    continue
                changes[target["id"]].append({"quantity": change[1], "date": published, "source_block_ids": [block.id], "document_id": document.id, "reason": "明确补疑原文：" + clause.strip()})
    return changes, issues


def apply_explicit_changes(facts, documents, records, blocks, value_builder):
    changes, issues = explicit_quantity_changes(facts, documents, records, blocks)
    index = {f["id"]: f for f in facts}
    for target_id, candidates in changes.items():
        dates = {c["date"] for c in candidates}
        if (len(candidates) > 1 and None in dates) or any(len({c["quantity"] for c in candidates if c["date"] == day}) > 1 for day in dates):
            issues.append({"message": "同一清单项目存在无法明确排序的补疑冲突，保留清单值并等待人工确认：" + target_id})
            continue
        target = index[target_id]
        for change in sorted(candidates, key=lambda c: c["date"] or ""):
            previous = target["value"]
            target["attributes"] = {**target["attributes"], "quantity": change["quantity"]}
            target["value"] = value_builder(target["attributes"])
            target["source_block_ids"] = list(dict.fromkeys([*target["source_block_ids"], *change["source_block_ids"]]))
            target["overrides"].append({**change, "previous_value": previous, "adopted_value": target["value"]})
    return issues
