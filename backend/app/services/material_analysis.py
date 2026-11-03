from pathlib import Path
import gzip
import hashlib
import json

from ..adapters.boq import analyze_boq
from ..adapters.cad import analyze_cad
from .material_import import ensure_record
from .parsing import sync_blocks


def analyze_material(session, document):
    path = Path(document.storage_path)
    record = ensure_record(session, document)
    analysis = analyze_cad(path) if document.extension in {".dwg", ".dxf"} else analyze_boq(path)
    blocks = [(r["text"], r["location"]) for r in analysis.get("text_records", [])]
    for item in analysis.get("items", []):
        text = f"单位工程：{item['unit_project']}；分部：{item['section']}；编码：{item['code']}；名称：{item['name']}；特征：{item['features']}；单位：{item['unit']}；工程量：{item['quantity'] if item['quantity'] is not None else '缺失'}"
        blocks.append((text, item["location"]))
    sync_blocks(session, document.id, blocks)
    record.analysis = {"origins": record.analysis.get("origins", []), **(compact_cad_analysis(path, analysis) if document.extension in {".dwg", ".dxf"} else analysis)}
    document.status = "analyzed"
    document.error_message = None
    session.commit()
    return analysis


def compact_cad_analysis(path, analysis):
    """Keep full measurements on disk; never hydrate a GB of CAD into each API read."""
    target = path.with_suffix(".analysis.json.gz")
    with gzip.open(target, "wt", encoding="utf-8", compresslevel=6) as output:
        json.dump(analysis, output, ensure_ascii=False, separators=(",", ":"))
    preview = []
    for kind, limit in [("volume", 20), ("count", 20), ("area", 40)]:
        entries = (m for m in analysis.get("measurements", []) if m["type"] == kind)
        from itertools import islice
        for measurement in islice(entries, limit):
            item = {k: v for k, v in measurement.items() if k != "instances"}
            item["source_handles"] = item["source_handles"][:10]
            item["preview_only"] = True
            preview.append(item)
    with target.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    return {"summary": analysis["summary"], "warnings": analysis["warnings"][:50], "measurements": preview, "detail_file": str(target.resolve()), "detail_sha256": digest}
