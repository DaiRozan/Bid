import math

import ezdxf
import pytest


def test_cad_area_count_and_explicit_volume_keep_entity_evidence(tmp_path):
    from app.adapters.cad import analyze_cad
    doc = ezdxf.new()
    doc.units = 6  # metres
    model = doc.modelspace()
    boundary = model.add_lwpolyline([(0, 0), (3, 0), (3, 2), (0, 2)], close=True)
    block = doc.blocks.new("混凝土构件")
    for tag in ["LENGTH", "WIDTH", "HEIGHT"]:
        block.add_attdef(tag, (0, 0))
    insert = model.add_blockref("混凝土构件", (10, 0))
    insert.add_auto_attribs({"LENGTH": "3", "WIDTH": "2", "HEIGHT": "2"})
    # An identical drawing in a paper layout must not double the measurements.
    doc.layouts.new("打印图").add_lwpolyline([(0, 0), (3, 0), (3, 2), (0, 2)], close=True)
    path = tmp_path / "drawing.dxf"
    doc.saveas(path)
    result = analyze_cad(path)
    area = next(x for x in result["measurements"] if x["type"] == "area")
    volume = next(x for x in result["measurements"] if x["type"] == "volume")
    count = next(x for x in result["measurements"] if x["type"] == "count")
    assert area["value"] == pytest.approx(6)
    assert area["unit"] == "m2"
    assert area["source_handles"] == [boundary.dxf.handle]
    assert volume["value"] == pytest.approx(12)
    assert volume["unit"] == "m3"
    assert volume["formula"]
    assert insert.dxf.handle in volume["source_handles"]
    assert count["value"] == 1
    assert all(x["adoptable"] is False for x in result["measurements"])


def test_nested_block_transform_applies_to_closed_boundary(tmp_path):
    from app.adapters.cad import analyze_cad
    doc = ezdxf.new()
    doc.units = 6
    inner = doc.blocks.new("轮廓")
    inner.add_lwpolyline([(0, 0), (3, 0), (3, 2), (0, 2)], close=True)
    outer = doc.blocks.new("构件")
    outer.add_blockref("轮廓", (2, 2))
    doc.modelspace().add_blockref("构件", (10, 10), dxfattribs={"xscale": 2, "yscale": 3})
    path = tmp_path / "nested.dxf"
    doc.saveas(path)
    result = analyze_cad(path)
    area = next(x for x in result["measurements"] if x["type"] == "area")
    assert area["value"] == pytest.approx(36)
    assert len(area["block_path"]) == 2


def test_unitless_drawing_does_not_invent_physical_units_or_volume(tmp_path):
    from app.adapters.cad import analyze_cad
    doc = ezdxf.new()
    doc.units = 0
    doc.modelspace().add_lwpolyline([(0, 0), (3, 0), (3, 2), (0, 2)], close=True)
    doc.modelspace().add_text("厚度未知，不能自动假定")
    path = tmp_path / "unitless.dxf"
    doc.saveas(path)
    result = analyze_cad(path)
    assert result["warnings"]
    assert all(m["unit"] not in {"m", "m2", "m3"} for m in result["measurements"])
    assert not any(m["type"] == "volume" for m in result["measurements"])


def test_curved_boundary_includes_arc_segment_area(tmp_path):
    from app.adapters.cad import analyze_cad
    doc = ezdxf.new()
    doc.units = 6
    doc.modelspace().add_lwpolyline([(0, 0, 1), (2, 0, 0)], format="xyb", close=True)
    path = tmp_path / "arc.dxf"
    doc.saveas(path)
    result = analyze_cad(path)
    area = next(x for x in result["measurements"] if x["type"] == "area")
    assert area["value"] == pytest.approx(math.pi / 2)
