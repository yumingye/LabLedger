"""Plotly interactive charts and offline Matplotlib PNG/SVG renderers."""
from io import BytesIO
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
from matplotlib.figure import Figure
from matplotlib import font_manager
from .analysis import numeric
from .science import correlation, regression
from .errors import LedgerError

KINDS=['折线图','柱状图','散点图','直方图','箱线图','小提琴图','热力图','饼图','面积图','误差棒图','多组对比图','回归拟合图']

def chart_data(frame,x,y,group=None):
    d=frame.copy(); d[y]=numeric(d[y]); d=d.dropna(subset=[x,y])
    converted=numeric(d[x])
    if len(d) and converted.notna().all(): d[x]=converted
    if group: d[group]=d[group].fillna('未分组').astype(str)
    if d.empty: raise LedgerError('没有可绘制的有效数据。')
    return d

def build(frame,kind,x,y,group=None,title='实验图表',palette='蓝',width=1000,height=520,xlabel='',ylabel='',legend=''):
    d=chart_data(frame,x,y,group); color=['#2563eb','#14b8a6','#f59e0b','#a855f7'] if palette=='蓝' else ['#0f766e','#f97316','#6366f1','#ec4899']
    opts=dict(data_frame=d,x=x,y=y,color=group,color_discrete_sequence=color)
    if kind=='热力图':
        nums=d.apply(numeric).dropna(axis=1,how='all'); fig=px.imshow(correlation(nums),zmin=-1,zmax=1,color_continuous_scale='RdBu_r',text_auto='.2f')
    elif kind=='直方图': fig=px.histogram(d,x=y,color=group,color_discrete_sequence=color,nbins=25,barmode='overlay')
    elif kind=='箱线图': fig=px.box(**opts,points='outliers')
    elif kind=='小提琴图': fig=px.violin(**opts,box=True)
    elif kind=='饼图':
        values=d.groupby(x)[y].sum()
        if (values<0).any() or values.sum()<=0: raise LedgerError('饼图要求非负且总和大于零。')
        fig=px.pie(names=values.index,values=values.values,color_discrete_sequence=color)
    elif kind=='面积图':
        keys=list(dict.fromkeys([x]+([group] if group else []))); avg=d.groupby(keys,dropna=False)[y].mean().reset_index()
        fig=px.area(**{**opts,'data_frame':avg.sort_values(x)})
    elif kind=='散点图': fig=px.scatter(**opts)
    elif kind=='回归拟合图':
        result=regression(d,[x],y); fig=px.scatter(**opts)
        pairs=pd.DataFrame({'x':numeric(d[x]),'y':numeric(d[y])}).dropna().sort_values('x')
        fig.add_scatter(x=pairs.x,y=result['coefficients'][0]+result['coefficients'][1]*pairs.x,name=f'拟合 R²={result["r2"]}',mode='lines')
    elif kind in ('误差棒图','多组对比图','柱状图'):
        keys=list(dict.fromkeys([x]+([group] if group else [])))
        agg=d.groupby(keys,dropna=False)[y].agg(['mean','std','count']).reset_index()
        fig=px.bar(agg,x=x,y='mean',color=group,barmode='group',error_y='std' if kind=='误差棒图' else None,color_discrete_sequence=color,hover_data=['count'])
    else:
        keys=list(dict.fromkeys([x]+([group] if group else []))); avg=d.groupby(keys,dropna=False)[y].mean().reset_index()
        fig=px.line(**{**opts,'data_frame':avg.sort_values(x)},markers=True)
    fig.update_layout(title=title,template='plotly_white',width=width,height=height,font_family='Microsoft YaHei, sans-serif',xaxis_title=xlabel or x,yaxis_title=ylabel or y,legend_title_text=legend or group or '',colorway=color)
    if kind=='热力图': fig.update_layout(xaxis_title='数值指标',yaxis_title='数值指标')
    return fig

def static(frame,kind,x,y,group=None,title='实验图表',fmt='png',width=1000,height=520,xlabel='',ylabel='',**kwargs):
    d=chart_data(frame,x,y,group)
    font=next((f.name for f in font_manager.fontManager.ttflist if f.name in ('Microsoft YaHei','SimHei','Noto Sans CJK SC')),'DejaVu Sans')
    with matplotlib.rc_context({'font.family':font,'axes.unicode_minus':False,'svg.fonttype':'path'}):
        fig=Figure(figsize=(width/100,height/100),dpi=100,layout='constrained'); ax=fig.subplots()
        groups=list(d.groupby(group)) if group else [('全部',d)]
        if kind=='热力图':
            matrix=correlation(d.apply(numeric).dropna(axis=1,how='all')); im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='RdBu_r'); fig.colorbar(im,ax=ax)
            ax.set_xticks(range(len(matrix)),matrix.columns,rotation=35); ax.set_yticks(range(len(matrix)),matrix.index)
        elif kind in ('箱线图','小提琴图'):
            parts=list(d.groupby(group or x)); values=[s[y].to_numpy() for _,s in parts]
            if kind=='箱线图': ax.boxplot(values,tick_labels=[str(k) for k,_ in parts])
            else:
                if any(len(v)<2 or np.std(v)==0 for v in values): raise LedgerError('小提琴图每组需要至少2个非恒定值。')
                ax.violinplot(values,showmeans=True); ax.set_xticks(range(1,len(parts)+1),[str(k) for k,_ in parts])
        elif kind=='饼图':
            vals=d.groupby(x)[y].sum()
            if (vals<0).any() or vals.sum()<=0: raise LedgerError('饼图需要正总和及非负数。')
            ax.pie(vals,labels=vals.index,autopct='%1.1f%%')
        else:
            for label,subset in groups:
                subset=subset.sort_values(x)
                if kind=='直方图': ax.hist(subset[y],bins=20,alpha=.6,label=str(label))
                elif kind in ('误差棒图','柱状图','多组对比图'):
                    agg=subset.groupby(x)[y].agg(['mean','std']); pos=np.arange(len(agg)); idx=[k for k,_ in groups].index(label); w=.8/len(groups)
                    ax.bar(pos+idx*w,agg['mean'],w,yerr=agg['std'].fillna(0) if kind=='误差棒图' else None,label=str(label)); ax.set_xticks(pos+.4-w/2,agg.index.astype(str),rotation=20)
                elif kind in ('散点图','回归拟合图'):
                    ax.scatter(subset[x],subset[y],label=str(label),s=16)
                    if kind=='回归拟合图':
                        model=regression(subset,[x],y); sx=numeric(subset[x]).sort_values(); ax.plot(sx,model['coefficients'][0]+model['coefficients'][1]*sx)
                elif kind=='面积图':
                    avg=subset.groupby(x)[y].mean(); ax.fill_between(avg.index,avg.values,alpha=.4,label=str(label))
                else:
                    avg=subset.groupby(x)[y].mean(); ax.plot(avg.index,avg.values,label=str(label))
            if group: ax.legend()
        ax.set_title(title)
        if kind!='热力图': ax.set_xlabel(xlabel or x); ax.set_ylabel(ylabel or y)
        out=BytesIO(); fig.savefig(out,format=fmt); return out.getvalue()
