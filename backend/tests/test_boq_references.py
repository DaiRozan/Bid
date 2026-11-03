from io import BytesIO
from openpyxl import load_workbook
import pytest
from test_material_import import configured_client, project
from test_review_regressions import boq_bytes, upload
from test_site_analysis import drawing


@pytest.mark.parametrize('quantity,conflict',[(6,False),(8,True)])
def test_control_price_cross_checks_instead_of_duplicating_tender_boq(tmp_path,quantity,conflict):
    with configured_client(tmp_path) as client:
        pid=project(client)
        original=upload(client,pid,'招标清单.xlsx',boq_bytes())
        book=load_workbook(BytesIO(boq_bytes()));sheet=book.active
        sheet.cell(3,5,quantity);sheet.cell(3,6,100)
        data=BytesIO();book.save(data)
        reference=upload(client,pid,'控制价.xlsx',data.getvalue())
        result=client.get(f'/api/projects/{pid}/fact-library').json()
        assert result['fact_count']==1
        assert result['facts'][0]['attributes']['quantity']=='6'
        assert result['boq_cross_check']['compared']==1
        assert result['boq_cross_check']['conflicts']==int(conflict)
        assert any('控制价' in i['message'] for i in result['issues']) == conflict
        if not conflict:
            assert len(result['facts'][0]['source_block_ids'])==2


def test_site_analysis_receives_authoritative_boq_quantities_with_evidence(tmp_path,monkeypatch):
    with configured_client(tmp_path) as client:
        pid=project(client)
        upload(client,pid,'招标清单.xlsx',boq_bytes());drawing(client,pid,tmp_path)
        async def complete(self,system,payload,schema):
            item=payload['adopted_boq'][0]
            assert '工程量：6 m2' in item['value']
            assert set(item['source_block_ids']).issubset({e['id'] for e in payload['evidence']})
            return schema(summary='清单与图纸共同核对',findings=[{'title':'场地平整','observation':'清单为6 m2','impact':'需核对对应范围','recommendation':'按清单范围组织','uncertainty':'现场未复测','source_block_ids':item['source_block_ids']}],limitations=[])
        monkeypatch.setattr('app.adapters.deepseek.DeepSeekClient.complete_json',complete)
        response=client.post(f'/api/projects/{pid}/site-analysis')
        assert response.status_code==200,response.text
        fact=client.get(f'/api/projects/{pid}/fact-library').json()['facts'][0]
        r=client.post(f'/api/projects/{pid}/fact-library/adoptions',json={'target_id':fact['id'],'value':'8 m2','reason':'重新核对采用量','source_block_ids':fact['source_block_ids']})
        assert r.status_code==201
        assert client.get(f'/api/projects/{pid}/site-analysis').json()['stale']
