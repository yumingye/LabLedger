import io
import json
import sqlite3
import zipfile
import sys
import numpy as np
import pandas as pd
import pytest
from labledger.db import Store
from labledger.errors import LedgerError
from labledger.science import clean,describe,correlation,regression,hypothesis,quality_score,outliers,insights,compare,temporal
from labledger.demo_v2 import load_algorithm_demo,algorithm_frame,FIELDS
from labledger.advanced_charts import KINDS,build,static
from labledger.reporting import report_bundle,project_export,project_import

@pytest.fixture
def demo(tmp_path):
    s=Store(tmp_path/'v2.db'); p=load_algorithm_demo(s); d=s.datasets(p)[0]['id']; return s,p,d

def test_migration(tmp_path):
    path=tmp_path/'old.db'
    with sqlite3.connect(path) as db:
        db.executescript("CREATE TABLE projects(id INTEGER PRIMARY KEY,name TEXT,created_at TEXT,updated_at TEXT); CREATE TABLE datasets(id INTEGER PRIMARY KEY,project_id INTEGER,name TEXT,schema_json TEXT,revision INTEGER DEFAULT 0); CREATE TABLE records(id INTEGER PRIMARY KEY,dataset_id INTEGER,payload TEXT); INSERT INTO projects VALUES(1,'old','a','b');")
        db.execute('INSERT INTO datasets VALUES(1,1,?,?,1)',('data',json.dumps([{'name':'x','type':'数字'}])))
        db.execute('INSERT INTO records VALUES(1,1,?)',(json.dumps({'x':'42'}),))
    s=Store(path); assert s.frame(1,1).iloc[0,0]=='42'; assert len(s.versions(1,1))==1
    assert len(Store(path).versions(1,1))==1

def test_meta_isolation_restart(demo):
    s,p,d=demo; p2=s.create_project('other'); s.set_metadata(p2,{'实验目标':'隔离'})
    assert s.metadata(p2)['实验目标']=='隔离'; assert s.metadata(p)!=s.metadata(p2)
    with pytest.raises(LedgerError): s.versions(p2,d)
    assert len(Store(s.path).frame(p,d))==121

@pytest.mark.parametrize('operation',['删除缺失行','均值填充','中位数填充','众数填充','指定值填充','删除重复行','异常值标记','数值转换','日期转换','排序','筛选','分组均值','标准化','归一化','派生字段'])
def test_clean_operations(operation):
    frame=pd.DataFrame({'x':['1','2',None,'4','4'],'y':[2,3,4,5,5],'g':['a','a','b','b','b']}); fields=[{'name':'x','type':'数字'},{'name':'y','type':'数字'},{'name':'g','type':'文本'}]
    out,fs=clean(frame,fields,{'operation':operation,'column':'g' if operation=='分组均值' else 'x','value':'1','other':'y','name':'derived','operator':'+'})
    assert list(out.columns)==[f['name'] for f in fs]
    assert frame.x.isna().sum()==1
    if operation in ('均值填充','中位数填充','众数填充','指定值填充'): assert not out.x.isna().any()
    if operation=='删除重复行': assert len(out)==4

def test_outlier_confirmation():
    s=pd.Series([1]*20+[100]); assert outliers(s).sum()==1; assert outliers(s,'3σ').sum()==1
    with pytest.raises(LedgerError): clean(pd.DataFrame({'x':s}),[{'name':'x','type':'数字'}],{'operation':'异常值过滤','column':'x'})

def test_versions(demo):
    s,p,d=demo; old=s.versions(p,d)[0]; rev=s.dataset(p,d)['revision']; frame=s.frame(p,d)
    changed,fields=clean(frame,FIELDS,{'operation':'异常值标记','column':'运行时间'})
    s.save_frame(p,d,changed,rev,'数据清洗',{'operation':'异常值标记'},fields)
    assert len(s.frame(p,d).columns)==8
    s.restore_version(p,d,old['id'],rev+1); assert len(s.frame(p,d).columns)==7
    assert len(s.versions(p,d))>=3
    with pytest.raises(LedgerError): s.save_frame(p,d,frame,rev)

def test_describe():
    row=describe(pd.DataFrame({'x':[1,2,3,4,5]})).iloc[0]
    assert row['均值']==3 and row['方差']==2.5 and row['四分位距']==2
    assert row['样本量']==5 and row['极差']==4

def test_correlation_regression():
    x=np.arange(10,dtype=float); frame=pd.DataFrame({'x':x,'y':2*x+3})
    assert correlation(frame).iloc[0,1]==pytest.approx(1)
    assert correlation(frame,'spearman').iloc[0,1]==pytest.approx(1)
    result=regression(frame,['x'],'y'); assert result['coefficients']==pytest.approx([3,2]); assert result['r2']==1
    rng=np.random.default_rng(9); z=rng.normal(size=10); frame['z']=z; frame['y']=2*x+4*z+3
    assert regression(frame,['x','z'],'y')['coefficients']==pytest.approx([3,2,4])
    with pytest.raises(LedgerError): regression(frame.head(2),['x'],'y')
    with pytest.raises(LedgerError): regression(pd.DataFrame({'x':[1]*10,'y':x}),['x'],'y')

def test_hypothesis_boundaries():
    assert hypothesis([[1],[2]])['status']=='样本不足'
    assert hypothesis([[1]*10,[2]*10])['status']=='条件不满足'
    rng=np.random.default_rng(5); a=rng.normal(size=100); b=rng.normal(size=100)+2
    result=hypothesis([a,b]); assert result['status']=='已计算'; assert result['p']<.05
    assert hypothesis([a,b[:-1]],'配对样本t检验')['status']=='条件不满足'
    assert hypothesis([a,a+.5],'配对样本t检验')['status'] in ('已计算','条件不满足')
    assert hypothesis([a,b,rng.normal(size=100)+4],'ANOVA')['status']=='已计算'

def test_ai_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules,'scipy',None)
    assert hypothesis([[1],[2]])['status']=='不可用'
    result=insights(algorithm_frame(),FIELDS)
    assert result['source']=='本地统计规则引擎（非大模型）'; assert 'n=' in result['draft']

def test_quality_compare_trend():
    frame=algorithm_frame(); q=quality_score(frame,FIELDS); assert 0<=q['score']<100 and q['missing']==1
    assert quality_score(pd.DataFrame(columns=frame.columns),FIELDS)['score']==0
    table=compare(frame,'算法名称','运行时间'); assert len(table)==3; assert table['count'].sum()==120
    data,cycle=temporal(frame,'时间戳','运行时间'); assert len(data)==120 and '移动平均' in data

@pytest.mark.parametrize('kind',KINDS)
def test_advanced_exports(kind):
    frame=algorithm_frame().dropna(); frame=frame[frame['运行时间']<9000]
    assert len(build(frame,kind,'输入规模','运行时间','算法名称').data)>0
    assert static(frame,kind,'输入规模','运行时间','算法名称').startswith(b'\x89PNG')
    assert b'<svg' in static(frame,kind,'输入规模','运行时间','算法名称',fmt='svg')
    assert 'plotly' in build(frame,kind,'输入规模','运行时间').to_html()

def test_report_and_roundtrip(demo,tmp_path):
    s,p,d=demo; s.log(p,d,'分析快照',{'dataset_revision':1,'xs':['输入规模'],'y':'运行时间'})
    bundle=report_bundle(s,p,d,'<script>alert(1)</script>实验草稿')
    assert b'<script>alert(1)</script>' not in bundle['html']
    with zipfile.ZipFile(io.BytesIO(bundle['zip'])) as z:
        assert {'report.html','report.md','data.csv','statistics.csv','summary.png','project.json'}<=set(z.namelist()); assert z.testzip() is None
        new=project_import(s,z.read('project.json'))
    assert len(s.frame(new,s.datasets(new)[0]['id']))==121
    assert s.metadata(new)==s.metadata(p)
    backup=tmp_path/'backup.db'; s.backup(backup); recovered=Store(backup)
    assert recovered.history(p)==s.history(p); assert recovered.versions(p,d)==s.versions(p,d)
    s.rename_project(new,'副本'); s.delete_project(new); assert all(pr['id']!=new for pr in s.projects())

def test_bad_import(demo):
    s,_,_=demo
    with pytest.raises(LedgerError): project_import(s,b'{bad')
    assert len(s.projects())==1
