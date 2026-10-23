from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def add_toc(document: Document) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("目录")
    run.bold = True
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), 'TOC \\o "1-3" \\h \\z \\u')
    paragraph._p.append(field)
    settings = document.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def render_blocks(document: Document, title: str, blocks: list[dict]) -> None:
    document.add_heading(title, level=1)
    for block in blocks:
        if block.get("type") == "table":
            rows = block.get("rows", [])
            if not rows:
                continue
            table = document.add_table(rows=len(rows), cols=max(len(row) for row in rows))
            table.style = "Table Grid"
            for row_index, row in enumerate(rows):
                for column_index, value in enumerate(row):
                    table.cell(row_index, column_index).text = value
        else:
            paragraph = document.add_paragraph(block.get("text", ""))
            if block.get("heading_level"):
                paragraph.style = f"Heading {block['heading_level']}"


def export_docx(path: Path, project_name: str, chapters: list[tuple[str, list[dict]]]) -> None:
    document = Document()
    document.add_heading("技术标审核稿", level=0)
    document.add_paragraph(f"项目名称：{project_name}")
    document.add_paragraph("状态：审核稿；页数与目录页码未验证")
    add_toc(document)
    for title, blocks in chapters:
        render_blocks(document, title, blocks)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)

