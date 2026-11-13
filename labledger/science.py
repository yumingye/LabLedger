"""Deterministic, local statistical workbench; no remote model calls."""
import numpy as np
import pandas as pd
from .analysis import numeric
from .validation import quality
from .errors import LedgerError

def numbers(frame, fields):
    return pd.DataFrame({f['name']:numeric(frame[f['name']]) for f in fields if f['type']=='数字'})

def describe(data):
    rows=[]
    for col in data:
        s=numeric(data[col]).dropna(); n=len(s)
        if not n: continue
        q1,q3=s.quantile([.25,.75])
        rows.append(dict(字段=col,样本量=n,均值=s.mean(),中位数=s.median(),众数=s.mode().iloc[0],最小值=s.min(),最大值=s.max(),极差=s.max()-s.min(),方差=s.var(),标准差=s.std(),Q1=q1,Q3=q3,四分位距=q3-q1,变异系数=s.std()/abs(s.mean()) if s.mean()!=0 else np.nan,偏度=s.skew(),峰度=s.kurt()))
    return pd.DataFrame(rows)

def correlation(data, method='pearson'):
    if method!='spearman': return data.corr(min_periods=3)
    result=pd.DataFrame(np.nan,index=data.columns,columns=data.columns)
    for a in data:
        for b in data:
            if a==b:
                result.loc[a,b]=1.0 if data[a].count()>=3 and data[a].nunique()>1 else np.nan
            else:
                pair=data[[a,b]].dropna()
                if len(pair)>=3: result.loc[a,b]=pair.rank().corr().iloc[0,1]
    return result

def quality_score(frame, fields):
    report=quality(frame,fields)
    affected={(i['行号'],i['字段']) for i in report['issues'] if i['字段']!='整行'}
    cells=frame.size
    penalty=100*len(affected)/cells if cells else 100
    duplicate_penalty=100*int(frame.duplicated().sum())/len(frame) if len(frame) else 0
    report.update(score=round(max(0,100-penalty-duplicate_penalty),2),rule='评分=max(0,100−100×有问题单元格数/总单元格数−100×冗余重复行数/总行数)；同一单元格只扣一次，空表0分。IQR是候选提示，并非测量错误。')
    return report

def outliers(series, method='IQR'):
    s=numeric(series)
    if s.count()<4: return pd.Series(False,index=s.index)
    if method=='IQR':
        q1,q3=s.quantile([.25,.75]); lo,hi=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
    else: lo,hi=s.mean()-3*s.std(),s.mean()+3*s.std()
    return ((s<lo)|(s>hi)).fillna(False)

def clean(frame, fields, params):
    data=frame.copy().replace(r'^\s*$',np.nan,regex=True)
    schema=[dict(f) for f in fields]; op=params['operation']; col=params.get('column')
    if op=='删除缺失行': data=data.dropna()
    elif op=='删除重复行': data=data.drop_duplicates()
    elif op in ('均值填充','中位数填充','众数填充','指定值填充'):
        groups=params.get('groups',[])
        if groups and op in ('均值填充','中位数填充'):
            if col in groups: raise LedgerError('填补字段不能同时作为分组条件。')
            source=data.copy(); source[col]=numeric(source[col])
            fill=source.groupby(groups,dropna=False)[col].transform('mean' if op=='均值填充' else 'median')
            data[col]=data[col].fillna(fill)
            return data[[f['name'] for f in schema]].reset_index(drop=True),schema
        s=numeric(data[col]) if op in ('均值填充','中位数填充') else data[col]
        value=s.mean() if op=='均值填充' else s.median() if op=='中位数填充' else (s.mode().iloc[0] if len(s.mode()) else None) if op=='众数填充' else params.get('value','')
        if value is None or pd.isna(value): raise LedgerError('没有可用于填充的有效值。')
        data[col]=data[col].fillna(value)
    elif op in ('异常值标记','异常值过滤'):
        groups=params.get('groups',[])
        if col in groups: raise LedgerError('检测字段不能同时作为分组条件。')
        mask=data.groupby(groups,dropna=False)[col].transform(lambda s:outliers(s,params.get('method','IQR'))) if groups else outliers(data[col],params.get('method','IQR'))
        if op=='异常值过滤':
            if not params.get('confirmed'): raise LedgerError('过滤异常值需要明确确认。')
            data=data.loc[~mask]
        else:
            name=f'{col}异常标记'; data[name]=mask.map({True:'候选异常',False:'正常/不足以判断'})
            if name not in [f['name'] for f in schema]: schema.append({'name':name,'type':'文本'})
    elif op in ('数值转换','日期转换'):
        data[col]=numeric(data[col]) if op=='数值转换' else pd.to_datetime(data[col],errors='coerce',format='mixed').dt.strftime('%Y-%m-%d')
        next(f for f in schema if f['name']==col)['type']='数字' if op=='数值转换' else '日期'
    elif op in ('标准化','归一化'):
        s=numeric(data[col]); denom=s.std() if op=='标准化' else s.max()-s.min()
        if not pd.notna(denom) or denom==0: raise LedgerError('常数列或样本不足，无法缩放。')
        data[col]=(s-(s.mean() if op=='标准化' else s.min()))/denom
        next(f for f in schema if f['name']==col).update(type='数字',min=None,max=None)
    elif op=='排序': data=data.sort_values(col,key=lambda s:numeric(s) if next(f for f in schema if f['name']==col)['type']=='数字' else s,ascending=not params.get('descending',False))
    elif op=='筛选': data=data[data[col].fillna('').astype(str).str.contains(str(params.get('value','')),regex=False)]
    elif op=='分组均值':
        nums=[f['name'] for f in schema if f['type']=='数字' and f['name']!=col]
        if not nums: raise LedgerError('没有可聚合的数值字段。')
        data[nums]=data[nums].apply(numeric); data=data.groupby(col,dropna=False)[nums].mean().reset_index(); schema=[f for f in schema if f['name'] in data.columns]
    elif op=='派生字段':
        other=params['other']; name=str(params.get('name','派生结果')).strip()
        if name in data or not name: raise LedgerError('派生字段必须使用新的非空名称。')
        a,b=numeric(data[col]),numeric(data[other]); operator=params.get('operator','+')
        if operator=='+': result=a+b
        elif operator=='-': result=a-b
        elif operator=='*': result=a*b
        else: result=a/b.replace(0,np.nan)
        data[name]=result; schema.append({'name':name,'type':'数字'})
    else: raise LedgerError('未知清洗操作。')
    return data[[f['name'] for f in schema]].reset_index(drop=True),schema

def regression(data, xs, y):
    if not xs or y in xs: raise LedgerError('请选择不同的自变量和因变量。')
    valid=data[xs+[y]].apply(numeric).dropna()
    if len(valid) and valid.abs().to_numpy().max()>1e100: raise LedgerError('数值量级过大，回归可能溢出；请先换算单位或标准化。')
    if len(valid)<=len(xs)+1: raise LedgerError('有效样本不足：需大于参数数量。')
    x=np.column_stack([np.ones(len(valid)),valid[xs].to_numpy()]); target=valid[y].to_numpy()
    if np.linalg.matrix_rank(x)<x.shape[1]: raise LedgerError('自变量常数或完全共线，无法唯一估计。')
    coef=np.linalg.lstsq(x,target,rcond=None)[0]; predicted=x@coef; residual=target-predicted; total=np.sum((target-target.mean())**2)
    return {'n':len(valid),'coefficients':coef.tolist(),'equation':f'{y} = {coef[0]:.6g}'+''.join(f' {c:+.6g}×{name}' for c,name in zip(coef[1:],xs)),'r2':float(1-np.sum(residual**2)/total) if total else None,'condition_number':float(np.linalg.cond(x)),'actual':target.tolist(),'predicted':predicted.tolist(),'residual':residual.tolist(),'limits':'最小二乘线性模型；需独立观测、线性关系、近似同方差；残差需检查，外推及因果解释不可靠。'}

def hypothesis(groups, kind='独立样本t检验', alpha=.05):
    try: from scipy import stats
    except ImportError: return {'status':'不可用','reason':'未安装SciPy；描述统计及回归仍可用，不输出显著性结论。'}
    arrays=[numeric(pd.Series(g)).dropna().to_numpy() for g in groups]
    if len(arrays)<2 or any(len(g)<8 for g in arrays): return {'status':'样本不足','reason':'每组至少8个有效值；小样本正态性诊断不稳定。'}
    if kind!='ANOVA' and len(arrays)!=2: return {'status':'条件不满足','reason':'t检验需要恰好两组。'}
    if kind=='配对样本t检验' and len(arrays[0])!=len(arrays[1]): return {'status':'条件不满足','reason':'配对样本必须按实验轮次对齐且等长。'}
    checks=[arrays[0]-arrays[1]] if kind=='配对样本t检验' else arrays
    if any(np.std(a)<1e-12 for a in arrays+checks) or any(stats.shapiro(a[:5000]).pvalue<alpha for a in checks): return {'status':'条件不满足','reason':'常数样本/差值或正态性检查未通过；不强行推断显著性。'}
    if kind=='ANOVA' and stats.levene(*arrays).pvalue<alpha: return {'status':'条件不满足','reason':'方差齐性检查未通过。'}
    result=stats.f_oneway(*arrays) if kind=='ANOVA' else stats.ttest_rel(*arrays) if kind=='配对样本t检验' else stats.ttest_ind(*arrays,equal_var=False)
    if not np.isfinite(result.pvalue): return {'status':'条件不满足','reason':'检验退化，无法推断。'}
    return {'status':'已计算','H0':'各组总体均值相等（配对检验为差值均值0）','H1':'至少一组均值不同','statistic':float(result.statistic),'p':float(result.pvalue),'alpha':alpha,'conclusion':'拒绝H0' if result.pvalue<alpha else '证据不足以拒绝H0','limits':'正态性诊断通过不保证假设成立；独立性需实验设计保证；不拒绝不等于证明相同。'}

def compare(frame, group, metric):
    data=frame[[group,metric]].copy(); data[metric]=numeric(data[metric]); data=data.dropna(subset=[metric])
    result=data.groupby(group)[metric].agg(['count','mean','std','min','max'])
    if len(result):
        base=result['mean'].iloc[0]; result['均值差(相对首组)']=result['mean']-base; result['相对变化%']=(result['mean']-base)/abs(base)*100 if base else np.nan
    return result

def insights(frame, fields, goal=''):
    data=numbers(frame,fields); q=quality_score(frame,fields)
    lines=[f'数据质量评分 {q["score"]}/100，{len(frame)}行、{len(frame.columns)}列、{q["missing"]}个缺失单元格、{q["duplicates"]}行涉及重复。']
    for col in data:
        s=data[col].dropna()
        if len(s): lines.append(f'{col}：n={len(s)}，均值={s.mean():.5g}，标准差={s.std():.5g}，IQR候选异常={int(outliers(s).sum())}。')
    matrix=correlation(data)
    for i,a in enumerate(matrix.columns):
        for b in matrix.columns[i+1:]:
            r=matrix.loc[a,b]
            if pd.notna(r) and abs(r)>=.6: lines.append(f'{a}与{b}：Pearson r={r:.3f}，有效配对n={len(data[[a,b]].dropna())}；相关不代表因果。')
    for f in fields:
        if f['type']=='文本' and 2<=frame[f['name']].nunique()<=8 and len(data.columns):
            metric=data.columns[-1]; table=compare(frame,f['name'],metric)
            if len(table)>1:
                best=table['mean'].idxmin(); lines.append(f'按{f["name"]}分组，{metric}当前均值最小组为{best}（{table.loc[best,"mean"]:.5g}，n={table.loc[best,"count"]:.0f}）；指标越小是否越好需结合目的，不能推断普遍优势。')
            break
    return {'source':'本地统计规则引擎（非大模型）','evidence':lines,'draft':f'实验目的：{goal or "待填写"}\n\n实验发现与关键数据：\n'+'\n'.join(lines)+'\n\n结果解释：仅描述当前样本，需要结合实验条件复核。\n局限性：合成数据仅供功能展示；真实数据仍需独立重复、控制混杂因素。\n后续建议：核对异常记录，增加重复测量，按输入规模和实验阶段分层比较。'}

def temporal(frame, time, metric, window=3, period=3):
    data=pd.DataFrame({'时间':pd.to_datetime(frame[time],errors='coerce'),'观测值':numeric(frame[metric])}).dropna().sort_values('时间')
    data['移动平均']=data['观测值'].rolling(window,min_periods=1).mean()
    data['增长率%']=data['观测值'].pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)*100
    return data,{'周期滞后':period,'自相关':data['观测值'].autocorr(period) if len(data)>period+2 and data['观测值'].std()>0 else None,'说明':'自相关是周期线索，非周期存在的证明；请先按固定时间间隔采样。'}
