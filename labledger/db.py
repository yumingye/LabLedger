"""SQLite persistence. Every dataset operation is scoped to its owning project."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator
import pandas as pd
from .errors import LedgerError
from .validation import missing, validate_schema

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS datasets(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL
                REFERENCES projects(id) ON DELETE CASCADE, name TEXT NOT NULL, schema_json TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0, UNIQUE(project_id,name));
            CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, dataset_id INTEGER NOT NULL
                REFERENCES datasets(id) ON DELETE CASCADE, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS dashboards(project_id INTEGER PRIMARY KEY REFERENCES projects(id)
                ON DELETE CASCADE, config TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS records_dataset ON records(dataset_id);
            CREATE TABLE IF NOT EXISTS project_meta(project_id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY, dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE, revision INTEGER NOT NULL, payload TEXT NOT NULL, schema_json TEXT NOT NULL, operation TEXT NOT NULL, parameters TEXT NOT NULL, created_at TEXT NOT NULL, actor TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE, dataset_id INTEGER, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS versions_dataset_revision ON versions(dataset_id,revision);
            CREATE INDEX IF NOT EXISTS history_project ON history(project_id,id);
            ''')
            db.execute('PRAGMA user_version=2')
            # Backfill existing data without changing any original records.
            for ds in db.execute('SELECT * FROM datasets WHERE NOT EXISTS (SELECT 1 FROM versions WHERE dataset_id=datasets.id)').fetchall():
                if not db.execute('SELECT 1 FROM versions WHERE dataset_id=?',(ds['id'],)).fetchone():
                    rows=[json.loads(r[0]) for r in db.execute('SELECT payload FROM records WHERE dataset_id=? ORDER BY id',(ds['id'],))]
                    db.execute('INSERT INTO versions(dataset_id,revision,payload,schema_json,operation,parameters,created_at,actor) VALUES(?,?,?,?,?,?,?,?)',(ds['id'],ds['revision'],json.dumps(rows,ensure_ascii=False),ds['schema_json'],'V1迁移基线','{}',now(),'本地用户'))

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        except sqlite3.IntegrityError as exc:
            raise LedgerError('名称重复或关联数据不存在，请检查输入。') from exc
        finally:
            db.close()

    @staticmethod
    def name(value: str) -> str:
        value = value.strip()
        if not value or len(value) > 100:
            raise LedgerError('名称需为 1–100 字。')
        return value

    def projects(self) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM projects ORDER BY updated_at DESC,id DESC')]

    def create_project(self, name: str) -> int:
        with self.connect() as db:
            stamp = now()
            return db.execute('INSERT INTO projects(name,created_at,updated_at) VALUES(?,?,?)',
                              (self.name(name),stamp,stamp)).lastrowid

    def rename_project(self, pid: int, name: str) -> None:
        with self.connect() as db:
            if not db.execute('UPDATE projects SET name=?,updated_at=? WHERE id=?', (self.name(name),now(),pid)).rowcount:
                raise LedgerError('实验项目不存在。')
        self.log(pid,None,'实验修改',{'name':name})

    def delete_project(self, pid: int) -> None:
        with self.connect() as db:
            db.execute('DELETE FROM projects WHERE id=?', (pid,))

    def datasets(self, pid: int) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM datasets WHERE project_id=? ORDER BY id', (pid,))]

    def create_dataset(self, pid: int, name: str, fields: list[dict]) -> int:
        schema = json.dumps(validate_schema(fields), ensure_ascii=False)
        with self.connect() as db:
            did = db.execute('INSERT INTO datasets(project_id,name,schema_json) VALUES(?,?,?)', (pid,self.name(name),schema)).lastrowid
            db.execute('UPDATE projects SET updated_at=? WHERE id=?', (now(),pid))
            return did

    def dataset(self, pid: int, did: int) -> dict:
        with self.connect() as db:
            row = db.execute('SELECT * FROM datasets WHERE project_id=? AND id=?', (pid,did)).fetchone()
            if row is None:
                raise LedgerError('数据集不存在或不属于当前实验。')
            return dict(row)

    def frame(self, pid: int, did: int) -> pd.DataFrame:
        return self.dataset_snapshot(pid, did)[1]

    def dataset_snapshot(self, pid: int, did: int) -> tuple[dict, pd.DataFrame]:
        with self.connect() as db:
            db.execute('BEGIN')
            dataset = db.execute(
                'SELECT * FROM datasets WHERE project_id=? AND id=?', (pid, did)
            ).fetchone()
            if dataset is None:
                raise LedgerError('数据集不存在或不属于当前实验。')
            fields = json.loads(dataset['schema_json'])
            rows = [json.loads(r['payload']) for r in db.execute('SELECT payload FROM records WHERE dataset_id=? ORDER BY id', (did,))]
        return dict(dataset), pd.DataFrame(rows, columns=[f['name'] for f in fields])

    def save_frame(self, pid: int, did: int, frame: pd.DataFrame, revision: int | None = None, operation: str = '数据录入/导入', parameters: dict | None = None, fields: list | None = None) -> None:
        dataset = self.dataset(pid,did)
        schema = validate_schema(fields) if fields is not None else json.loads(dataset['schema_json'])
        names = [f['name'] for f in schema]
        if set(frame.columns) != set(names):
            raise LedgerError('数据列必须与字段定义完全一致。')
        # Keep raw strings (including invalid data); normalize only missing cells.
        payloads = [json.dumps({n: None if missing(row[n]) else str(row[n]) for n in names}, ensure_ascii=False) for row in frame.to_dict('records')]
        with self.connect() as db:
            expected = dataset['revision'] if revision is None else revision
            # Acquire the write lock while testing revision, before replacing any rows.
            updated = db.execute('UPDATE datasets SET revision=revision+1 WHERE id=? AND project_id=? AND revision=?', (did,pid,expected)).rowcount
            if not updated:
                raise LedgerError('数据已被其他窗口修改，请刷新后重试。')
            db.execute('DELETE FROM records WHERE dataset_id=?', (did,))
            db.executemany('INSERT INTO records(dataset_id,payload) VALUES(?,?)', [(did,p) for p in payloads])
            db.execute('UPDATE projects SET updated_at=? WHERE id=?', (now(),pid))
            schema_json=json.dumps(schema,ensure_ascii=False)
            db.execute('UPDATE datasets SET schema_json=? WHERE id=?',(schema_json,did))
            db.execute('INSERT INTO versions(dataset_id,revision,payload,schema_json,operation,parameters,created_at,actor) VALUES(?,?,?,?,?,?,?,?)',(did,expected+1,'['+','.join(payloads)+']',schema_json,operation,json.dumps(parameters or {},ensure_ascii=False),now(),'本地用户'))
            db.execute('INSERT INTO history(project_id,dataset_id,kind,payload,created_at) VALUES(?,?,?,?,?)',(pid,did,operation,json.dumps(parameters or {},ensure_ascii=False),now()))

    def save_dashboard(self, pid: int, config: dict) -> None:
        with self.connect() as db:
            db.execute('INSERT INTO dashboards VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET config=excluded.config', (pid,json.dumps(config,ensure_ascii=False)))
            db.execute('UPDATE projects SET updated_at=? WHERE id=?', (now(),pid))
        self.log(pid,None,'参数修改/仪表盘保存',config)

    def dashboard(self, pid: int) -> dict:
        with self.connect() as db:
            row = db.execute('SELECT config FROM dashboards WHERE project_id=?', (pid,)).fetchone()
            return json.loads(row['config']) if row else {'columns': 2, 'charts': []}

    def metadata(self, pid: int) -> dict:
        with self.connect() as db:
            row=db.execute('SELECT payload FROM project_meta WHERE project_id=?',(pid,)).fetchone()
            return json.loads(row[0]) if row else {}

    def set_metadata(self, pid: int, payload: dict) -> None:
        with self.connect() as db:
            db.execute('INSERT INTO project_meta VALUES(?,?) ON CONFLICT(project_id) DO UPDATE SET payload=excluded.payload',(pid,json.dumps(payload,ensure_ascii=False)))
            db.execute('UPDATE projects SET updated_at=? WHERE id=?',(now(),pid))
        self.log(pid,None,'实验修改',payload)

    def log(self, pid: int, did: int | None, kind: str, payload: dict) -> None:
        if did is not None: self.dataset(pid,did)
        with self.connect() as db:
            db.execute('INSERT INTO history(project_id,dataset_id,kind,payload,created_at) VALUES(?,?,?,?,?)',(pid,did,kind,json.dumps(payload,ensure_ascii=False,default=str),now()))

    def history(self, pid: int) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM history WHERE project_id=? ORDER BY id DESC',(pid,))]

    def versions(self, pid: int, did: int) -> list[dict]:
        self.dataset(pid,did)
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM versions WHERE dataset_id=? ORDER BY id DESC',(did,))]

    def restore_version(self, pid: int, did: int, vid: int, revision: int) -> None:
        version=next((v for v in self.versions(pid,did) if v['id']==vid),None)
        if version is None: raise LedgerError('版本不属于当前数据集。')
        fields=json.loads(version['schema_json'])
        self.save_frame(pid,did,pd.DataFrame(json.loads(version['payload']),columns=[f['name'] for f in fields]),revision,'恢复版本',{'version_id':vid},fields)

    def backup(self, destination: Path) -> None:
        destination=Path(destination)
        if destination.resolve()==self.path.resolve(): raise LedgerError('备份路径不能与数据库相同。')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as source, sqlite3.connect(destination) as target: source.backup(target)

    def workspace_counts(self) -> dict:
        with self.connect() as db:
            return {table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('projects','datasets','records')}

    def delete_dataset(self,pid: int,did: int) -> None:
        self.dataset(pid,did)
        with self.connect() as db:
            db.execute('DELETE FROM datasets WHERE id=? AND project_id=?',(did,pid))
            row=db.execute('SELECT config FROM dashboards WHERE project_id=?',(pid,)).fetchone()
            if row:
                config=json.loads(row[0]); config['charts']=[c for c in config.get('charts',[]) if c.get('dataset_id')!=did]
                db.execute('UPDATE dashboards SET config=? WHERE project_id=?',(json.dumps(config,ensure_ascii=False),pid))
        self.log(pid,None,'数据集删除',{'dataset_id':did,'note':'已封存数字档案的独立输入保留在操作历史中'})
