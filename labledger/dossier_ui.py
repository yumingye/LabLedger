import json
import pandas as pd
import streamlit as st
from .archive import make_archive,replay,unwrap,diagnose,plan_comparison
from .exports import csv_bytes
from .errors import LedgerError

def dossier_page(store,pid,did,frame,fields):
    st.subheader('实验数字档案')
    st.caption('封存数据与参数 → 核查哈希 → 重跑分析 → 比对数值。统计规则引擎，无大模型调用。')
    numeric=[f['name'] for f in fields if f['type']=='数字']
    if not numeric: st.info('请先创建含数值字段的数据集。'); return
    archives,diagnostics,plans=st.tabs(['封存与复现','异常诊断','方案与结果对照'])
    with archives:
        y=st.selectbox('档案核心指标',numeric,index=next((i for i,n in enumerate(numeric) if '运行时间' in n),len(numeric)-1))
        xs=st.multiselect('档案回归自变量',[n for n in numeric if n!=y],default=[n for n in numeric if n!=y][:1])
        groups=['不分组']+[f['name'] for f in fields if f['type']=='文本']; group=st.selectbox('档案对比组别',groups)
        if st.button('封存可执行数字档案',type='primary'):
            charts=[json.loads(r['payload']) for r in store.history(pid) if r['dataset_id']==did and r['kind']=='图表生成']
            package=make_archive(store,pid,did,{'y':y,'xs':xs,'method':'pearson','group':None if group=='不分组' else group},charts[0] if charts else {})
            st.success(f'已封存原始版本、当前版本、处理链和分析结果：{package["source_sha256"][:16]}…')
        records=[r for r in store.history(pid) if r['kind']=='数字档案' and r['dataset_id']==did]
        if records:
            record_id=st.selectbox('已封存的数字档案',[r['id'] for r in records],format_func=lambda n:f'档案 #{n}')
            record=next(r for r in records if r['id']==record_id); package=unwrap(record['payload'])
            a,b,c=st.columns(3); a.metric('封存数据版本',package['revision']); b.metric('原始版本',package['original_revision']); c.metric('处理步骤',len(package['pipeline']))
            st.code('SHA256 '+package['source_sha256']); st.caption('内容哈希可核查一致性，不能验证作者身份。')
            st.download_button('下载数字档案 JSON',json.dumps(package,ensure_ascii=False,indent=2).encode(),'LabLedger_dossier.json',on_click='ignore')
            if st.button('一键重新运行并核对'):
                outcome=replay(package); store.log(pid,did,'档案重跑',{'archive_id':record_id,'status':outcome['status'],'differences':outcome['differences']})
                if outcome['status']=='一致': st.success('重跑结果一致：所有数值在1e-9容差内通过。')
                else: st.warning('重新计算结果存在差异，请核查软件版本与计算环境。')
                st.json(outcome)
            with st.expander('封存参数与处理链'): st.json({k:package[k] for k in ['software_version','created_at','config','chart_config','pipeline']})
        else: st.info('尚无数字档案。选择指标与模型参数，点击封存；以后修改数据也不会改变这份分析。')
    with diagnostics:
        defaults=[n for n in numeric if '运行时间' in n] or numeric[:1]
        selected_metrics=st.multiselect('诊断指标（排除轮次和编号等控制字段）',numeric,default=defaults)
        groups=st.multiselect('诊断分层条件',frame.columns)
        selected_fields=[f for f in fields if f['type']!='数字' or f['name'] in selected_metrics]
        result=diagnose(frame,selected_fields,groups); st.caption('只诊断选定测量指标，避免把轮次/编号误当波动风险。IQR每组至少4个有效观测；CV至少8个；最多展示300项，不自动删除。')
        if result: st.dataframe(pd.DataFrame(result),hide_index=True,width='stretch')
        else: st.info('当前规则未发现问题；这不保证实验数据完全正确。')
        if st.button('保存异常诊断报告'): store.log(pid,did,'异常诊断',{'revision':store.dataset(pid,did)['revision'],'groups':groups,'metrics':selected_metrics,'findings':result}); st.success('诊断依据与建议已保存。')
        st.download_button('下载异常诊断 CSV',csv_bytes(pd.DataFrame(result)),'LabLedger_diagnostics.csv',on_click='ignore')
    with plans:
        meta=store.metadata(pid); saved=meta.get('实验方案',{})
        hypothesis=st.text_area('实验假设与预期解释',saved.get('hypothesis','相同实验条件下，比较运行时间与波动。'))
        metric=st.selectbox('预设结果指标',numeric,index=next((i for i,n in enumerate(numeric) if '运行时间' in n),0))
        target=st.number_input('预期目标值',value=float(saved.get('target',1))); direction=st.selectbox('目标方向',['不高于','不低于','接近'])
        tolerance=st.number_input('允许偏差',min_value=0.,value=float(saved.get('tolerance',0)))
        groups=st.multiselect('方案对照分组条件',frame.columns)
        followup=st.text_area('偏差解释与后续实验计划',saved.get('followup','控制设备与输入规模，核对异常记录后增加独立重复。'))
        table=plan_comparison(frame,metric,target,direction,tolerance,groups); st.dataframe(table,hide_index=True)
        st.caption('95%区间采用均值t区间，依赖独立重复与近似正态；符合目标仅为当前样本的描述，不是等效/优效检验结论。')
        if st.button('保存实验方案与结果对照'):
            payload={'hypothesis':hypothesis,'metric':metric,'target':target,'direction':direction,'tolerance':tolerance,'groups':groups,'followup':followup,'result':table.to_dict('records')}; meta['实验方案']=payload; store.set_metadata(pid,meta)
            store.log(pid,did,'方案结果对照',payload); st.success('实验假设、目标、实际结果及下一步已保存。')
