from pathlib import Path
import json
from streamlit.testing.v1 import AppTest
from labledger.db import Store
from labledger.demo_v2 import load_algorithm_demo
from labledger.reporting import project_import,project_export,report_bundle

def test_imported_conclusion_and_analysis_remain_usable(tmp_path,monkeypatch):
    path=tmp_path/'test.db'; monkeypatch.setenv('LABLEDGER_DB',str(path)); s=Store(path); p=load_algorithm_demo(s); d=s.datasets(p)[0]['id']
    s.log(p,d,'实验结论',{'draft':'测试结论'}); s.log(p,d,'分析快照',{'dataset_revision':1,'y':'运行时间','xs':['输入规模'],'correlation':'pearson'})
    imported=project_import(s,json.dumps(project_export(s,p),ensure_ascii=False).encode()); newd=s.datasets(imported)[0]['id']
    assert len(report_bundle(s,imported,newd,'测试结论')['zip'])>0
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run(); app.radio(key='page').set_value('报告中心').run()
    assert not app.error and not app.exception
    assert any(t.value=='测试结论' for t in app.text_area)
