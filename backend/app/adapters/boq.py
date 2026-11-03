"""BOQ rows retain their original engineering scope and cell locations."""
from decimal import Decimal
import hashlib
from pathlib import Path
import re


def cell_text(value):
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return format(Decimal(str(value)).normalize(), "f")
    return str(value).strip()


def workbook_rows(path):
    if path.suffix.lower() == ".xls":
        import xlrd
        book = xlrd.open_workbook(path, on_demand=True)
        try:
            for sheet in book.sheets():
                yield sheet.name, [sheet.row_values(row) for row in range(sheet.nrows)], {}
        finally:
            book.release_resources()
    else:
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=True)
        formulas = load_workbook(path, read_only=True, data_only=False)
        try:
            for sheet in book:
                rows = []
                missing_formulas = {}
                for row_number, (row, original) in enumerate(zip(sheet.iter_rows(), formulas[sheet.title].iter_rows()), 1):
                    values = []
                    for col, (cell, expression) in enumerate(zip(row, original)):
                        value = cell.value
                        if isinstance(value, (int, float)) and re.fullmatch(r"0{8,}", cell.number_format or ""):
                            value = str(int(value)).zfill(len(cell.number_format))
                        values.append(value)
                        if expression.data_type == "f" and value is None:
                            missing_formulas[(row_number, col)] = True
                    rows.append(values)
                yield sheet.title, rows, missing_formulas
        finally:
            book.close()
            formulas.close()


def analyze_boq(path: Path) -> dict:
    items, sheets, warnings, previews = [], [], [], []
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    aliases = {"code": {"项目编码", "清单编码"}, "name": {"项目名称", "清单名称"}, "features": {"项目特征描述", "项目特征"}, "unit": {"计量单位", "单位"}, "quantity": {"工程量", "数量"}}
    for sheet_name, rows, missing_formulas in workbook_rows(path):
        sheets.append({"name": sheet_name, "rows": len(rows)})
        header = None
        header_row = 0
        for index, row in enumerate(rows):
            normalized = [re.sub(r"\s+", "", cell_text(c)) for c in row]
            columns = {key: next((i for i, text in enumerate(normalized) if text in values), None) for key, values in aliases.items()}
            if all(columns[key] is not None for key in ["code", "name", "quantity"]):
                header, header_row = columns, index
                break
        if header is None:
            # Drawing indices/cover sheets remain readable evidence too.
            for row_number, row in enumerate(rows[:2000], 1):
                text = " | ".join(cell_text(v) for v in row if cell_text(v))
                if text:
                    previews.append({"text": text, "location": {"kind": "spreadsheet", "sheet": sheet_name, "row": row_number}})
            continue
        unit_project = ""
        for row in rows[:header_row]:
            for cell in row:
                match = re.search(r"(?:工程名称|项目名称)\s*[:：]\s*(.+)", cell_text(cell))
                if match:
                    unit_project = match[1].strip()
        section = ""
        last_item = None
        before = len(items)
        for index in range(header_row + 1, len(rows)):
            row = rows[index]
            scope = next((m[1].strip() for cell in row if (m := re.search(r"(?:工程名称|项目名称)\s*[:：]\s*(.+)", cell_text(cell)))), None)
            if scope:
                if scope != unit_project:
                    unit_project, section, last_item = scope, "", None
                continue
            normalized = [re.sub(r"\s+", "", cell_text(c)) for c in row]
            columns = {key: next((i for i, text in enumerate(normalized) if text in values), None) for key, values in aliases.items()}
            if all(columns[key] is not None for key in ["code", "name", "quantity"]):
                header = columns
                continue
            def value(key):
                col = header[key]
                return cell_text(row[col]) if col is not None and col < len(row) else ""
            code, name, quantity = value("code"), value("name"), value("quantity")
            if not code and not name and not quantity and value("features") and last_item is not None:
                last_item["features"] += "\n" + value("features")
                last_item["location"].setdefault("continuation_rows", []).append(index + 1)
                continue
            if not name or name == "项目名称":
                continue
            # Numeric codes are sometimes stored without their leading zero.
            if code.isdigit() and len(code) == 11:
                code = code.zfill(12)
            if not re.fullmatch(r"(?:[A-Za-z]{0,5})?\d{12,}", code):
                if name and code and len(code) < 12 and not quantity and "合计" not in name:
                    section = name
                    last_item = None
                continue
            location = {"kind": "spreadsheet", "sheet": sheet_name, "row": index + 1}
            item_id = "boq-" + hashlib.sha256(f"{digest}:{sheet_name}:{index+1}".encode()).hexdigest()[:24]
            item = {"id": item_id, "unit_project": unit_project or sheet_name, "section": section, "code": code, "name": name, "features": value("features"), "unit": value("unit"), "quantity": quantity or None, "location": location}
            items.append(item)
            last_item = item
            if not quantity:
                cause = "公式缺少计算缓存" if missing_formulas.get((index + 1, header["quantity"])) else "原表工程量为空"
                warnings.append(f"{sheet_name} 第{index+1}行：{cause}，保留空值")
        sheets[-1]["item_count"] = len(items) - before
    return {"summary": {"sheet_count": len(sheets), "bill_sheet_count": sum(s.get("item_count", 0) > 0 for s in sheets), "item_count": len(items)}, "items": items, "sheets": sheets, "warnings": warnings, "text_records": previews}
