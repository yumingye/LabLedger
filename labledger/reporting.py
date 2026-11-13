"""Self-contained reports with version lineage and reproducible snapshots."""
import html
import io
import json
import zipfile
import base64
import pandas as pd
from .science import numbers,describe,correlation,insights,quality_score,regression,compare
from .advanced_charts import static
from .exports import csv_bytes
from .errors import LedgerError
from .archive import unwrap

def project_export(store,pid):
    project=next(p for p in store.projects() if p['id']==pid)
    return {'format':'LabLedger-V2','project':project,'metadata':store.metadata(pid),'dashboard':store.dashboard(pid),'history':store.history(pid),'datasets':[{'id':d['id'],'name':d['name'],'fields':json.loads(d['schema_json']),'records':store.frame(pid,d['id']).to_dict('records'),'versions':store.versions(pid,d['id'])} for d in store.datasets(pid)]}

def project_import(store,content):
    if len(content)>20*1024*1024: raise LedgerError('项目文件超过20MB。')
    try:
        obj=json.loads(content)
        if not isinstance(obj,dict) or obj.get('format')!='LabLedger-V2' or not isinstance(obj.get('datasets'),list) or not obj['datasets'] or len(obj['datasets'])>100: raise ValueError()
        if not isinstance(obj['project']['name'],str): raise ValueError()
        from .validation import validate_schema
        for ds in obj['datasets']:
            validate_schema(ds['fields']); names={f['name'] for f in ds['fields']}
            if not isinstance(ds['records'],list) or any(not isinstance(r,dict) or set(r)!=names or any(isinstance(v,(dict,list)) for v in r.values()) for r in ds['records']): raise ValueError()
            store.name(ds['name'])
            for version in ds.get('versions',[]):
                validate_schema(json.loads(version['schema_json'])); json.loads(version['payload']); json.loads(version['parameters'])
        dashboard=obj.get('dashboard',{'columns':2,'charts':[]})
        if dashboard['columns'] not in (1,2,3) or not isinstance(dashboard['charts'],list) or len(dashboard['charts'])>50: raise ValueError()
        ids={d['id'] for d in obj['datasets']}
        if len(ids)!=len(obj['datasets']): raise ValueError()
        for chart in dashboard['charts']:
            from .charts import ChartConfig
            if chart['dataset_id'] not in ids: raise ValueError()
            ChartConfig(**{k:v for k,v in chart.items() if k!='dataset_id'})
    except (ValueError,KeyError,TypeError,AttributeError,IndexError): raise LedgerError('不是有效的LabLedger V2项目备份。')
    pid=store.create_project(obj['project']['name'][:94]+'（导入）')
    try:
        store.set_metadata(pid,obj.get('metadata',{})); mapping={}
        for ds in obj['datasets']:
            did=store.create_dataset(pid,ds['name'],ds['fields']); mapping[ds['id']]=did
            for version in reversed(ds.get('versions',[])):
                fields=json.loads(version['schema_json']); store.save_frame(pid,did,pd.DataFrame(json.loads(version['payload']),columns=[f['name'] for f in fields]),operation='导入历史版本',parameters={'source_version':version},fields=fields)
            store.save_frame(pid,did,pd.DataFrame(ds['records'],columns=[f['name'] for f in ds['fields']]),operation='项目导入',fields=ds['fields'])
        dashboard=obj.get('dashboard',{'columns':2,'charts':[]})
        for c in dashboard['charts']: c['dataset_id']=mapping[c['dataset_id']]
        store.save_dashboard(pid,dashboard)
        for record in reversed(obj.get('history',[])): store.log(pid,mapping.get(record['dataset_id']),record['kind'],{'imported_history':record})
    except Exception:
        store.delete_project(pid); raise
    return pid

def report_bundle(store,pid,did,conclusion):
    frame=store.frame(pid,did)
    if frame.empty: raise LedgerError('空数据不能生成实验报告。')
    fields=json.loads(store.dataset(pid,did)['schema_json']); meta=store.metadata(pid)
    project=next(p for p in store.projects() if p['id']==pid); nums=numbers(frame,fields); desc=describe(nums); corr=correlation(nums)
    analysis=next((unwrap(r['payload']) for r in store.history(pid) if r['dataset_id']==did and r['kind']=='分析快照'),{})
    core=meta.get('实验方案',{}).get('metric',analysis.get('y'))
    if core not in nums.columns: core=next((n for n in nums.columns if '运行时间' in n),nums.columns[-1] if len(nums.columns) else None)
    q=quality_score(frame,fields); evidence=insights(frame,fields,meta.get('实验目标',''))
    sections=[('实验目的',meta.get('实验目标','未填写')),('实验背景',meta.get('实验背景','未填写')),('实验方法',meta.get('实验方法','未填写')),('数据来源与规模',f'{meta.get("数据来源","本地录入/CSV；请确认是否为合成数据")}；{len(frame)}行×{len(frame.columns)}列'),('数据质量',json.dumps(q,ensure_ascii=False,indent=2)),('清洗与版本记录',json.dumps(store.versions(pid,did),ensure_ascii=False,indent=2)),('描述统计',desc.to_string(index=False)),('相关性（不代表因果）',corr.to_string()),('智能分析依据','\n'.join(evidence['evidence'])),('实验结论（用户可编辑草稿）',conclusion),('局限性与后续改进','当前样本不保证总体代表性；核对异常值，补充独立重复，分层控制输入规模和实验环境。')]
    if len(nums.columns)>=2:
        try:
            xs=analysis.get('xs') or [n for n in nums.columns if n!=core][:1]
            model=regression(nums,xs,core)
            sections.append(('回归分析',json.dumps({k:v for k,v in model.items() if k not in ('actual','predicted','residual')},ensure_ascii=False,indent=2)))
        except LedgerError as exc: sections.append(('回归适用性',str(exc)))
    groups=[f['name'] for f in fields if f['type']=='文本' and 2<=frame[f['name']].nunique()<=8]
    if groups and len(nums.columns): sections.append(('组间对比（样本描述）',compare(frame,groups[0],core).to_string()))
    snapshots=[r for r in store.history(pid) if r['kind'] in ('统计分析','分析快照','图表生成','实验对比','异常诊断','方案结果对照','档案重跑') and r['dataset_id']==did]
    sections.append(('历史分析及参数',json.dumps([{k:r[k] for k in ('id','kind','created_at','dataset_id')} for r in snapshots],ensure_ascii=False,indent=2)+'\n完整参数及结果见project.json操作历史。'))
    if meta.get('实验方案'): sections.append(('实验方案与结果对照',json.dumps(meta['实验方案'],ensure_ascii=False,indent=2)))
    archives=[r for r in store.history(pid) if r['kind']=='数字档案' and r['dataset_id']==did]
    if archives:
        dossier=unwrap(archives[0]['payload']); sections.append(('数字档案完整性',f'数据SHA256：{dossier["source_sha256"]}；封存版本：{dossier["revision"]}；软件版本：{dossier["software_version"]}。完整档案见项目JSON历史，可在数字档案页面重跑。'))
    # The complete raw versions remain in project.json, not in the report body.
    sections=[(title,json.dumps([{k:v[k] for k in ('id','revision','operation','parameters','created_at','actor')} for v in store.versions(pid,did)],ensure_ascii=False,indent=2) if title=='清洗与版本记录' else text) for title,text in sections]
    md='# '+project['name']+' · 实验报告\n\n'+'\n\n'.join('## '+title+'\n\n'+text for title,text in sections)
    images={}
    if len(nums.columns):
        x=groups[0] if groups else frame.columns[0]; y=core
        images['summary.png']=static(frame,'箱线图' if groups else '直方图',x,y,title='实验分布概览')
    tables={'描述统计':desc.to_html(index=False,escape=True),'相关性（不代表因果）':corr.to_html(escape=True)}
    if groups and core: tables['组间对比（样本描述）']=compare(frame,groups[0],core).to_html(escape=True)
    body='<style>table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:10px;border-bottom:1px solid #dbe4ee;text-align:right}th{background:#edf4fd}section{overflow-x:auto}</style>'+''.join(f'<h2>{html.escape(title)}</h2><section>{tables.get(title,"<pre>"+html.escape(text)+"</pre>")}</section>' for title,text in sections)
    body+=''.join('<img alt="实验数据图表" src="data:image/png;base64,'+base64.b64encode(content).decode()+'">' for content in images.values())
    webpage='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>LabLedger实验报告</title><style>body{max-width:1100px;margin:40px auto;font-family:"Microsoft YaHei",sans-serif;color:#17304d;padding:30px}h1{border-bottom:4px solid #2563eb;padding-bottom:20px}h2{color:#2563eb;margin-top:40px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fb;padding:20px;border-radius:12px}img{max-width:100%}</style><h1>'+html.escape(project['name'])+'</h1>'+body+'</html>'
    snapshot=project_export(store,pid)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('report.html',webpage); z.writestr('report.md',md); z.writestr('data.csv',csv_bytes(frame)); z.writestr('statistics.csv',csv_bytes(desc)); z.writestr('project.json',json.dumps(snapshot,ensure_ascii=False,default=str))
        for name,content in images.items(): z.writestr(name,content)
    return {'html':webpage.encode(),'md':md.encode(),'zip':out.getvalue(),'images':images}
