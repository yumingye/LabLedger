"""Executable, hashed experiment dossiers and evidence-based diagnostics."""
import hashlib
import json
from datetime import datetime,timezone
import math
import numpy as np
import pandas as pd
from . import __version__
from .errors import LedgerError
from . import science as sc

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str).encode('utf-8')

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()

def serial(frame):
    return json.loads(frame.to_json(orient='records',force_ascii=False,double_precision=15))

def confidence(series,level=.95):
    s=sc.numeric(pd.Series(series)).dropna(); n=len(s)
    result={'n':n,'mean':float(s.mean()) if n else None,'std':float(s.std()) if n>1 else None,'level':level,'lower':None,'upper':None}
    if n<2: return {**result,'status':'样本不足'}
    if not 0<level<1: raise LedgerError('置信水平需在0与1之间。')
    try: from scipy.stats import t
    except ImportError: return {**result,'status':'SciPy不可用'}
    mean=result['mean']; std=result['std']
    if not math.isfinite(mean) or not math.isfinite(std): raise LedgerError('数值范围过大，无法稳定估计置信区间，请缩放单位。')
    margin=float(t.ppf((1+level)/2,n-1)*std/np.sqrt(n))
    return {**result,'lower':mean-margin,'upper':mean+margin,'status':'已计算','assumptions':'独立重复、近似正态的均值t区间；不是单次预测区间，也不证明达到科学目标。'}

def analyse(frame,fields,config):
    data=sc.numbers(frame,fields); result={'description':serial(sc.describe(data))}
    method=config.get('method','pearson'); result['correlation']=sc.correlation(data,method).to_json(orient='split',double_precision=15)
    xs=config.get('xs',[]); y=config.get('y')
    if y:
        if y not in data: raise LedgerError('归档指标不在数值字段中。')
        result['confidence']=confidence(data[y])
    if xs:
        result['regression']=sc.regression(data,xs,y)
    group=config.get('group')
    if group and y:
        result['comparison']=serial(sc.compare(frame,group,y).reset_index())
    return result

def make_archive(store,pid,did,config,chart_config=None):
    ds=store.dataset(pid,did); fields=json.loads(ds['schema_json']); frame=store.frame(pid,did)
    if frame.empty: raise LedgerError('没有数据，不能创建数字档案。')
    versions=store.versions(pid,did)
    source={'fields':fields,'records':frame.to_dict('records')}
    package={'format':'LabLedger-Dossier-1','software_version':__version__,'created_at':datetime.now(timezone.utc).isoformat(),'project_id':pid,'dataset_id':did,'revision':ds['revision'],'original_revision':versions[-1]['revision'] if versions else ds['revision'],'source':source,'source_sha256':digest(source),'pipeline':[{k:v[k] for k in ('revision','operation','parameters','created_at')} for v in reversed(versions)],'config':config,'chart_config':chart_config or {},'metadata':store.metadata(pid),'result':analyse(frame,fields,config)}
    package['version_history']=list(reversed(versions))
    package['archive_sha256']=digest(package)
    store.log(pid,did,'数字档案',package)
    return package

def rerun_cleaning(package):
    versions=package.get('version_history',[])
    if not versions: return {'status':'未保存可执行清洗链','steps':[]}
    frame=None; fields=None; steps=[]
    for version in versions:
        raw=pd.DataFrame(json.loads(version['payload']),columns=[f['name'] for f in json.loads(version['schema_json'])])
        if version['operation']=='数据清洗' and frame is not None:
            frame,fields=sc.clean(frame,fields,json.loads(version['parameters'])); steps.append({'revision':version['revision'],'operation':'重新执行清洗'})
            # Store persists raw cells as strings and missing values as None.
            frame=frame.map(lambda value:None if pd.isna(value) or isinstance(value,str) and not value.strip() else str(value))
            if digest({'fields':fields,'records':frame.to_dict('records')})!=digest({'fields':json.loads(version['schema_json']),'records':raw.to_dict('records')}):
                return {'status':'清洗步骤存在差异','steps':steps,'revision':version['revision']}
        else:
            frame=raw; fields=json.loads(version['schema_json']); steps.append({'revision':version['revision'],'operation':'载入保存的原始/手工/恢复版本'})
    current={'fields':fields,'records':frame.to_dict('records')}
    return {'status':'一致' if digest(current)==package['source_sha256'] else '最终数据存在差异','steps':steps}

def unwrap(payload):
    if isinstance(payload,str): payload=json.loads(payload)
    for _ in range(20):
        if 'imported_history' not in payload: return payload
        payload=json.loads(payload['imported_history']['payload'])
    raise LedgerError('导入历史嵌套过深。')

def differences(before,after,path='',tolerance=1e-9):
    rows=[]
    if isinstance(before,dict) and isinstance(after,dict):
        for key in sorted(set(before)|set(after)): rows.extend(differences(before.get(key),after.get(key),path+'.'+key,tolerance))
    elif isinstance(before,list) and isinstance(after,list):
        if len(before)!=len(after): rows.append({'位置':path,'原值':len(before),'现值':len(after)})
        else:
            for i,(a,b) in enumerate(zip(before,after)): rows.extend(differences(a,b,f'{path}[{i}]',tolerance))
    elif isinstance(before,(int,float)) and isinstance(after,(int,float)):
        if not np.isclose(before,after,rtol=tolerance,atol=tolerance,equal_nan=True): rows.append({'位置':path,'原值':before,'现值':after})
    elif before!=after: rows.append({'位置':path,'原值':str(before),'现值':str(after)})
    return rows

def replay(package):
    package=unwrap(package)
    if package.get('format')!='LabLedger-Dossier-1': raise LedgerError('不支持的数字档案格式。')
    supplied=package.get('archive_sha256'); copy={k:v for k,v in package.items() if k!='archive_sha256'}
    if supplied!=digest(copy) or package.get('source_sha256')!=digest(package['source']): raise LedgerError('档案哈希不匹配，数据或参数可能已变化。')
    source=package['source']; frame=pd.DataFrame(source['records'],columns=[f['name'] for f in source['fields']])
    result=analyse(frame,source['fields'],package['config']); diff=differences(package['result'],result)
    cleaning=rerun_cleaning(package)
    return {'status':'一致' if not diff and cleaning['status']=='一致' else '存在差异','source_sha256':package['source_sha256'],'saved_software':package['software_version'],'current_software':__version__,'tolerance':1e-9,'differences':diff,'cleaning_replay':cleaning,'result':result,'note':'哈希用于完整性检查，不是数字签名。清洗操作从保存的原始版本重新执行；手工录入和版本恢复步骤从保存记录载入，随后重算分析。'}

def diagnose(frame,fields,groups=None):
    groups=groups or []; rows=[]
    for f in fields:
        col=f['name']; missing=frame[col].isna()|frame[col].fillna('').astype(str).str.strip().eq('')
        if missing.any(): rows.append({'字段':col,'位置':'行 '+','.join(str(i+1) for i in np.flatnonzero(missing)[:30]),'方法':'缺失模式统计','依据':f'{int(missing.sum())}/{len(frame)} 单元格缺失','可能原因':'未测量、导出遗漏或录入缺失，需核实','建议':'先核实来源；按相同实验条件填补或保留缺失，不跨组强填'})
        if f['type']!='数字' or col in groups: continue
        for label,subset in (frame.groupby(groups,dropna=False) if groups else [('全部',frame)]):
            s=sc.numeric(subset[col]); mask=sc.outliers(s); valid=s.dropna()
            if mask.any():
                q1,q3=valid.quantile([.25,.75]); iqr=q3-q1
                rows.append({'字段':col,'位置':f'条件{label}；行 '+','.join(str(frame.index.get_loc(i)+1) for i in subset.index[mask][:30]),'方法':'分条件IQR（1.5倍）','依据':f'n={len(valid)}，Q1={q1:.6g}，Q3={q3:.6g}，界限[{q1-1.5*iqr:.6g},{q3+1.5*iqr:.6g}]，候选{int(mask.sum())}个','可能原因':'可能是测量波动、单位问题或有效极端观测；统计异常不等于实验错误','建议':'检查原记录和设备，补充重复测量；默认保留并标记'})
            if len(valid)>=8 and valid.mean()!=0 and valid.std()/abs(valid.mean())>.3:
                rows.append({'字段':col,'位置':f'条件{label}','方法':'变异系数风险阈值0.3（经验规则）','依据':f'n={len(valid)}，均值={valid.mean():.6g}，标准差={valid.std():.6g}，CV={valid.std()/abs(valid.mean()):.4g}','可能原因':'可能混合不同条件、设备噪声或均值接近0','建议':'分层核对实验条件，确认该指标CV是否有解释意义'})
    report=sc.quality_score(frame,fields)
    for issue in report['issues']:
        if '类型' in issue['问题'] or '范围' in issue['问题'] or '日期' in issue['问题']:
            rows.append({'字段':issue['字段'],'位置':f'行{issue["行号"]}','方法':issue['问题'],'依据':issue['原值'],'可能原因':'字段定义、单位或录入可能不一致','建议':'核实并预览转换；保留原版本'})
    return rows[:300]

def plan_comparison(frame,metric,target,direction,tolerance=0,groups=None):
    if not math.isfinite(target) or not math.isfinite(tolerance) or tolerance<0: raise LedgerError('目标与容差必须为有限数，容差不能为负。')
    rows=[]
    for label,subset in (frame.groupby(groups,dropna=False) if groups else [('全部',frame)]):
        ci=confidence(subset[metric]); mean=ci['mean']
        if mean is None: status='无有效观测'
        else:
            meets=mean<=target+tolerance if direction=='不高于' else mean>=target-tolerance if direction=='不低于' else abs(mean-target)<=tolerance
            status='当前样本均值符合预设' if meets else '当前样本均值偏离预设'
        rows.append({'条件':str(label),'指标':metric,'目标':target,'方向':direction,'容差':tolerance,'实际均值':mean,'偏差':mean-target if mean is not None else None,'n':ci['n'],'95%CI下界':ci['lower'],'95%CI上界':ci['upper'],'描述性对照':status})
    return pd.DataFrame(rows)
