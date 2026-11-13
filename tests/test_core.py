from io import BytesIO
import json
import subprocess
import sys
import pandas as pd
import pytest
from PIL import Image
from labledger.db import Store
from labledger.validation import quality,validate_schema,valid_date,valid_number
from labledger.analysis import statistics,trend,recommendations
from labledger.charts import ChartConfig,plot,png
from labledger.exports import import_csv,csv_bytes,raw_bytes,filename
from labledger.errors import LedgerError
from labledger.demo import load_demo

def sample():
    return pd.DataFrame({'时间':['0','1','2','3'], '测量':['1','3','5','7'], '组':['甲']*4,'日期':['2026-11-01']*4})

def test_project_crud_and_times(dataset):
    s,p,d=dataset
    before=s.projects()[0]
    s.rename_project(p,'改名实验')
    assert s.projects()[0]['name']=='改名实验'
    assert s.projects()[0]['updated_at']>before['updated_at']
    s.delete_project(p)
    assert not s.projects() and not s.datasets(p)

def test_record_crud_and_persistence(dataset):
    s,p,d=dataset
    frame=sample()
    s.save_frame(p,d,frame)
    frame.loc[0,'测量']='9'; s.save_frame(p,d,frame)
    s.save_frame(p,d,frame.iloc[:-1])
    recovered=Store(s.path).frame(p,d)
    assert len(recovered)==3 and recovered.iloc[0]['测量']=='9'
    result=subprocess.check_output([sys.executable,'-c',"from labledger.db import Store; import sys; print(len(Store(sys.argv[1]).frame(1,1)))",str(s.path)],text=True)
    assert result.strip()=='3'

def test_project_isolation(dataset,fields):
    s,p,d=dataset; other=s.create_project('隔离实验')
    od=s.create_dataset(other,'独立表',fields)
    s.save_frame(p,d,sample())
    assert s.frame(other,od).empty
    with pytest.raises(LedgerError): s.frame(other,d)
    with pytest.raises(LedgerError): s.save_frame(other,d,sample())
    s.delete_project(other)
    assert len(s.frame(p,d))==4

def test_optimistic_lock_and_atomicity(dataset):
    s,p,d=dataset
    s.save_frame(p,d,sample(),0)
    with pytest.raises(LedgerError): s.save_frame(p,d,sample().iloc[:1],0)
    assert len(s.frame(p,d))==4

def test_concurrent_stale_writers(dataset):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    s,p,d=dataset
    barrier=Barrier(2)
    def write(value):
        frame=sample();frame.loc[0,'测量']=value
        barrier.wait(timeout=5)
        try:
            s.save_frame(p,d,frame,revision=0)
            return True
        except LedgerError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(write,['10','20']))==1
    assert len(s.frame(p,d))==4 and s.dataset(p,d)['revision']==1

@pytest.mark.parametrize('name',['','  ','x'*101])
def test_invalid_name(dataset,name):
    with pytest.raises(LedgerError): dataset[0].create_project(name)

def test_schema_and_columns(dataset):
    for fields in [[],[{'name':'x','type':'错误'}],[{'name':'x','type':'数字','min':2,'max':1}], [{'name':'x','type':'文本'}]*2]:
        with pytest.raises(LedgerError):validate_schema(fields)
    with pytest.raises(LedgerError):dataset[0].save_frame(dataset[1],dataset[2],pd.DataFrame({'错列':[1]}))

@pytest.mark.parametrize('encoding',['utf-8-sig','gb18030'])
def test_csv_import(encoding):
    frame=sample()
    assert import_csv(frame.to_csv(index=False).encode(encoding),list(frame)).equals(frame)

def test_csv_invalid():
    for raw in [b'',b'a,a\n1,2',b'a\n1','时间\n1,2'.encode('utf-8')]:
        with pytest.raises(LedgerError):import_csv(raw,['时间'])

def test_exports_chinese_and_raw():
    f=sample();f.loc[0,'组']='=1+1'
    result=csv_bytes(f)
    assert result.startswith(b'\xef\xbb\xbf') and "'=1+1" in result.decode('utf-8-sig')
    assert json.loads(raw_bytes(f,[]))['records'][0]['组']=='=1+1'
    assert '中文实验' in filename('中文实验','数据','csv')

def test_quality_all_rules(fields):
    frame=sample()
    frame.loc[0,'时间']='-1';frame.loc[1,'测量']='错误';frame.loc[2,'日期']='2026-02-30';frame.loc[3,'组']=''
    frame=pd.concat([frame,frame.iloc[[0]]],ignore_index=True)
    report=quality(frame,fields)
    kinds={i['问题'] for i in report['issues']}
    assert {'缺失值','重复数据','数字类型错误','超出设定范围','日期格式错误（应为 YYYY-MM-DD）'}<=kinds
    assert report['duplicates']==2 and report['missing']==1
    assert report['completeness']==95

def test_iqr(fields):
    frame=pd.DataFrame({'测量':[1,2,2,3,2,2,100]})
    report=quality(frame,[fields[1]])
    assert any(i['原值']=='100' and 'IQR' in i['问题'] for i in report['issues'])

@pytest.mark.parametrize('value',['inf','NaN','-inf','text',True])
def test_invalid_numeric(value):assert not valid_number(value)

def test_dates():
    assert valid_date('2024-02-29')
    assert not valid_date('2026-02-29') and not valid_date('2026-1-1')

def test_statistics(fields):
    result=statistics(sample(),fields).set_index('字段').loc['测量']
    assert result['均值']==4 and result['中位数']==4
    assert result['最小值']==1 and result['最大值']==7
    assert result['方差']==pytest.approx(20/3)
    assert result['标准差']==pytest.approx((20/3)**.5)
    f=sample();f.loc[0,'测量']='';f.loc[1,'测量']='错误'
    result=statistics(f,fields).set_index('字段').loc['测量']
    assert result['缺失值']==1 and result['无效或缺失']==2

def test_trend():
    result=trend(sample(),'时间','测量')
    assert result['slope']==pytest.approx(2) and result['intercept']==pytest.approx(1)
    assert result['r2']==pytest.approx(1) and result['rate_percent']==600
    f=sample();f['时间']='1'
    assert trend(f,'时间','测量') is None
    f['时间']=['0','1','2','3'];f['测量']=['0','2','4','6']
    assert trend(f,'时间','测量')['rate_percent'] is None

@pytest.mark.parametrize('kind',['折线图','柱状图','散点图'])
def test_charts_and_png(kind):
    c=ChartConfig('时间','测量',kind=kind,group='组',numeric_x=True,fit=kind!='柱状图',width=800,height=400,title='中文实验')
    fig=plot(sample(),c)
    assert len(fig.data)>=1
    blob=png(sample(),c)
    assert blob.startswith(b'\x89PNG')
    assert Image.open(BytesIO(blob)).size==(800,400)

def test_date_chart():
    frame=sample();frame['日期']=['2026-11-01','2026-11-02','2026-11-03','2026-11-04']
    c=ChartConfig('日期','测量',date_x=True,fit=True)
    assert len(plot(frame,c).data)==2
    assert png(frame,c).startswith(b'\x89PNG')

def test_empty_and_single(fields):
    empty=sample().iloc[:0]
    assert quality(empty,fields)['completeness']==0
    assert len(statistics(empty,fields))==2
    assert all(len(trace.x)==0 for trace in plot(empty,ChartConfig('时间','测量')).data)
    assert png(empty,ChartConfig('时间','测量')).startswith(b'\x89PNG')
    assert pd.isna(statistics(sample().iloc[:1],fields).iloc[0]['标准差'])

def test_dashboard_restore_and_demo(tmp_path):
    store=Store(tmp_path/'demo.db');pid=load_demo(store)
    config=store.dashboard(pid)
    assert len(config['charts'])==3
    config['columns']=3;config['charts'].reverse();store.save_dashboard(pid,config)
    assert Store(store.path).dashboard(pid)==config
    did=store.datasets(pid)[0]['id'];frame=store.frame(pid,did)
    assert len(frame)==43
    fields=json.loads(store.dataset(pid,did)['schema_json'])
    assert quality(frame,fields)['issues']
    assert len(recommendations(frame,fields,quality(frame,fields)))>=3
