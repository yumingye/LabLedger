"""Incremental V2 pages; V1 routes remain compatible."""
import json
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
from . import science as sc
from .advanced_charts import KINDS,build,static
from .reporting import report_bundle,project_export,project_import
from .exports import csv_bytes
from .errors import LedgerError
from .dossier_ui import dossier_page
from .archive import unwrap

ROOT=Path(__file__).resolve().parents[1]
META=['实验分类','实验标签','实验目标','研究问题','实验背景','实验方法','自变量','因变量','控制变量','实验设备','实验环境','实验备注','数据来源']

def details(store,pid,did,frame,fields):
    st.subheader('实验详情与研究设计')
    meta=store.metadata(pid)
    with st.form(f'metadata_{pid}'):
        cols=st.columns(2); payload=dict(meta)
        for i,key in enumerate(META): payload[key]=cols[i%2].text_area(key,meta.get(key,''),height=80)
        states=['准备中','进行中','已完成','已归档']; payload['实验状态']=st.selectbox('实验状态',states,index=states.index(meta.get('实验状态','准备中')))
        if st.form_submit_button('保存实验详情'): store.set_metadata(pid,payload); st.success('研究设计与条件已持久化。')
    st.dataframe(pd.DataFrame(store.datasets(pid)),hide_index=True)
    st.write('质量概览',sc.quality_score(frame,fields)['score'])
    st.dataframe(sc.describe(sc.numbers(frame,fields)),hide_index=True)
    st.write('已保存图表配置',store.dashboard(pid))
    st.dataframe(pd.DataFrame(store.history(pid)),hide_index=True)

def cleaning(store,pid,did,frame,fields):
    st.subheader('数据预处理工作台')
    q=sc.quality_score(frame,fields); st.metric('质量评分',q['score']); st.caption(q['rule'])
    st.dataframe(pd.DataFrame(q['issues']),hide_index=True)
    numeric=sc.numbers(frame,fields)
    if len(numeric.columns):
        with st.expander('数值分布与相关性'):
            st.dataframe(sc.describe(numeric)); st.dataframe(sc.correlation(numeric))
    operation=st.selectbox('处理操作',['异常值标记','删除重复行','删除缺失行','均值填充','中位数填充','众数填充','指定值填充','异常值过滤','数值转换','日期转换','排序','筛选','分组均值','标准化','归一化','派生字段'])
    col=st.selectbox('处理字段',frame.columns)
    params={'operation':operation,'column':col}
    if operation in ('均值填充','中位数填充','异常值标记','异常值过滤'):
        params['groups']=st.multiselect('按实验条件分别处理',[c for c in frame.columns if c!=col])
        st.caption('建议按算法、输入规模或批次分组。无有效值的组不强行填补；每组少于4个样本时不判定异常。')
    if operation in ('指定值填充','筛选'): params['value']=st.text_input('指定值 / 包含文本')
    if operation in ('异常值标记','异常值过滤'): params['method']=st.radio('检测方法',['IQR','3σ'],horizontal=True)
    if operation=='排序': params['descending']=st.checkbox('降序')
    if operation=='异常值过滤': params['confirmed']=st.checkbox('确认过滤候选异常（原版本仍保留）')
    if operation=='派生字段':
        params['other']=st.selectbox('第二字段',frame.columns); params['operator']=st.selectbox('计算',['+','-','*','/']); params['name']=st.text_input('新字段名称','派生结果')
    revision=store.dataset(pid,did)['revision']
    key=f'preview_{pid}_{did}'
    if st.button('预览处理结果',type='primary'):
        changed,schema=sc.clean(frame,fields,params)
        st.session_state[key]=(changed,schema,params,revision)
    if key in st.session_state:
        changed,schema,saved,rev=st.session_state[key]
        st.caption(f'预览操作：{saved}；原始 {len(frame)} 行 → 预览 {len(changed)} 行。原数据尚未修改。')
        a,b=st.columns(2); a.dataframe(frame.head(30).astype(str)); b.dataframe(changed.head(30).astype(str))
        if st.button('保存为新版本'):
            store.save_frame(pid,did,changed,rev,'数据清洗',saved,schema); del st.session_state[key]; st.rerun()
    versions=store.versions(pid,did)
    st.subheader('版本历史与恢复')
    st.dataframe(pd.DataFrame([{k:v[k] for k in ('id','revision','operation','parameters','created_at','actor')} for v in versions]),hide_index=True)
    if versions:
        vid=st.selectbox('查看/恢复版本',[v['id'] for v in versions],format_func=lambda n:f'版本 #{n}')
        selected=next(v for v in versions if v['id']==vid); prior=pd.DataFrame(json.loads(selected['payload']))
        st.caption(f'所选版本 {len(prior)} 行、{len(json.loads(selected["schema_json"]))} 列；当前 {len(frame)} 行、{len(frame.columns)} 列。')
        st.dataframe(prior.head(30))
        confirmed=st.checkbox('确认恢复此历史版本')
        if st.button('恢复版本',disabled=not confirmed): store.restore_version(pid,did,vid,revision); st.rerun()

def stats(store,pid,did,frame,fields):
    st.subheader('专业统计分析工作台')
    data=sc.numbers(frame,fields); names=list(data.columns)
    if not names: st.info('需要数值字段。'); return
    st.dataframe(sc.describe(data),hide_index=True)
    st.caption('方差/标准差采用样本估计ddof=1；CV=标准差/|均值|，零均值时未定义；偏度与峰度采用Pandas无偏估计；众数并列时显示最小值。')
    method=st.radio('相关性方法',['pearson','spearman'],horizontal=True,key=f'stats_corr_{pid}_{did}')
    matrix=sc.correlation(data,method); st.dataframe(matrix)
    st.caption('|r|≥0.8很强，≥0.6较强，≥0.3中等，其余较弱；仅作经验描述。至少3个有效配对，常数列未定义；相关不代表因果。')
    y=st.selectbox('因变量',names,index=len(names)-1,key=f'stats_y_{pid}_{did}'); xs=st.multiselect('回归自变量',[n for n in names if n!=y],default=[n for n in names if n!=y][:1],key=f'stats_xs_{pid}_{did}')
    model=None
    if xs:
        try:
            model=sc.regression(data,xs,y); st.code(model['equation']); st.write('R²',model['r2']); st.caption(model['limits'])
            st.dataframe(pd.DataFrame({k:model[k] for k in ('actual','predicted','residual')})); st.plotly_chart(build(pd.DataFrame({'预测':model['predicted'],'残差':model['residual']}),'散点图','预测','残差',title='残差诊断'),width='stretch')
        except LedgerError as exc: st.info(str(exc))
    groups=[f['name'] for f in fields if f['type']=='文本']
    test=None; group=None; kind=None
    if groups:
        group=st.selectbox('假设检验分组字段',groups); kind=st.selectbox('检验类型',['独立样本t检验','配对样本t检验','ANOVA']); alpha=st.number_input('显著性水平',.001,.2,.05,.001)
        if kind=='配对样本t检验':
            pair=st.selectbox('配对标识字段（同一受试对象/轮次）',frame.columns)
            groups_data=[]
            if frame.duplicated([group,pair]).any(): st.warning('配对标识在组内重复，请先筛选固定实验条件。')
            else:
                wide=frame.pivot(index=pair,columns=group,values=y).apply(sc.numeric).dropna()
                groups_data=[wide[c] for c in wide]
        else: groups_data=[s[y] for _,s in frame.groupby(group)]
        test=sc.hypothesis(groups_data,kind,alpha); st.json(test)
    params={'xs':xs,'y':y,'correlation':method,'group':group,'test':kind,'model':model,'hypothesis':test,'dataset_revision':store.dataset(pid,did)['revision']}
    if st.button('保存分析快照'): store.log(pid,did,'分析快照',params); st.success('数据版本、结果和参数已保存。')
    dates=[f['name'] for f in fields if f['type']=='日期']
    if dates:
        time=st.selectbox('时间字段',dates); window=st.slider('移动平均窗口',2,20,3); period=st.slider('周期滞后',1,30,3)
        timeline,cycle=sc.temporal(frame,time,y,window,period); st.dataframe(timeline); st.json(cycle)
        if len(timeline): st.line_chart(timeline.set_index('时间')[['观测值','移动平均']])

def comparison(store,pid,did,frame,fields):
    st.subheader('实验与批次对比')
    projects=store.projects(); lookup={p['id']:p['name'] for p in projects}
    selected=st.multiselect('参与对比的实验',list(lookup),default=[pid],format_func=lookup.get)
    parts=[]
    for p in selected:
        datasets=store.datasets(p)
        if not datasets: continue
        ds=st.selectbox(f'实验 {lookup[p]} 的数据集',[d['id'] for d in datasets],format_func=lambda n:next(d['name'] for d in datasets if d['id']==n),key=f'cmp_{p}')
        part=store.frame(p,ds).copy(); part['来源实验']=f'{lookup[p]} #{p}'; parts.append(part)
    if not parts: st.info('请选择有数据的实验。'); return
    common=set(parts[0].columns)
    for part in parts[1:]: common &= set(part.columns)
    combined=pd.concat([part[sorted(common)] for part in parts],ignore_index=True)
    nums=[c for c in sorted(common) if sc.numeric(combined[c]).notna().any()]
    if not nums: st.info('没有共同的数值指标。'); return
    metric=st.selectbox('对比指标',nums,index=next((i for i,c in enumerate(nums) if '运行时间' in c),0))
    group=st.selectbox('组别/实验条件',sorted(common),index=sorted(common).index('算法名称') if '算法名称' in common else sorted(common).index('来源实验'))
    scale=st.selectbox('分层控制字段',['不分层']+[c for c in sorted(common) if c not in (group,metric)])
    if scale!='不分层':
        values=st.multiselect('保留条件',combined[scale].dropna().unique().tolist())
        if values: combined=combined[combined[scale].isin(values)]
        st.caption('请按相同输入规模、设备和实验阶段对比，避免混杂。')
    table=sc.compare(combined,group,metric); st.dataframe(table)
    st.plotly_chart(build(combined,'箱线图',group,metric,title='组间分布与稳定性'),width='stretch')
    if scale!='不分层': st.plotly_chart(build(combined,'折线图',scale,metric,group,title='各实验条件的趋势对比'),width='stretch')
    st.caption('均值差和相对变化以表中首组为基线。标准差显示样本波动；一次测量无法证明普遍优势。')
    test=sc.hypothesis([s[metric] for _,s in combined.groupby(group)],'ANOVA' if len(table)>2 else '独立样本t检验'); st.json(test)
    if st.button('保存对比结果'): store.log(pid,did,'实验对比',{'metric':metric,'group':group,'experiments':selected,'summary':table.reset_index().to_dict('records'),'test':test}); st.success('对比结果已保存。')

def charts(store,pid,did,frame,fields):
    st.subheader('高级图表工坊')
    nums=[f['name'] for f in fields if f['type']=='数字']
    if not nums: st.info('需要数值字段。'); return
    kind=st.selectbox('高级图表类型',KINDS); x=st.selectbox('高级X轴',frame.columns); y=st.selectbox('高级Y轴',nums,index=len(nums)-1)
    group=st.selectbox('高级分组',['不分组']+list(frame.columns)); group=None if group=='不分组' else group
    title=st.text_input('高级图表标题','实验数据分析'); xlabel=st.text_input('X轴标题与单位',x); ylabel=st.text_input('Y轴标题与单位',y); legend=st.text_input('图例标题',group or '')
    palette=st.selectbox('配色',['蓝','青']); width=st.slider('图像宽度',600,1800,1000,100); height=st.slider('图像高度',300,900,520,20)
    filter_col=st.selectbox('图表筛选字段',['不筛选']+list(frame.columns)); data=frame
    if filter_col!='不筛选':
        values=st.multiselect('图表保留值',frame[filter_col].dropna().astype(str).unique()); data=frame[frame[filter_col].astype(str).isin(values)] if values else frame
    config=dict(kind=kind,x=x,y=y,group=group,title=title,palette=palette,width=width,height=height,xlabel=xlabel,ylabel=ylabel,legend=legend)
    fig=build(data,**config); st.plotly_chart(fig,width='stretch')
    st.caption('折线/面积/柱状图按坐标和分组取均值；误差棒为样本标准差。HTML内嵌Plotly，可离线打开。')
    for fmt in ['png','svg']:
        st.download_button(f'下载高级图表 {fmt.upper()}',static(data,fmt=fmt,**config),f'LabLedger_chart.{fmt}')
    st.download_button('下载交互图表 HTML',fig.to_html(include_plotlyjs=True).encode(),'LabLedger_chart.html','text/html',on_click='ignore')
    if st.button('保存图表分析记录'): store.log(pid,did,'图表生成',{'config':config,'revision':store.dataset(pid,did)['revision'],'filter_column':filter_col,'values':values if filter_col!='不筛选' else []}); st.success('图表参数已保存。')

def assistant(store,pid,did,frame,fields):
    st.subheader('智能实验分析助手')
    result=sc.insights(frame,fields,store.metadata(pid).get('实验目标','')); st.caption(result['source'])
    for line in result['evidence']: st.info(line)
    key=f'conclusion_{pid}_{did}'; draft=st.text_area('可编辑实验结论',result['draft'],height=350,key=key)
    if st.button('保存结论草稿'): store.log(pid,did,'实验结论',{'draft':draft,'revision':store.dataset(pid,did)['revision']}); st.success('草稿已保存；报告中心可继续编辑。')
    st.caption('默认不联网、不调用付费API。本版本未集成Ollama；全部建议由本地统计计算产生。')

def reports(store,pid,did,frame,fields):
    st.subheader('实验报告中心')
    saved=next((unwrap(r['payload'])['draft'] for r in store.history(pid) if r['kind']=='实验结论' and r['dataset_id']==did),None)
    draft=st.text_area('报告结论（可编辑）',saved or sc.insights(frame,fields,store.metadata(pid).get('实验目标',''))['draft'],height=250,key=f'report_draft_{pid}_{did}')
    key=f'report_{pid}_{did}'
    revision=store.dataset(pid,did)['revision']
    fingerprint=(revision,draft)
    if key in st.session_state and st.session_state.get(key+'_source')!=fingerprint:
        del st.session_state[key]; st.info('数据版本或结论已变化，请重新生成报告，避免下载过期结果。')
    if st.button('生成完整实验报告',type='primary'):
        bundle=report_bundle(store,pid,did,draft); st.session_state[key]=bundle
        st.session_state[key+'_source']=fingerprint
        target=ROOT/'exports/v2'/f'project_{pid}'; target.mkdir(parents=True,exist_ok=True)
        from datetime import datetime
        path=target/f'report_dataset{did}_rev{revision}_{datetime.now():%Y%m%d_%H%M%S_%f}.zip'; path.write_bytes(bundle['zip'])
        store.log(pid,did,'报告导出',{'file':str(path.relative_to(ROOT)),'revision':revision,'conclusion':draft}); st.success('报告已生成并保存，可下载以下文件。')
    if key in st.session_state:
        bundle=st.session_state[key]
        for fmt in ['html','md','zip']: st.download_button(f'下载报告 {fmt.upper()}',bundle[fmt],f'LabLedger_report.{fmt}',on_click='ignore')
        st.download_button('下载报告 CSV附件',csv_bytes(frame),'LabLedger_data.csv')
        for name,content in bundle['images'].items(): st.image(content); st.download_button('下载报告 PNG',content,name)
        with st.expander('报告正文预览',expanded=True): st.markdown(bundle['md'])
    st.dataframe(pd.DataFrame([r for r in store.history(pid) if r['kind']=='报告导出' and r['dataset_id']==did]))

def settings(store,pid,did,frame,fields):
    st.subheader('历史、备份与可复现性')
    history=store.history(pid); st.dataframe(pd.DataFrame(history),hide_index=True)
    with st.expander('删除当前数据集（保留独立数字档案历史）'):
        phrase=st.text_input('输入当前数据集名称确认删除',key=f'dataset_delete_{did}')
        if st.button('确认删除此数据集',disabled=phrase!=store.dataset(pid,did)['name']): store.delete_dataset(pid,did); st.rerun()
    st.download_button('导出完整实验项目 JSON',json.dumps(project_export(store,pid),ensure_ascii=False,default=str).encode(),'LabLedger_project.json')
    upload=st.file_uploader('导入实验项目（新建隔离副本）',type='json')
    if upload and st.button('导入项目副本'):
        new=project_import(store,upload.getvalue()); st.session_state['pending_project']=new; st.rerun()
    if st.button('创建数据库备份'):
        from datetime import datetime
        path=ROOT/'exports/v2'/f'backup_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3'; store.backup(path); st.session_state['backup_bytes']=path.read_bytes(); st.success(f'已保存：{path.name}')
    if 'backup_bytes' in st.session_state: st.download_button('下载数据库备份',st.session_state['backup_bytes'],'LabLedger_backup.sqlite3')
    backup=st.file_uploader('恢复数据库备份（保留当前库副本）',type=['sqlite3','db'])
    confirmed=st.checkbox('确认替换当前数据库；恢复前自动保留当前库备份')
    if backup and st.button('执行数据库恢复',disabled=not confirmed):
        if backup.size>20*1024*1024: raise LedgerError('备份超过20MB。')
        target=ROOT/'.runtime/tmp/restore_candidate.sqlite3'; target.write_bytes(backup.getvalue())
        try:
            with sqlite3.connect(f'{target.as_uri()}?mode=ro',uri=True) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise LedgerError('备份完整性失败。')
                for table in ['projects','datasets','records','versions','history']: db.execute(f'SELECT * FROM {table} LIMIT 1')
        except sqlite3.Error as exc: raise LedgerError('不是可用的V2数据库备份。') from exc
        from datetime import datetime
        store.backup(ROOT/'exports/v2'/f'before_restore_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3')
        with sqlite3.connect(target) as source,store.connect() as dest: source.backup(dest)
        st.session_state.clear(); st.rerun()
    snapshots=[r for r in history if r['kind'] in ('分析快照','图表生成')]
    if snapshots:
        selected=st.selectbox('历史快照',[r['id'] for r in snapshots]); record=next(r for r in snapshots if r['id']==selected); payload=unwrap(record['payload']); st.json(payload)
        if not any(d['id']==record['dataset_id'] for d in store.datasets(pid)):
            st.info('该数据集已删除，历史参数仍可查看；完整数字档案可从项目历史导出复核。'); return
        versions=store.versions(pid,record['dataset_id']); revision=payload.get('dataset_revision',payload.get('revision'))
        version=next((v for v in versions if v['revision']==revision),None)
        if st.checkbox('确认恢复快照数据版本') and st.button('恢复快照数据与参数'):
            if version is None: raise LedgerError('快照版本不存在。')
            store.restore_version(pid,record['dataset_id'],version['id'],store.dataset(pid,record['dataset_id'])['revision'])
            st.session_state['restored_snapshot']=payload
            if record['kind']=='分析快照':
                st.session_state['pending_snapshot']={'pid':pid,'did':record['dataset_id'],'payload':payload}; st.rerun()
            st.success('原数据版本已恢复，原图表参数及结果显示于上方。')

PAGES={'实验详情':details,'数据清洗':cleaning,'专业统计':stats,'实验对比':comparison,'高级图表':charts,'智能分析':assistant,'报告中心':reports,'系统设置':settings,'数字档案':dossier_page}
