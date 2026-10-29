from collections import Counter, defaultdict
import hashlib
import math
import os
from pathlib import Path
import re
import shutil

import ezdxf

from ..config import get_settings
from .cad_geometry import UNIT_METRES, entity_measurements, attribute_volume


def converter_executable():
    candidates = [get_settings().oda_converter_path, shutil.which("ODAFileConverter")]
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    candidates.append(str(local / "TechnicalBid/tools/oda/ODAFileConverter.exe"))
    for root in [Path("C:/Program Files/ODA"), Path("C:/Program Files (x86)/ODA")]:
        if root.exists():
            candidates.extend(str(p) for p in root.glob("**/ODAFileConverter.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise ValueError("未找到 DWG 转换器，请安装 ODA 或配置 ODA_CONVERTER_PATH")


def dxf_source(path):
    if path.suffix.lower() == ".dxf":
        return path
    from ezdxf.addons import odafc
    ezdxf.options.set("odafc-addon", "win_exec_path", converter_executable())
    converted = path.parent / "converted" / (path.stem + ".dxf")
    converted.parent.mkdir(exist_ok=True)
    if not converted.exists():
        odafc.convert(path.resolve(), converted.resolve(), audit=True)
    return converted


def original_handle(entity):
    original = getattr(entity, "source_of_copy", None)
    return str(entity.dxf.get("handle") or (original.dxf.get("handle") if original else "virtual"))


def analyze_cad(path: Path) -> dict:
    drawing = ezdxf.readfile(dxf_source(path))
    metres = UNIT_METRES.get(drawing.units)
    warnings = ["图形测量及块实例数量仅供复核，可能包含图例、图框和重复视图，不能直接作为清单工程量。"]
    if metres is None:
        warnings.append("图纸未明确支持的计量单位，禁止推定为毫米或米。")
    texts, measurements, dimensions, inserts = [], [], [], []
    counts = defaultdict(list)
    types = Counter()
    visited_count = 0

    def provenance(entity, layout, block_path):
        handle = original_handle(entity)
        return {"kind": "cad", "handle": handle, "layer": entity.dxf.get("layer", "0"), "layout": layout, "block_path": block_path}

    def append_measure(item, location, handles=None):
        item.update(source_handles=handles or [location["handle"]], location=location, block_path=location["block_path"], adoptable=False, review_status="needs_review", scope="模型空间内单个图形/块实例；未核定施工计量范围")
        key = repr((location, item["type"], len(measurements)))
        item["id"] = "cad-" + hashlib.sha256(key.encode()).hexdigest()[:24]
        measurements.append(item)

    def walk(entities, layout, block_path, depth=0):
        nonlocal visited_count
        if depth > 16:
            warnings.append("块引用递归超过16层，相关图形待复核")
            return
        for entity in entities:
            visited_count += 1
            if visited_count > 500_000:
                raise ValueError("图纸图元展开超过50万，需拆分后处理")
            kind = entity.dxftype()
            types[kind] += 1
            loc = provenance(entity, layout, block_path)
            if kind in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
                text = entity.plain_text() if kind == "MTEXT" else entity.dxf.get("text", "")
                text = re.sub(r"\\U\+([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text)
                if text.strip():
                    loc["insert"] = list(entity.dxf.get("insert", (0, 0, 0)))
                    texts.append({"text": text.strip(), "location": loc})
            if kind == "DIMENSION":
                try:
                    measured = entity.get_measurement()
                    if isinstance(measured, (float, int)) and math.isfinite(measured):
                        dimensions.append({"value": measured, "display_text": entity.dxf.get("text", "<>"), "location": loc})
                except (ValueError, TypeError, AttributeError):
                    pass
            if kind == "INSERT":
                name = entity.dxf.name
                path_element = f"{name}@{loc['handle']}"
                if any(p.split("@")[0] == name for p in block_path):
                    warnings.append(f"循环块引用 {name} 已跳过")
                    continue
                attributes = [{"tag": a.dxf.tag, "text": a.dxf.text, "handle": original_handle(a)} for a in entity.attribs]
                inserts.append({"name": name, "attributes": attributes, "location": loc, "insert": list(entity.dxf.insert)})
                for a in entity.attribs:
                    texts.append({"text": f"{a.dxf.tag}：{a.dxf.text}", "location": provenance(a, layout, block_path + [path_element])})
                if layout == "Model":
                    if not name.startswith("*") and not re.search(r"图框|图例|图签|legend|title", name, re.I):
                        counts[(name, loc["layer"])].append(loc)
                    volume = attribute_volume(attributes, metres)
                    if volume:
                        append_measure(volume, loc, [loc["handle"], *[a["handle"] for a in attributes]])
                try:
                    copies = entity.virtual_entities(skipped_entity_callback=lambda e, reason: warnings.append(f"未能展开图元 {original_handle(e)}：{reason}"))
                    walk(copies, layout, block_path + [path_element], depth + 1)
                except (ValueError, ezdxf.DXFError, NotImplementedError) as exc:
                    warnings.append(f"块 {name} 无法完整展开：{type(exc).__name__}")
            elif layout == "Model":
                try:
                    for item in entity_measurements(entity, metres):
                        append_measure(item, loc)
                except (ValueError, TypeError, AttributeError, ZeroDivisionError):
                    warnings.append(f"图元 {loc['handle']} 无法可靠测量")

    for layout in drawing.layouts:
        walk(layout, layout.name, [])
    for (name, layer), sources in counts.items():
        append_measure({"type": "count", "name": name, "value": len(sources), "unit": "个块实例", "formula": "按块名称、图层和实例路径统计；不等于经核准的构件数量", "instances": sources}, sources[0], [s["handle"] for s in sources])
    xrefs = [b.name for b in drawing.blocks if b.block.is_xref]
    if xrefs:
        warnings.append("外部参照尚需核对是否齐全：" + "、".join(xrefs))
    if types["ACAD_PROXY_ENTITY"]:
        warnings.append(f"含 {types['ACAD_PROXY_ENTITY']} 个代理对象，无法保证完整读取其专业属性")
    return {"summary": {"drawing_units_code": drawing.units, "metres_per_unit": metres, "entity_count": visited_count, "text_count": len(texts), "measurement_count": len(measurements), "dimension_count": len(dimensions), "block_instance_count": len(inserts), "proxy_count": types["ACAD_PROXY_ENTITY"], "xref_count": len(xrefs)}, "text_records": texts, "dimensions": dimensions, "block_instances": inserts, "measurements": measurements, "entity_types": dict(types), "warnings": list(dict.fromkeys(warnings))}
