from pathlib import Path

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
    record.analysis = analysis
    document.status = "analyzed"
    document.error_message = None
    session.commit()
    return analysis
