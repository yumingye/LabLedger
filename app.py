"""Streamlit presentation layer. Business logic lives in labledger/."""
from __future__ import annotations
from labledger import runtime
import html
import json
import logging
import os
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st
from labledger.db import Store
from labledger.errors import LedgerError
from labledger.validation import quality
from labledger.analysis import statistics, recommendations, trend
from labledger.charts import ChartConfig, available_fonts, plot, png, prepare
from labledger.exports import import_csv, csv_bytes, raw_bytes, filename
from labledger.demo import load_demo
from labledger.v2_ui import PAGES
from labledger.demo_v2 import load_algorithm_demo

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='数迹 LabLedger · 智能实验数据工坊',page_icon='◈',layout='wide')
(ROOT/'logs').mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT/'logs/app.log',level=logging.INFO,encoding='utf-8')
st.markdown('''<style>
.block-container{padding-top:3.7rem;padding-bottom:3rem;max-width:1480px}
[data-testid="stSidebar"]{background:#11283e}
[data-testid="stSidebar"] *{color:#e2edf5}
[data-testid="stSidebar"] input{color:#172b46}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#172b46}
[data-testid="stSidebar"] button{background:#244158;border-color:#365369}
h1,h2,h3{letter-spacing:-.035em} h1{font-weight:750!important;font-size:2.1rem!important}
[data-testid="stMetric"]{background:white;border:1px solid #e5ebf2;border-radius:14px;padding:18px 22px}
[data-testid="stMetricLabel"]{color:#70839a}
.eyebrow{color:#0e9285;font-size:12px;letter-spacing:2px;font-weight:700;margin-bottom:8px}
.hero{background:linear-gradient(115deg,#13364b,#145b61);padding:30px 34px;border-radius:18px;color:white;margin:12px 0 24px}
.hero h2{color:white;margin:0 0 8px;font-size:27px}.hero p{color:#bfdbdf;margin:0;line-height:1.8}
.step{background:white;border:1px solid #e4ebf1;border-radius:14px;padding:22px;min-height:145px}
.step b{color:#0e9285}.step h4{margin:8px 0}.step p{font-size:14px;color:#77869a}
[data-testid="stTabs"]{margin-top:18px}
.stButton>button,.stDownloadButton>button{border-radius:9px}
footer{visibility:hidden}
</style>''',unsafe_allow_html=True)

def rerun(message: str = '') -> None:
    if message:
        st.session_state['notice']=message
    st.rerun()

def metrics(frame: pd.DataFrame, report: dict, fields: list[dict]) -> None:
    a,b,c,d=st.columns(4)
    a.metric('记录总量',f'{len(frame):,}',help='当前数据集的持久化记录数')
    b.metric('数据完整率',f'{report["completeness"]:.1f}%')
    c.metric('待检查提示',len(report['issues']),help='同一记录可能有多项提示；不自动删除')
    d.metric('数值字段',sum(f['type']=='数字' for f in fields))

def create_dataset(store: Store, pid: int) -> None:
    st.caption('字段类型支持数字、文本、日期。日期使用 YYYY-MM-DD；数字可设置范围。')
    if st.button('创建算法性能模板数据表',key=f'algorithm_schema_{pid}'):
        from labledger.demo_v2 import FIELDS
        store.create_dataset(pid,'算法性能观测表',FIELDS); rerun('已创建算法字段；请到数据记录上传CSV。')
    with st.form(f'schema_{pid}'):
        name=st.text_input('数据表名称',value='实验观测表')
        initial=pd.DataFrame([{'字段名':'时间','类型':'数字','下限':None,'上限':None}, {'字段名':'测量值','类型':'数字','下限':None,'上限':None}, {'字段名':'分组','类型':'文本','下限':None,'上限':None}])
        spec=st.data_editor(initial,num_rows='dynamic',hide_index=True,width='stretch',
                            column_config={'类型':st.column_config.SelectboxColumn(options=['数字','文本','日期'],required=True),
                                           '下限':st.column_config.NumberColumn(), '上限':st.column_config.NumberColumn()},key=f'fields_{pid}')
        if st.form_submit_button('创建数据表',type='primary'):
            fields=[{'name':r['字段名'],'type':r['类型'], 'min':None if pd.isna(r['下限']) else float(r['下限']), 'max':None if pd.isna(r['上限']) else float(r['上限'])} for r in spec.to_dict('records')]
            store.create_dataset(pid,name,fields)
            rerun('数据表已创建。')

def autosave_table(store: Store, pid: int, did: int, frame: pd.DataFrame, revision: int, key: str) -> None:
    changes = st.session_state[key]
    edited = frame.copy().astype(object)
    for row, values in changes['edited_rows'].items():
        for column, value in values.items():
            edited.at[int(row), column] = value
    edited = edited.drop(index=changes['deleted_rows'])
    if changes['added_rows']:
        added = pd.DataFrame(changes['added_rows'], columns=edited.columns)
        edited = pd.concat([edited, added], ignore_index=True)
    if edited.equals(frame.astype(object)):
        return
    save_edited_data(store, pid, did, edited, revision)


def autosave_field(store: Store, pid: int, did: int, frame: pd.DataFrame, revision: int, row: int, column: str, key: str) -> None:
    edited = frame.copy().astype(object)
    edited.at[row, column] = st.session_state[key]
    save_edited_data(store, pid, did, edited, revision)


def save_edited_data(store: Store, pid: int, did: int, edited: pd.DataFrame, revision: int) -> None:
    try:
        store.save_frame(pid, did, edited, revision, '表格自动保存')
    except LedgerError as exc:
        st.session_state['autosave_error'] = f'此次修改未保存。{exc}'
    except (sqlite3.Error, OSError):
        logging.exception('Table autosave failed')
        st.session_state['autosave_error'] = '此次修改未保存，请检查本地存储后重试。'
    else:
        st.session_state['notice'] = '表格修改已自动保存。'


def data_page(store: Store,pid: int,did: int,frame: pd.DataFrame,fields: list[dict],revision: int) -> None:
    st.subheader('数据工作台')
    st.caption('提交单元格编辑后自动保存到 SQLite。空值和异常值会保留，并在质量中心标记。')
    if error := st.session_state.pop('autosave_error', None):
        st.error(error)
    edit,view,upload=st.tabs(['录入与编辑','搜索与筛选','CSV 导入'])
    with edit:
        key = f'editor_{pid}_{did}_{revision}'
        st.data_editor(frame.astype(object), num_rows='dynamic', hide_index=False,
                       width='stretch', key=key, on_change=autosave_table,
                       args=(store, pid, did, frame, revision, key))
        st.caption('在末行添加记录。选择行号后按 Delete 删除整行，可在数据清洗页恢复旧版本。')
        if len(frame):
            with st.expander('逐字段编辑（自动保存）'):
                row = st.number_input('编辑行号', min_value=1, max_value=len(frame),
                                      step=1, key=f'autosave_row_{pid}_{did}') - 1
                for field in fields:
                    column = field['name']
                    value = frame.at[row, column]
                    field_key = f'autosave_{pid}_{did}_{revision}_{row}_{column}'
                    st.text_input(f'{column} · 自动保存', value='' if pd.isna(value) else str(value),
                                  key=field_key, on_change=autosave_field,
                                  args=(store, pid, did, frame, revision, row, column, field_key))
        with st.expander('单条记录操作（也可使用上方表格）'):
            with st.form(f'add_{did}'):
                row={f['name']:st.text_input(f"{f['name']} · {f['type']}",key=f'add_{did}_{f["name"]}') for f in fields}
                if st.form_submit_button('新增记录'):
                    store.save_frame(pid,did,pd.concat([frame,pd.DataFrame([row])],ignore_index=True),revision)
                    rerun('记录已新增。')
            if len(frame):
                index=st.number_input('待操作行号（从 1 开始）',min_value=1,max_value=len(frame),step=1,key=f'row_{did}')-1
                with st.form(f'update_{did}_{index}'):
                    row={f['name']:st.text_input(f['name'],value='' if pd.isna(frame.iloc[index][f['name']]) else str(frame.iloc[index][f['name']]),key=f'upd_{did}_{index}_{f["name"]}') for f in fields}
                    if st.form_submit_button('更新该行'):
                        changed=frame.copy(); changed.loc[index]=row
                        store.save_frame(pid,did,changed,revision); rerun('记录已更新。')
                confirm=st.checkbox('确认删除选中记录',key=f'delconfirm_{did}')
                if st.button('删除该行',disabled=not confirm):
                    store.save_frame(pid,did,frame.drop(frame.index[index]),revision); rerun('记录已删除。')
    with view:
        search=st.text_input('搜索所有字段',placeholder='输入实验组、备注或观测值')
        column=st.selectbox('筛选字段',frame.columns,key='filter_col')
        values=st.multiselect('保留字段值（留空表示全部）',sorted(frame[column].fillna('（空）').astype(str).unique()))
        sort=st.selectbox('排序字段',frame.columns,key='sort_col')
        descending=st.checkbox('降序排列')
        filtered=frame.copy()
        if search:
            filtered=filtered[filtered.fillna('').astype(str).apply(lambda s:s.str.contains(search,case=False,regex=False)).any(axis=1)]
        if values:
            filtered=filtered[filtered[column].fillna('（空）').astype(str).isin(values)]
        field=next(f for f in fields if f['name']==sort)
        sortkey=(lambda s:pd.to_numeric(s,errors='coerce')) if field['type']=='数字' else ((lambda s:pd.to_datetime(s,errors='coerce')) if field['type']=='日期' else (lambda s:s.fillna('').astype(str)))
        filtered=filtered.sort_values(sort,ascending=not descending,key=sortkey)
        st.dataframe(filtered,width='stretch',hide_index=True)
        st.caption(f'筛选后 {len(filtered)} / {len(frame)} 条；筛选不会修改原始数据。')
        st.download_button('导出筛选结果 CSV',csv_bytes(filtered),filename('筛选结果','数据','csv'),'text/csv')
    with upload:
        st.info('仅支持与当前字段完全一致的 CSV 表头。导入保留原值，错误类型可在质量中心修正。')
        st.download_button('下载 CSV 字段模板',csv_bytes(frame.iloc[:0]),'LabLedger_字段模板.csv','text/csv')
        uploaded=st.file_uploader('选择 UTF-8 / GB18030 CSV',type='csv')
        if uploaded:
            incoming=import_csv(uploaded.getvalue(),list(frame.columns))
            st.dataframe(incoming.head(20),width='stretch')
            mode=st.radio('导入方式',['追加','替换'],horizontal=True)
            accepted=st.checkbox('确认替换全部现有记录') if mode=='替换' else True
            if st.button('确认导入',disabled=not accepted):
                store.save_frame(pid,did,pd.concat([frame,incoming],ignore_index=True) if mode=='追加' else incoming,revision)
                rerun(f'成功导入 {len(incoming)} 条记录。')

def quality_page(frame: pd.DataFrame,fields: list[dict],report: dict) -> None:
    st.subheader('数据质量中心')
    st.caption('缺失 / 重复 / 类型 / 日期 / 范围 / IQR 六类规则 · 全程保留原始记录')
    if not len(frame):
        st.info('暂无记录，完整率显示为 0%，请先录入数据。')
    elif report['issues']:
        st.warning('发现待检查项。请结合实验背景判断，在「数据记录」中手动修正；异常不等同于错误。')
        st.dataframe(pd.DataFrame(report['issues']),width='stretch',hide_index=True)
        st.download_button('导出质量检查报告',csv_bytes(pd.DataFrame(report['issues'])),filename('实验','质量检查','csv'),'text/csv')
    else:
        st.success('当前规则未发现质量问题。')
    st.markdown('**检查口径**：重复数为参与重复的所有行；完整率为非空单元格占比。IQR 使用 Q1−1.5×IQR 至 Q3+1.5×IQR，少于 4 个有效数值时不判异常。范围规则优先于 IQR。')
    for text in recommendations(frame,fields,report):
        st.info(text)

def analysis_page(frame: pd.DataFrame, fields: list[dict]) -> None:
    st.subheader('统计与趋势')
    stats=statistics(frame,fields)
    st.dataframe(stats,width='stretch',hide_index=True)
    st.caption('标准差与方差使用样本口径（ddof=1）；不足两个有效值时不定义。空白和非有限数值不参与统计。')
    numbers=[f['name'] for f in fields if f['type']=='数字']
    xs=[f['name'] for f in fields if f['type'] in ('数字','日期')]
    if numbers and xs:
        a,b=st.columns(2)
        x=a.selectbox('趋势 X 字段',xs)
        y=b.selectbox('趋势 Y 字段',numbers,index=min(1,len(numbers)-1))
        result=trend(frame,x,y,next(f['type'] for f in fields if f['name']==x)=='日期')
        if result:
            a,b,c=st.columns(3)
            a.metric('线性斜率',f'{result["slope"]:.5g}')
            b.metric('拟合 R²',f'{result["r2"]:.4f}')
            c.metric('首末变化率','未定义（起点为零）' if result['rate_percent'] is None else f'{result["rate_percent"]:.2f}%')
            st.caption('按 X 升序取首末有效值；日期斜率单位为每天。全数据趋势可能混合实验组，分组拟合请在图表工坊查看。')
            st.download_button('导出趋势分析 JSON',json.dumps(result,ensure_ascii=False,indent=2).encode(),filename('实验','趋势','json'),'application/json')
        else:
            st.info('需要至少两对有效数据，且 X 不能全部相同。')

def chart_page(store: Store,pid: int,did: int,frame: pd.DataFrame,fields: list[dict],project: str) -> None:
    st.subheader('图表工坊')
    numbers=[f['name'] for f in fields if f['type']=='数字']
    if not numbers:
        st.info('需要至少一个数字字段才能绘图。'); return
    settings,canvas=st.columns([1,2.8],gap='large')
    with settings:
        kind=st.selectbox('图表类型',['折线图','柱状图','散点图'])
        x=st.selectbox('X 轴字段',frame.columns)
        y=st.selectbox('Y 轴字段',numbers,index=min(1,len(numbers)-1))
        grouping=st.selectbox('分组字段',['不分组']+[n for n in frame.columns if n not in (x,y)])
        title=st.text_input('图表标题','实验观测结果')
        palette=st.selectbox('颜色主题',['海盐青','深海蓝','暖日橙'])
        xtype=next(f['type'] for f in fields if f['name']==x)
        fit=st.checkbox('显示线性趋势线',disabled=xtype=='文本' or kind=='柱状图')
        with st.expander('更多样式'):
            xlabel=st.text_input('X 轴标题',x)
            ylabel=st.text_input('Y 轴标题',y)
            marker=st.selectbox('数据点样式',['circle','square','diamond'])
            grid=st.checkbox('显示网格',True)
            legend=st.checkbox('显示图例',True)
            font = st.selectbox('图表字体', available_fonts())
            font_size = st.slider('字体字号', 10, 26, 14)
            width=st.slider('导出宽度（px）',600,1800,1000,100)
            height=st.slider('图表高度（px）',300,900,480,20)
        c=ChartConfig(x=x,y=y,kind=kind,group=None if grouping=='不分组' else grouping,title=title,palette=palette,
                      fit=fit and kind!='柱状图',xlabel=xlabel,ylabel=ylabel,marker=marker,grid=grid,legend=legend,width=width,height=height,date_x=xtype=='日期',numeric_x=xtype=='数字',
                      font_family=font,font_size=font_size)
    with canvas:
        data = prepare(frame, c)
        if data.empty:
            st.info('所选字段没有可绘制的记录。请选择其他字段，或检查数据质量。')
            return
        st.plotly_chart(plot(frame,c),width='stretch')
        st.caption(f'共绘制 {len(data):,} 条有效记录。高清 PNG 为 {width * 2} × {height * 2} 像素。')
        a, b, actions = st.columns(3)
        with a:
            try:
                image = png(frame, c, scale=2)
            except (ValueError, OSError, RuntimeError):
                logging.exception('Chart PNG export failed')
                st.error('无法生成 PNG。请调整图表尺寸或字体后重试。')
            else:
                st.download_button('↓ 导出 PNG', image, filename(project, title, 'png'), 'image/png', width='stretch')
        columns = list(dict.fromkeys(name for name in (c.x, c.y, c.group) if name is not None))
        b.download_button('↓ 图表数据 CSV', csv_bytes(data[columns]), filename(project, title, 'csv'), 'text/csv', width='stretch')
        if actions.button('＋ 添加到仪表盘',width='stretch'):
            config=store.dashboard(pid)
            config['charts'].append({'dataset_id':did,**c.to_dict()})
            store.save_dashboard(pid,config)
            st.success('图表配置已保存至仪表盘。')

def dashboard_page(store: Store,pid: int) -> None:
    st.subheader('实验仪表盘')
    config=store.dashboard(pid)
    columns=st.radio('布局列数',[1,2,3],index=[1,2,3].index(config['columns']),horizontal=True)
    if st.button('保存布局'):
        config['columns']=columns; store.save_dashboard(pid,config); rerun('布局已保存。')
    if not config['charts']:
        st.info('还没有图表。前往图表工坊，选择字段并添加到仪表盘。'); return
    st.caption('图表读取最新数据。使用上移 / 下移调整顺序，配置会立即持久化。')
    slots=st.columns(columns)
    for i,item in enumerate(config['charts']):
        with slots[i%columns]:
            try:
                frame=store.frame(pid,item['dataset_id'])
                c=ChartConfig(**{k:v for k,v in item.items() if k!='dataset_id'})
                st.plotly_chart(plot(frame,c),width='stretch',key=f'dash_{pid}_{i}')
                a,b,d=st.columns(3)
                if a.button('↑ 上移',key=f'up_{i}',disabled=i==0):
                    config['charts'][i-1],config['charts'][i]=config['charts'][i],config['charts'][i-1]
                    store.save_dashboard(pid,config); rerun()
                if b.button('↓ 下移',key=f'down_{i}',disabled=i==len(config['charts'])-1):
                    config['charts'][i+1],config['charts'][i]=config['charts'][i],config['charts'][i+1]
                    store.save_dashboard(pid,config); rerun()
                if d.button('移除',key=f'remove_{i}'):
                    config['charts'].pop(i); store.save_dashboard(pid,config); rerun()
            except LedgerError as exc:
                st.warning(str(exc))
    st.download_button('导出仪表盘配置',json.dumps(config,ensure_ascii=False,indent=2).encode(),filename('仪表盘','配置','json'),'application/json')

def main() -> None:
    store=Store(os.environ.get('LABLEDGER_DB',str(ROOT/'data/labledger.sqlite3')))
    with st.sidebar:
        st.markdown('## ◈ 数迹 LabLedger')
        st.caption('智能实验数据工坊 / LOCAL WORKSPACE')
        st.divider()
        projects=store.projects()
        choices=[p['id'] for p in projects]
        labels={p['id']:f"{p['name']} · #{p['id']}" for p in projects}
        if st.session_state.get('active_project') not in choices:
            st.session_state['active_project']=choices[0] if choices else None
        pid=st.selectbox('当前实验',choices,format_func=labels.get,key='active_project') if choices else None
        with st.expander('＋ 创建实验',expanded=not choices):
            with st.form('new_project'):
                name=st.text_input('实验名称',placeholder='例如：自由落体测量')
                if st.form_submit_button('创建实验'):
                    new=store.create_project(name)
                    st.session_state['pending_project']=new; rerun('实验已创建。')
        if st.button('一键加载模拟实验',width='stretch'):
            st.session_state['pending_project']=load_demo(store); rerun('已加载模拟实验，包含少量预设质量问题。')
        if st.button('加载算法性能演示',width='stretch'):
            st.session_state['pending_project']=load_algorithm_demo(store); rerun('已加载固定种子的合成数据，不代表真实实验测量结果。')
        with st.expander('实验 CSV 模板与字段说明'):
            for template in sorted((ROOT/'demo/templates').glob('*')):
                if template.is_file(): st.download_button(template.name,template.read_bytes(),template.name,key=f'template_{template.name}')
        st.divider()
        st.caption('离线可用 · SQLite 本地持久化\n\n智能规则推荐 · 无付费 API')
    st.markdown('<div class="eyebrow">LABLEDGER / EXPERIMENT WORKSPACE</div>',unsafe_allow_html=True)
    top,tag=st.columns([4,1])
    top.title('让每一份实验数据，都有迹可循。')
    tag.caption('● 本地工作空间\n\nv2.1 · 个人参赛作品')
    if 'notice' in st.session_state:
        st.success(st.session_state.pop('notice'))
    if pid is None:
        st.markdown('<div class="hero"><h2>从第一条记录，到一张有说服力的图表</h2><p>记录、检查、分析与可视化，在同一个工作空间完成。<br>创建你的第一个实验，或在左侧加载模拟实验，体验完整的数据闭环。</p></div>',unsafe_allow_html=True)
        cols=st.columns(3)
        for col,title,desc in zip(cols,['01 / 结构化记录','02 / 可信分析','03 / 清晰表达'],['自定义数字、文本与日期字段，CSV 批量导入。','发现缺失、重复与异常，统计每一份真实数据。','交互式图表、多图仪表盘和高清 PNG 导出。']):
            col.markdown(f'<div class="step"><b>{title}</b><p>{desc}</p></div>',unsafe_allow_html=True)
        return
    project=next(p for p in projects if p['id']==pid)
    st.caption(f'当前实验：{project["name"]}　·　创建 {project["created_at"]}　·　最近修改 {project["updated_at"]}（UTC）')
    with st.expander('实验设置 / 新建数据表'):
        left,right=st.columns(2)
        with left:
            with st.form(f'rename_{pid}'):
                renamed=st.text_input('修改实验名称',project['name'])
                if st.form_submit_button('保存名称'):
                    store.rename_project(pid,renamed); rerun('实验已重命名。')
            phrase=st.text_input('删除实验：输入完整实验名称确认',key=f'del_{pid}')
            if st.button('永久删除此实验',disabled=phrase!=project['name']):
                store.delete_project(pid); rerun('实验及关联数据已删除。')
        with right:
            create_dataset(store,pid)
    datasets=store.datasets(pid)
    if not datasets:
        st.info('此实验还没有数据表。展开上方设置，自定义字段后创建数据表。'); return
    labels={d['id']:d['name'] for d in datasets}
    did=st.selectbox('数据集',list(labels),format_func=labels.get,key=f'dataset_{pid}')
    dataset, frame = store.dataset_snapshot(pid, did)
    fields = json.loads(dataset['schema_json'])
    report=quality(frame,fields)
    metrics(frame,report,fields)
    # Explicit navigation avoids calculating PNG and all charts on every data edit.
    page=st.sidebar.radio('工作区导航',['总览','实验详情','数据记录','数据清洗','专业统计','实验对比','高级图表','数字档案','智能分析','报告中心','仪表盘','系统设置','质量中心','统计分析','图表工坊','导出中心'],key='page')
    st.divider()
    if page in PAGES:
        PAGES[page](store,pid,did,frame,fields)
    elif page=='总览':
        for column, label, destination in zip(
            st.columns(3),
            ('录入或导入数据', '检查数据质量', '生成与导出图表'),
            ('数据记录', '质量中心', '图表工坊'),
        ):
            column.button(label, width='stretch', on_click=st.session_state.update, args=({'page': destination},))
        all_projects=store.projects(); counts=store.workspace_counts()
        st.caption(f'工作空间：{counts["projects"]} 个实验 · {counts["datasets"]} 个数据集 · {counts["records"]} 条记录')
        st.info('推荐流程：数据记录导入 → 数据清洗预览 → 专业统计与实验对比 → 数字档案封存与重跑 → 报告中心导出。基础统计和旧图表入口继续兼容。')
        with st.expander('最近实验与分析'):
            st.dataframe(pd.DataFrame(all_projects).head(6),hide_index=True)
            st.dataframe(pd.DataFrame(store.history(pid)).head(8),hide_index=True)
        st.markdown('<div class="hero"><h2>把时间留给发现，把数据交给数迹。</h2><p>从结构化记录到可复现分析，让每一步实验都有依据。<br>当前所有修改保存在本机，刷新与重启后仍可恢复。</p></div>',unsafe_allow_html=True)
        left,right=st.columns([2,1])
        with left:
            nums=[f['name'] for f in fields if f['type']=='数字']
            if nums:
                st.plotly_chart(plot(frame,ChartConfig(x=fields[0]['name'],y=nums[-1],title='数据速览',numeric_x=fields[0]['type']=='数字',date_x=fields[0]['type']=='日期')),width='stretch')
            else:
                st.dataframe(frame.head(12),width='stretch')
        with right:
            st.subheader('规则洞察')
            for message in recommendations(frame,fields,report):
                st.info(message)
    elif page=='数据记录': data_page(store,pid,did,frame,fields,dataset['revision'])
    elif page=='质量中心': quality_page(frame,fields,report)
    elif page=='统计分析': analysis_page(frame,fields)
    elif page=='图表工坊': chart_page(store,pid,did,frame,fields,project['name'])
    elif page=='仪表盘': dashboard_page(store,pid)
    else:
        st.subheader('导出中心')
        st.caption('CSV 使用 UTF-8 BOM，兼容中文；公式前缀会转义以安全打开。原始 JSON 保留未经转义的单元格。PNG 在图表工坊下载。')
        a,b,c=st.columns(3)
        a.download_button('↓ 数据 CSV',csv_bytes(frame),filename(project['name'],'数据','csv'),'text/csv',width='stretch')
        b.download_button('↓ 原始数据 JSON',raw_bytes(frame,fields),filename(project['name'],'原始数据','json'),'application/json',width='stretch')
        c.download_button('↓ 统计分析 CSV',csv_bytes(statistics(frame,fields)),filename(project['name'],'统计','csv'),'text/csv',width='stretch')
        st.dataframe(statistics(frame,fields),width='stretch',hide_index=True)

try:
    if 'pending_snapshot' in st.session_state:
        snap=st.session_state.pop('pending_snapshot'); sp,sd,payload=snap['pid'],snap['did'],snap['payload']
        st.session_state['active_project']=sp; st.session_state[f'dataset_{sp}']=sd
        st.session_state['page']='专业统计'
        st.session_state[f'stats_y_{sp}_{sd}']=payload['y']; st.session_state[f'stats_xs_{sp}_{sd}']=payload['xs']; st.session_state[f'stats_corr_{sp}_{sd}']=payload['correlation']
    if 'pending_project' in st.session_state:
        st.session_state['active_project']=st.session_state.pop('pending_project')
    main()
except LedgerError as exc:
    st.error(str(exc))
except (sqlite3.Error,OSError) as exc:
    logging.exception('Storage error')
    st.error('本地文件访问失败，请检查磁盘空间与目录权限。详细信息已写入 logs/app.log。')
except Exception:
    logging.exception('Unexpected application error')
    st.error('操作未完成，请刷新后重试；详细信息已写入 logs/app.log。')
