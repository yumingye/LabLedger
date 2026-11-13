import copy
import json
import pandas as pd
import pytest
from labledger.archive import confidence,make_archive,replay,digest,diagnose,plan_comparison
from labledger.db import Store
from labledger.demo_v2 import load_algorithm_demo,FIELDS
from labledger.science import clean
from labledger.errors import LedgerError
from labledger.reporting import project_export,project_import

def test_t_confidence_independent_reference():
    result=confidence([1,2,3,4,5]); assert result['mean']==3
    assert result['lower']==pytest.approx(1.0367568385)
    assert result['upper']==pytest.approx(4.9632431615)
    assert confidence([2])['status']=='样本不足'

def test_archive_reruns_pipeline_and_isolates_live_changes(tmp_path):
    s=Store(tmp_path/'d.db'); p=load_algorithm_demo(s); d=s.datasets(p)[0]['id']
    for op in ['删除重复行','中位数填充','异常值标记']:
        params={'operation':op,'column':'运行时间','groups':['算法名称','输入规模']}
        fields=json.loads(s.dataset(p,d)['schema_json']); changed,schema=clean(s.frame(p,d),fields,params)
        s.save_frame(p,d,changed,operation='数据清洗',parameters=params,fields=schema)
    package=make_archive(s,p,d,{'xs':['输入规模'],'y':'运行时间','group':'算法名称'})
    assert replay(package)['status']=='一致'
    assert replay(package)['cleaning_replay']['status']=='一致'
    s.save_frame(p,d,s.frame(p,d).iloc[:5])
    assert replay(package)['status']=='一致'
    imported=project_import(s,json.dumps(project_export(s,p),ensure_ascii=False).encode())
    record=next(r for r in s.history(imported) if r['kind']=='数字档案')
    assert replay(record['payload'])['status']=='一致'
    bad=copy.deepcopy(package); bad['source']['records'][0]['运行时间']='999'
    with pytest.raises(LedgerError): replay(bad)
    changed=copy.deepcopy(package); changed['result']['description'][0]['均值']+=1
    changed['archive_sha256']=digest({k:v for k,v in changed.items() if k!='archive_sha256'})
    outcome=replay(changed); assert outcome['status']=='存在差异'; assert outcome['differences']

def test_diagnostics_locations_and_conditions():
    frame=pd.DataFrame({'组':['a']*10+['b']*10,'值':[1]*9+[100]+[1000]*10}); fields=[{'name':'组','type':'文本'},{'name':'值','type':'数字'}]
    findings=diagnose(frame,fields,['组'])
    iqr=next(r for r in findings if 'IQR' in r['方法'])
    assert '10' in iqr['位置'] and '候选1个' in iqr['依据'] and '不等于实验错误' in iqr['可能原因']
    frame.loc[0,'值']=None
    assert any('1/20' in f['依据'] for f in diagnose(frame,fields,['组']))

def test_plan_current_sample_only():
    frame=pd.DataFrame({'g':['A']*5,'x':[1,2,3,4,5]})
    result=plan_comparison(frame,'x',4,'不高于',groups=['g'])
    assert result.iloc[0]['偏差']==-1
    assert result.iloc[0]['描述性对照']=='当前样本均值符合预设'
    assert result.iloc[0]['95%CI上界']>4
    with pytest.raises(LedgerError): plan_comparison(frame,'x',float('inf'),'不高于')
