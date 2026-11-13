from __future__ import annotations
from dataclasses import dataclass, asdict
from io import BytesIO
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib import font_manager
from .analysis import numeric, trend
from .errors import LedgerError

PALETTES = {'海盐青':['#0e9285','#4c70d6','#eea23b','#b86ab9'], '深海蓝':['#3b68d9','#45b6ba','#e6aa45','#db7089'], '暖日橙':['#e88c30','#d85569','#549f92','#697ac7']}

@dataclass
class ChartConfig:
    x: str
    y: str
    kind: str = '折线图'
    group: str | None = None
    title: str = '实验数据图表'
    xlabel: str = ''
    ylabel: str = ''
    palette: str = '海盐青'
    marker: str = 'circle'
    grid: bool = True
    legend: bool = True
    width: int = 1000
    height: int = 480
    fit: bool = False
    date_x: bool = False
    numeric_x: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

def prepare(frame: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    c = config
    needed = [c.x,c.y]+([c.group] if c.group else [])
    if any(n not in frame.columns for n in needed):
        raise LedgerError('图表字段不存在，请重新配置。')
    if c.kind not in ('折线图','柱状图','散点图') or c.palette not in PALETTES:
        raise LedgerError('图表类型或颜色主题无效。')
    data = frame.copy()
    data[c.y] = numeric(data[c.y])
    if c.date_x:
        data[c.x] = pd.to_datetime(data[c.x],errors='coerce')
    elif c.numeric_x:
        data[c.x] = numeric(data[c.x])
    data = data.dropna(subset=[c.x,c.y])
    if c.group:
        data[c.group] = data[c.group].fillna('（未分组）').astype(str)
    if c.kind == '折线图':
        data = data.sort_values(c.x, kind='stable')
    return data

def plot(frame: pd.DataFrame, config: ChartConfig) -> go.Figure:
    c = config
    data = prepare(frame,c)
    options = dict(data_frame=data,x=c.x,y=c.y,color=c.group,title=c.title,color_discrete_sequence=PALETTES[c.palette])
    if c.kind=='折线图':
        fig = px.line(**options,markers=True)
    elif c.kind=='柱状图':
        fig = px.bar(**options,barmode='group')
    else:
        fig = px.scatter(**options)
    fig.update_traces(marker_symbol=c.marker) if c.kind!='柱状图' else None
    if c.fit and (c.numeric_x or c.date_x):
        groups = data.groupby(c.group,sort=False) if c.group else [('全部',data)]
        for label, subset in groups:
            result = trend(subset,c.x,c.y,c.date_x)
            if result:
                fit_x = pd.to_datetime(result['x'],unit='D') if c.date_x else result['x']
                order = np.argsort(result['x'])
                fig.add_scatter(x=np.asarray(fit_x)[order],y=np.asarray(result['predicted'])[order],mode='lines',name=f'{label} · 趋势',line={'dash':'dash'})
    fig.update_layout(template='plotly_white',height=c.height,width=c.width,showlegend=c.legend,
                      font={'family':'Microsoft YaHei, sans-serif','color':'#27405d'},
                      margin={'l':40,'r':24,'t':65,'b':45},paper_bgcolor='white',plot_bgcolor='white',
                      xaxis_title=c.xlabel or c.x,yaxis_title=c.ylabel or c.y,
                      legend_title_text=c.group or '',title_font_size=20)
    fig.update_xaxes(showgrid=c.grid,gridcolor='#edf1f6')
    fig.update_yaxes(showgrid=c.grid,gridcolor='#edf1f6')
    return fig

def png(frame: pd.DataFrame, config: ChartConfig) -> bytes:
    c = config
    data = prepare(frame,c)
    font = next((f.name for f in font_manager.fontManager.ttflist if f.name in ('Microsoft YaHei','SimHei','Noto Sans CJK SC')), 'DejaVu Sans')
    with matplotlib.rc_context({'font.family':font,'axes.unicode_minus':False}):
        fig = Figure(figsize=(c.width/100,c.height/100),dpi=100,layout='constrained')
        ax = fig.subplots()
        groups = list(data.groupby(c.group,sort=False)) if c.group else [(c.y,data)]
        for i,(label,subset) in enumerate(groups):
            color=PALETTES[c.palette][i%4]
            if c.kind=='柱状图':
                # Numeric and categorical x share aligned category slots, matching Plotly grouping.
                categories=list(dict.fromkeys(data[c.x].astype(str)))
                pos=np.array([categories.index(str(v)) for v in subset[c.x]])
                width=.8/max(1,len(groups))
                ax.bar(pos-.4+width*(i+.5),subset[c.y],width,label=str(label),color=color)
                ax.set_xticks(range(len(categories)),categories)
            else:
                marker={'circle':'o','square':'s','diamond':'D'}[c.marker]
                if c.kind=='折线图':
                    ax.plot(subset[c.x],subset[c.y],marker=marker,label=str(label),color=color)
                else:
                    ax.scatter(subset[c.x],subset[c.y],marker=marker,label=str(label),color=color)
            if c.fit and (c.numeric_x or c.date_x):
                result=trend(subset,c.x,c.y,c.date_x)
                if result:
                    fit_x=pd.to_datetime(result['x'],unit='D') if c.date_x else result['x']
                    order=np.argsort(result['x'])
                    # Bar axes use category positions; a continuous fit would misrepresent them.
                    if c.kind!='柱状图':
                        ax.plot(np.asarray(fit_x)[order],np.asarray(result['predicted'])[order],'--',color=color,label=f'{label} · 趋势')
        ax.set(title=c.title,xlabel=c.xlabel or c.x,ylabel=c.ylabel or c.y)
        ax.grid(c.grid,alpha=.15)
        ax.set_axisbelow(True)
        if c.legend and len(data):
            ax.legend()
        output=BytesIO()
        fig.savefig(output,format='png',dpi=100)
        return output.getvalue()
