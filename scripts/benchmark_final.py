from pathlib import Path
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from labledger import runtime
import numpy as np
import pandas as pd
from labledger.science import describe,clean
from labledger.db import Store
ROOT=Path(__file__).resolve().parents[1]
rng=np.random.default_rng(77); frame=pd.DataFrame({'x':rng.normal(size=10000),'g':np.tile(['A','B'],5000)})
fields=[{'name':'x','type':'数字'},{'name':'g','type':'文本'}]; start=time.perf_counter(); describe(frame[['x']]); stats=time.perf_counter()-start
start=time.perf_counter(); clean(frame,fields,{'operation':'中位数填充','column':'x','groups':['g']}); cleaning=time.perf_counter()-start
s=Store(ROOT/'final_optimization/experiments/benchmark.sqlite3'); p=s.create_project('synthetic benchmark'); d=s.create_dataset(p,'synthetic',fields)
start=time.perf_counter(); s.save_frame(p,d,frame); save=time.perf_counter()-start
start=time.perf_counter(); counts=s.workspace_counts(); count=time.perf_counter()-start
evidence={'rows':10000,'seed':77,'seconds':{'describe':stats,'conditional_cleaning':cleaning,'save_with_version':save,'sql_counts':count},'counts':counts,'scope':'one warm local run, not a throughput guarantee or stress test'}
(ROOT/'final_optimization/reports/performance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8'); print(evidence)
