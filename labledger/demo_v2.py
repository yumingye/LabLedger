from pathlib import Path
import numpy as np
import pandas as pd
from .exports import csv_bytes

NOTICE='本数据为软件功能展示用合成数据，不代表真实实验测量结果。'
FIELDS=[{'name':name,'type':kind} for name,kind in [('算法名称','文本'),('输入规模','数字'),('实验轮次','数字'),('运行时间','数字'),('内存占用','数字'),('实验环境','文本'),('时间戳','日期')]]

def algorithm_frame():
    rng=np.random.default_rng(2026); rows=[]
    for algorithm,factor in [('算法A',1.0),('算法B',.7),('算法C',1.3)]:
        for size in [100,500,1000,5000]:
            for repeat in range(1,11):
                rows.append([algorithm,size,repeat,round(factor*size*np.log2(size)/1000*rng.normal(1,.08),4),round(size*factor/100+rng.uniform(1,3),3),'合成演示环境',f'2026-11-{repeat:02d}'])
    frame=pd.DataFrame(rows,columns=[f['name'] for f in FIELDS]); frame.loc[5,'运行时间']=np.nan; frame.loc[13,'运行时间']=9999
    return pd.concat([frame,frame.iloc[[2]]],ignore_index=True)

def load_algorithm_demo(store):
    pid=store.create_project('算法性能对比 · 合成演示'); did=store.create_dataset(pid,'三种算法重复测量',FIELDS)
    store.set_metadata(pid,{'实验目标':'比较相同输入规模下算法的平均耗时与稳定性','实验分类':'算法性能','实验状态':'进行中','数据来源':NOTICE,'实验方法':'三种算法、四种输入规模、每条件10次重复；固定种子2026。','实验环境':'仅用于展示的合成环境'})
    store.save_frame(pid,did,algorithm_frame(),operation='合成演示数据导入',parameters={'seed':2026,'notice':NOTICE})
    return pid

def write_templates(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    (root/'算法性能示例.csv').write_bytes(csv_bytes(algorithm_frame()))
    (root/'物理实验示例.csv').write_bytes(csv_bytes(pd.DataFrame({'时间秒':[0,1,2],'位移米':[0,4.9,19.6],'轮次':[1,1,1],'环境':['合成演示']*3})))
    (root/'化学实验示例.csv').write_bytes(csv_bytes(pd.DataFrame({'浓度mol_L':[.1,.2,.3],'吸光度':[.12,.24,.36],'温度摄氏度':[25]*3,'轮次':[1]*3})))
    (root/'字段说明.md').write_text('# 演示数据与模板\n\n'+NOTICE+'\n\n算法：算法名称（文本）、输入规模（整数）、实验轮次（重复标识）、运行时间（ms）、内存占用（MB）、实验环境（文本）、时间戳（日期）。\n物理：时间秒、位移米、轮次、环境。\n化学：浓度mol_L、吸光度、温度摄氏度、轮次。\n模板全部为合成示例；算法文件含缺失、重复和极端值以展示清洗。',encoding='utf-8')
