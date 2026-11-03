import pymupdf
from pypdf._page import PageObject
from pypdf.errors import LimitReachedError
from app.adapters.pdf_parser import extract_pdf


def test_pdf_text_and_page_locations_survive_vector_stream_parser_limit(tmp_path,monkeypatch):
    path=tmp_path/'drawing.pdf'
    with pymupdf.open() as doc:
        doc.new_page().insert_text((30,30),'SITE ROAD')
        doc.new_page().insert_text((30,30),'DRAIN OUTLET')
        doc.save(path)
    def limit(*args,**kwargs):
        raise LimitReachedError('Reached maximum number of tokens per stream.')
    monkeypatch.setattr(PageObject,'extract_text',limit)
    blocks=extract_pdf(str(path))
    assert [(text,loc['page']) for text,loc in blocks]==[('SITE ROAD',1),('DRAIN OUTLET',2)]
