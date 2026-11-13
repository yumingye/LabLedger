"""Idempotent migration with a pre-migration SQLite backup."""
from pathlib import Path
from datetime import datetime
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from labledger import runtime
from labledger.db import Store

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/labledger.sqlite3'
    if path.exists():
        backup=ROOT/'exports/v2'/f'pre_migrate_{datetime.now():%Y%m%d_%H%M%S_%f}.sqlite3'; backup.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path) as source,sqlite3.connect(backup) as target: source.backup(target)
        print('Backup:',backup)
    store=Store(path)
    with store.connect() as db: print('Schema version:',db.execute('PRAGMA user_version').fetchone()[0])
