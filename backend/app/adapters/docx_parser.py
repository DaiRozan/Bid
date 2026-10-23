from docx import Document


def extract_docx(path: str) -> list[tuple[str, dict]]:
    document = Document(path)
    blocks: list[tuple[str, dict]] = []
    for index, paragraph in enumerate(document.paragraphs):
        if paragraph.text.strip():
            blocks.append((paragraph.text.strip(), {"kind": "paragraph", "index": index}))
    for table_index, table in enumerate(document.tables):
        for row_index, row in enumerate(table.rows):
            for column_index, cell in enumerate(row.cells):
                text = cell.text.strip()
                if text:
                    blocks.append(
                        (text, {"kind": "table", "index": table_index, "row": row_index, "column": column_index})
                    )
    return blocks

