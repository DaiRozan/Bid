from openpyxl import Workbook


def test_multiline_boq_headers_preserve_scope_codes_features_and_missing_quantity(tmp_path):
    from app.adapters.boq import analyze_boq
    book = Workbook()
    sheet = book.active
    sheet.title = "分部分项"
    for row in [
        ["分部分项工程量清单计价表"],
        ["工程名称：1号楼土建"],
        ["序号", "项目编码", "项目名称", "项目特征描述", "计量\n单位", "工程量"],
        [None, "0101", "土石方工程"],
        [1, "010101001001", "平整场地", "土壤类别：三类土\n施工范围：详图", "m2", 6.25],
        [2, "WB010101011001", "人工清底", "不得填补缺失数量", "m2", None],
        ["合计", None, None, None, None, 6.25],
        ["序号", "项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"],
    ]:
        sheet.append(row)
    other = book.create_sheet("同编码另一个单位工程")
    for row in [["分部分项工程量清单"], ["工程名称：2号楼土建"], ["序号", "项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"], [1, "010101001001", "平整场地", "另一单位工程", "m2", 10]]:
        other.append(row)
    summary = book.create_sheet("汇总表")
    summary.append(["单位工程汇总", "金额"])
    path = tmp_path / "清单.xlsx"
    book.save(path)
    result = analyze_boq(path)
    assert result["summary"]["item_count"] == 3
    assert result["summary"]["bill_sheet_count"] == 2
    first, second, third = result["items"]
    assert first["code"] == "010101001001"
    assert first["section"] == "土石方工程"
    assert first["quantity"] == "6.25"
    assert first["features"] == "土壤类别：三类土\n施工范围：详图"
    assert first["location"] == {"kind": "spreadsheet", "sheet": "分部分项", "row": 5}
    assert second["quantity"] is None
    assert third["unit_project"] == "2号楼土建"
    assert third["id"] != first["id"]


def test_numeric_item_code_uses_excel_number_format_and_formula_without_cache_is_missing(tmp_path):
    from app.adapters.boq import analyze_boq
    book = Workbook()
    sheet = book.active
    sheet.append(["项目编码", "项目名称", "计量单位", "工程量"])
    sheet.append([10101001001, "土方", "m3", "=2*3"])
    sheet.cell(2, 1).number_format = "000000000000"
    path = tmp_path / "formula.xlsx"
    book.save(path)
    result = analyze_boq(path)
    assert result["items"][0]["code"] == "010101001001"
    assert result["items"][0]["quantity"] is None
    assert result["warnings"]
