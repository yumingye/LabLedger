from __future__ import annotations
from datetime import datetime
from io import BytesIO
import csv
import json
import re
import pandas as pd
from .errors import LedgerError

def import_csv(content: bytes, names: list[str]) -> pd.DataFrame:
    if len(content)>20*1024*1024:
        raise LedgerError('CSV 大小不能超过 20 MB。')
    text = None
    for encoding in ('utf-8-sig','gb18030'):
        try:
            text=content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise LedgerError('CSV 编码无法识别，请使用 UTF-8 或 GB18030。')
    try:
        parsed=list(csv.reader(text.splitlines(),strict=True))
        header=parsed[0] if parsed else []
        if len(header)!=len(set(header)) or set(header)!=set(names):
            raise LedgerError('CSV 表头必须与字段名称完全一致，且不能重复。')
        if any(len(row)!=len(header) for row in parsed[1:] if row):
            raise LedgerError('CSV 存在列数不一致的记录，请检查分隔符与引号。')
        frame=pd.read_csv(BytesIO(text.encode('utf-8')),dtype=str,keep_default_na=False)
        return frame[names]
    except (pd.errors.ParserError,pd.errors.EmptyDataError,StopIteration,csv.Error) as exc:
        raise LedgerError('无法读取 CSV，请检查分隔符、表头和引号。') from exc

def csv_bytes(frame: pd.DataFrame, safe: bool = True) -> bytes:
    data=frame.copy()
    if safe:
        # Spreadsheet formula guard; untouched source is separately available as JSON.
        for col in data:
            data[col]=data[col].map(lambda v: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@','\t','\r')) and not _number(v) else v)
    return data.to_csv(index=False,lineterminator='\n').encode('utf-8-sig')

def _number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def raw_bytes(frame: pd.DataFrame, fields: list[dict]) -> bytes:
    return json.dumps({'schema':fields,'records':frame.where(frame.notna(),None).to_dict('records')},ensure_ascii=False,indent=2,default=str).encode('utf-8')

def filename(project: str, kind: str, suffix: str) -> str:
    safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',project).strip('. ')[:60] or '实验'
    safe_kind = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', kind).strip('. ')[:60] or '导出'
    return f'{safe}_{safe_kind}_{datetime.now():%Y%m%d_%H%M%S}.{suffix}'
