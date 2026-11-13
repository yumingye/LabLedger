import numpy as np
import pandas as pd
from .db import Store

FIELDS=[{'name':'时间/min','type':'数字','min':0,'max':100},
        {'name':'温度/℃','type':'数字','min':0,'max':100},
        {'name':'实验组','type':'文本'}, {'name':'观测日期','type':'日期'}, {'name':'备注','type':'文本'}]

def load_demo(store: Store) -> int:
    pid=store.create_project('冷却曲线研究 · 模拟数据')
    did=store.create_dataset(pid,'两组温度观测（模拟）',FIELDS)
    rng=np.random.default_rng(42)
    rows=[]
    for group,rate in [('A · 自然冷却',.045),('B · 风冷',.075)]:
        for t in range(0,61,3):
            rows.append({'时间/min':str(t),'温度/℃':str(round(23+58*np.exp(-rate*t)+rng.normal(0,.7),2)),
                         '实验组':group,'观测日期':'2026-11-01','备注':'程序生成的模拟实验数据'})
    rows[8]['温度/℃']='115'
    rows[12]['温度/℃']=None
    rows[16]['观测日期']='2026-02-30'
    rows.append(rows[5].copy())
    store.save_frame(pid,did,pd.DataFrame(rows))
    base={'dataset_id':did,'x':'时间/min','y':'温度/℃','group':'实验组','numeric_x':True}
    store.save_dashboard(pid,{'columns':2,'charts':[{**base,'kind':k,'title':f'{k} · 模拟冷却实验'} for k in ['折线图','柱状图','散点图']]})
    return pid
