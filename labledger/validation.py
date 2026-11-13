"""Non-destructive validation: retain invalid raw cells for user-led repair."""
from __future__ import annotations
from datetime import date
import math
import re
from typing import Any
import pandas as pd
from .errors import LedgerError

TYPES = ('数字', '文本', '日期')

def missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or bool(pd.isna(value))

def validate_schema(fields: list[dict]) -> list[dict]:
    if not fields:
        raise LedgerError('至少需要一个字段。')
    names = [str(f.get('name', '')).strip() for f in fields]
    if any(not n or len(n) > 80 or n.startswith('_') for n in names):
        raise LedgerError('字段名称需为 1–80 字，且不能以下划线开头。')
    if len(set(names)) != len(names):
        raise LedgerError('字段名称不能重复。')
    for field, name in zip(fields, names):
        field['name'] = name
        if field.get('type') not in TYPES:
            raise LedgerError('未知字段类型。')
        if field.get('min') is not None and field.get('max') is not None and field['min'] > field['max']:
            raise LedgerError('范围下限不能大于上限。')
    return fields

def valid_number(value: Any) -> bool:
    try:
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (ValueError, TypeError, OverflowError):
        return False

def valid_date(value: Any) -> bool:
    try:
        text = str(value)
        return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', text)) and bool(date.fromisoformat(text))
    except ValueError:
        return False

def quality(frame: pd.DataFrame, fields: list[dict]) -> dict:
    issues: list[dict] = []
    absent = 0
    for field in fields:
        name = field['name']
        values = frame[name]
        numeric = pd.to_numeric(values, errors='coerce') if field['type'] == '数字' else None
        finite = numeric[numeric.map(valid_number)] if numeric is not None else None
        limits = None
        if finite is not None and len(finite) >= 4:
            q1, q3 = finite.quantile([.25, .75])
            limits = (q1 - 1.5 * (q3-q1), q3 + 1.5 * (q3-q1))
        for row, value in enumerate(values, 1):
            reason = None
            if missing(value):
                absent += 1
                reason = '缺失值'
            elif field['type'] == '数字':
                if not valid_number(value):
                    reason = '数字类型错误'
                else:
                    number = float(value)
                    if (field.get('min') is not None and number < field['min']) or (field.get('max') is not None and number > field['max']):
                        reason = '超出设定范围'
                    elif limits and not limits[0] <= number <= limits[1]:
                        reason = 'IQR 异常值候选'
            elif field['type'] == '日期' and not valid_date(value):
                reason = '日期格式错误（应为 YYYY-MM-DD）'
            if reason:
                issues.append({'行号': row, '字段': name, '问题': reason, '原值': str(value)})
    duplicate_count = int(frame.duplicated(keep=False).sum())
    for row in range(len(frame)):
        if frame.duplicated(keep=False).iloc[row]:
            issues.append({'行号': row+1, '字段': '整行', '问题': '重复数据', '原值': ''})
    cells = len(frame) * len(fields)
    return {'rows': len(frame), 'missing': absent, 'duplicates': duplicate_count,
            'completeness': round(100*(cells-absent)/cells, 2) if cells else 0.0,
            'issues': issues}
