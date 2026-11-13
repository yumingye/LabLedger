from __future__ import annotations
import numpy as np
import pandas as pd
from .validation import valid_number

def numeric(series: pd.Series) -> pd.Series:
    result = pd.to_numeric(series, errors='coerce')
    return result.where(result.map(valid_number))

def statistics(frame: pd.DataFrame, fields: list[dict]) -> pd.DataFrame:
    rows = []
    for field in fields:
        if field['type'] != '数字':
            continue
        raw = frame[field['name']]
        s = numeric(raw)
        rows.append({'字段': field['name'], '总量': len(raw), '有效数值': int(s.count()),
                     '缺失值': int(raw.fillna('').astype(str).str.strip().eq('').sum()),
                     '无效或缺失': int(s.isna().sum()), '均值': s.mean(), '中位数': s.median(),
                     '最小值': s.min(), '最大值': s.max(), '标准差': s.std(ddof=1), '方差': s.var(ddof=1)})
    return pd.DataFrame(rows)

def trend(frame: pd.DataFrame, x: str, y: str, date_x: bool = False) -> dict | None:
    xs = (pd.to_datetime(frame[x], errors='coerce') - pd.Timestamp('1970-01-01')).dt.total_seconds()/86400 if date_x else numeric(frame[x])
    ys = numeric(frame[y])
    valid = xs.notna() & ys.notna()
    xs, ys = xs[valid], ys[valid]
    if len(xs) < 2 or xs.nunique() < 2:
        return None
    slope, intercept = np.polyfit(xs, ys, 1)
    residual = float(((ys-(slope*xs+intercept))**2).sum())
    total = float(((ys-ys.mean())**2).sum())
    ordered = pd.DataFrame({'x':xs,'y':ys}).sort_values('x', kind='stable')
    first, last = float(ordered.y.iloc[0]), float(ordered.y.iloc[-1])
    return {'slope':float(slope), 'intercept':float(intercept), 'r2':1-residual/total if total else 1.,
            'rate_percent':(last-first)/abs(first)*100 if first else None, 'n':len(xs),
            'x':xs.tolist(), 'predicted':(slope*xs+intercept).tolist()}

def recommendations(frame: pd.DataFrame, fields: list[dict], report: dict) -> list[str]:
    numeric_fields = [f['name'] for f in fields if f['type']=='数字']
    dates = [f['name'] for f in fields if f['type']=='日期']
    messages = ['智能规则推荐：基于字段类型、IQR 和最小二乘法计算，未使用大模型服务。']
    if dates and numeric_fields:
        messages.append(f'建议用「{dates[0]}」与「{numeric_fields[0]}」生成折线图观察时间变化。')
    if len(numeric_fields)>1:
        messages.append(f'建议用「{numeric_fields[0]}」与「{numeric_fields[1]}」生成散点图观察关联。')
        result = trend(frame,*numeric_fields[:2])
        if result:
            messages.append(f'线性趋势：斜率 {result["slope"]:.4g}，R²={result["r2"]:.3f}（{result["n"]} 对有效数据）。相关性不代表因果关系。')
    if report['issues']:
        messages.append(f'发现 {len(report["issues"])} 项质量提示，请先检查原始记录；IQR 仅为候选提示。')
    if not len(frame):
        messages.append('当前没有记录，请录入或导入 CSV 后开始分析。')
    return messages
