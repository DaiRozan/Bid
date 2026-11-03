from pypdf import PdfReader
import pymupdf


def extract_pdf(path: str) -> list[tuple[str, dict]]:
    # CAD-exported PDFs can exceed pypdf's graphics-token budget even when
    # their text is small. MuPDF extracts text without building that token list.
    try:
        with pymupdf.open(path) as document:
            return [(text, {"kind":"pdf_page", "page":number}) for number,page in enumerate(document,1) if (text := page.get_text("text",sort=True).strip())]
    except (RuntimeError,ValueError):
        return extract_with_pypdf(path)


def extract_with_pypdf(path: str) -> list[tuple[str, dict]]:
    reader = PdfReader(path)
    blocks: list[tuple[str, dict]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            blocks.append((text, {"kind": "pdf_page", "page": page_number}))
    return blocks

