from io import BytesIO
import ezdxf
import pymupdf
from test_material_import import configured_client, project, zip_bytes


def test_archive_site_labels_and_context_path_guide_site_analysis(tmp_path,monkeypatch):
    files=[]
    for name in ['室外甲','室外乙','室外丙','D-site']:
        doc=ezdxf.new();doc.units=6
        doc.modelspace().add_text('现状水泥路')
        doc.modelspace().add_text('养鸡场' if name=='D-site' else name)
        doc.modelspace().add_text('苗圃' if name=='D-site' else name+'说明')
        p=tmp_path/(name+'.dxf');doc.saveas(p)
        files.append((('现状地形/' if name=='D-site' else '')+p.name,p.read_bytes()))
    with configured_client(tmp_path) as client:
        pid=project(client)
        root=client.post(f'/api/projects/{pid}/documents',files={'file':('资料.zip',zip_bytes(files))}).json()
        client.post(f"/api/documents/{root['id']}/parse")
        async def complete(self,system,payload,schema):
            assert any(d['filename']=='D-site.dxf' for d in payload['drawings'])
            assert {'养鸡场','苗圃'}.issubset({e['text'] for e in payload['evidence']})
            evidence=next(e for e in payload['evidence'] if e['text']=='养鸡场')
            return schema(summary='周边设施需核实',findings=[{'title':'既有设施协调','observation':'图中标注养鸡场','impact':'运输及防护界面需核实','recommendation':'核实权属、使用状态与保护范围','uncertainty':'尚未踏勘','source_block_ids':[evidence['id']]}],limitations=[])
        monkeypatch.setattr('app.adapters.deepseek.DeepSeekClient.complete_json',complete)
        r=client.post(f'/api/projects/{pid}/site-analysis')
        assert r.status_code==200,r.text


def test_unread_supplement_is_explicit_in_site_analysis_coverage(tmp_path,monkeypatch):
    from test_site_analysis import drawing
    with configured_client(tmp_path) as client:
        pid=project(client);drawing(client,pid,tmp_path)
        p=tmp_path/'扫描答疑.pdf'
        with pymupdf.open() as doc:
            doc.new_page();doc.save(p)
        item=client.post(f'/api/projects/{pid}/documents',files={'file':(p.name,p.read_bytes())}).json()
        client.post(f"/api/documents/{item['id']}/parse")
        async def complete(self,system,payload,schema):
            assert any(d['filename']=='扫描答疑.pdf' for d in payload['unread_documents'])
            e=payload['evidence'][0]
            return schema(summary='有限资料分析',findings=[{'title':'周边待核实','observation':'图纸有水塘文字','impact':'临水作业条件待核实','recommendation':'现场踏勘','uncertainty':'未读答疑不得视为已核对','source_block_ids':[e['id']]}],limitations=[])
        monkeypatch.setattr('app.adapters.deepseek.DeepSeekClient.complete_json',complete)
        r=client.post(f'/api/projects/{pid}/site-analysis')
        assert r.status_code==200,r.text
        assert any('扫描答疑.pdf' in s for s in r.json()['limitations'])


def test_partial_pdf_text_coverage_is_visible_even_if_model_omits_it(tmp_path,monkeypatch):
    from test_site_analysis import drawing
    with configured_client(tmp_path) as client:
        pid=project(client);drawing(client,pid,tmp_path)
        p=tmp_path/'混合页答疑.pdf'
        with pymupdf.open() as doc:
            doc.new_page().insert_text((30,30),'Readable page')
            doc.new_page();doc.save(p)
        item=client.post(f'/api/projects/{pid}/documents',files={'file':(p.name,p.read_bytes())}).json();client.post(f"/api/documents/{item['id']}/parse")
        async def complete(self,system,payload,schema):
            e=payload['evidence'][0]
            return schema(summary='有限资料分析',findings=[{'title':'周边条件','observation':'现状图标注','impact':'待核实作业条件','recommendation':'现场核实','uncertainty':'资料覆盖有限','source_block_ids':[e['id']]}],limitations=[])
        monkeypatch.setattr('app.adapters.deepseek.DeepSeekClient.complete_json',complete)
        r=client.post(f'/api/projects/{pid}/site-analysis')
        assert r.status_code==200
        assert any('混合页答疑.pdf' in s and '1/2' in s for s in r.json()['limitations'])
