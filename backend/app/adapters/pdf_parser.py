from pypdf import PdfReader


def extract_pdf(path: str) -> list[tuple[str, dict]]:
    reader = PdfReader(path)
    blocks: list[tuple[str, dict]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            blocks.append((text, {"kind": "pdf_page", "page": page_number}))
    return blocks

