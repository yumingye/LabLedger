import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from labledger.db import Store

@pytest.fixture
def fields():
    return [{'name':'时间','type':'数字','min':0,'max':100}, {'name':'测量','type':'数字'}, {'name':'组','type':'文本'}, {'name':'日期','type':'日期'}]

@pytest.fixture
def dataset(tmp_path,fields):
    store=Store(tmp_path/'test.sqlite3')
    pid=store.create_project('中文实验')
    did=store.create_dataset(pid,'观测表',fields)
    return store,pid,did
