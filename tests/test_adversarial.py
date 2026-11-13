import json
import math
import numpy as np
import pandas as pd
import pytest
from labledger.db import Store
from labledger.errors import LedgerError
from labledger.exports import import_csv,csv_bytes,filename
from labledger.reporting import project_import,project_export,report_bundle
from labledger.archive import make_archive,replay
from labledger.science import regression,hypothesis,describe,correlation,quality_score

@pytest.mark.parametrize('payload',[b'',b' ',b'x;x\n1;2',b'x,x\n1,2',b'\xff\xff\x00',b'y\nhello',b'x\n"unterminated'])
def test_invalid_csv(payload):
    with pytest.raises(LedgerError): import_csv(payload,['x'])

def test_oversized_upload():
    with pytest.raises(LedgerError): import_csv(b'x'*(20*1024*1024+1),['x'])

@pytest.mark.parametrize('payload',[b'[]',b'null',b'42',b'{}',b'{bad',b'{"format":"LabLedger-V2","datasets":[{}]}'])
def test_malformed_project_no_partial_creation(tmp_path,payload):
    s=Store(tmp_path/'a.db')
    with pytest.raises(LedgerError): project_import(s,payload)
    assert not s.projects()

def test_formula_and_paths():
    frame=pd.DataFrame({'x':['=SUM(1,2)','+cmd','@bad','-2.5','\t=1']})
    output=csv_bytes(frame).decode('utf-8-sig'); assert "'=SUM" in output and "'+cmd" in output and "'@bad" in output
    assert '-2.5' in output and "'-2.5" not in output
    name=filename('../../CON\\file:evil','export','csv'); assert '/' not in name and '\\' not in name and ':' not in name

def test_sql_names_and_deleted_dataset_history(tmp_path):
    s=Store(tmp_path/'a.db'); p=s.create_project("'; DROP TABLE projects; --"); d=s.create_dataset(p,'x',[{'name':'x','type':'数字'}]); s.save_frame(p,d,pd.DataFrame({'x':[1,2,3,4]}))
    package=make_archive(s,p,d,{'y':'x'}); s.delete_dataset(p,d)
    assert len(s.projects())==1 and not s.datasets(p)
    record=next(r for r in s.history(p) if r['kind']=='数字档案'); assert replay(record['payload'])['status']=='一致'
    assert replay(package)['status']=='一致'

def test_empty_one_constant_and_extreme(tmp_path):
    fields=[{'name':'x','type':'数字'}]; s=Store(tmp_path/'a.db'); p=s.create_project('a'); d=s.create_dataset(p,'b',fields)
    with pytest.raises(LedgerError): report_bundle(s,p,d,'empty')
    assert quality_score(s.frame(p,d),fields)['score']==0
    row=describe(pd.DataFrame({'x':[3]})).iloc[0]; assert row['均值']==3 and pd.isna(row['方差'])
    assert pd.isna(correlation(pd.DataFrame({'x':[1]*10,'y':[2]*10})).iloc[0,1])
    assert hypothesis([[1]*8,[1]*8])['status']=='条件不满足'
    with pytest.raises(LedgerError): regression(pd.DataFrame({'x':[1e308,1e307,1e306],'y':[2,3,4]}),['x'],'y')

def test_welch_p_value_independent_quadrature():
    # Independent stdlib Simpson integration of the Student t density (df=14).
    a=np.arange(1,9,dtype=float); b=a+10; result=hypothesis([a,b])
    statistic=10/math.sqrt(6/8+6/8); df=14
    c=math.gamma((df+1)/2)/(math.sqrt(df*math.pi)*math.gamma(df/2))
    def f(x): return c*(1+x*x/df)**(-(df+1)/2)
    n=10000; h=statistic/n
    integral=h/3*(f(0)+f(statistic)+4*sum(f(i*h) for i in range(1,n,2))+2*sum(f(i*h) for i in range(2,n,2)))
    expected=1-2*integral
    assert result['status']=='已计算' and result['statistic']==pytest.approx(-statistic)
    assert result['p']==pytest.approx(expected,abs=1e-11)

def test_duplicate_import_is_explicit_isolated_copy(tmp_path):
    s=Store(tmp_path/'a.db'); p=s.create_project('source'); d=s.create_dataset(p,'data',[{'name':'x','type':'数字'}]); s.save_frame(p,d,pd.DataFrame({'x':[1]}))
    data=json.dumps(project_export(s,p)).encode(); a=project_import(s,data); b=project_import(s,data)
    assert len({p,a,b})==3 and len(s.projects())==3
