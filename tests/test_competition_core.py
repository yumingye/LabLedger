import json
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from labledger.science import clean
from labledger.advanced_charts import build
from labledger.db import Store
from labledger.demo_v2 import load_algorithm_demo

def test_conditional_imputation_and_outlier():
    f=pd.DataFrame({'g':['a']*5+['b']*5,'x':[1,2,None,3,100,100,101,None,102,1000]}); schema=[{'name':'g','type':'文本'},{'name':'x','type':'数字'}]
    out,_=clean(f,schema,{'operation':'中位数填充','column':'x','groups':['g']})
    assert out.x.iloc[2]==2.5 and out.x.iloc[7]==101.5
    marked,_=clean(out,schema,{'operation':'异常值标记','column':'x','groups':['g']})
    assert marked['x异常标记'].eq('候选异常').sum()==2
    assert f.x.isna().sum()==2

def test_mean_curve_not_repeated_measurement_lines():
    fig=build(pd.DataFrame({'x':[1,1,2,2],'y':[2,4,6,8]}),'折线图','x','y')
    assert list(fig.data[0].y)==[3,7]
    matrix=build(pd.DataFrame({'x':[1,2,3],'y':[2,3,4]}),'热力图','x','y')
    assert matrix.layout.xaxis.title.text=='数值指标'

def test_report_staleness_and_unique_archives(tmp_path,monkeypatch):
    path=tmp_path/'db.sqlite3'; monkeypatch.setenv('LABLEDGER_DB',str(path)); s=Store(path); p=load_algorithm_demo(s); d=s.datasets(p)[0]['id']
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run(); app.radio(key='page').set_value('报告中心').run()
    def generate(): next(b for b in app.button if b.label=='生成完整实验报告').click().run()
    generate(); generate(); records=[json.loads(r['payload'])['file'] for r in s.history(p) if r['kind']=='报告导出']
    assert len(set(records))==2
    frame=s.frame(p,d); s.save_frame(p,d,frame.iloc[:10]); app.run()
    with pytest.raises(KeyError): app.session_state[f'report_{p}_{d}']
    assert not app.error
