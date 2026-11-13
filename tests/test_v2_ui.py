from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from labledger.db import Store
from labledger.demo_v2 import load_algorithm_demo
from labledger.v2_ui import PAGES

@pytest.mark.parametrize('page',list(PAGES))
def test_v2_pages(tmp_path,monkeypatch,page):
    path=tmp_path/'ui.db'; monkeypatch.setenv('LABLEDGER_DB',str(path)); load_algorithm_demo(Store(path))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    app.radio(key='page').set_value(page).run()
    assert not app.exception and not app.error

def test_clean_preview_save(tmp_path,monkeypatch):
    path=tmp_path/'ui.db'; monkeypatch.setenv('LABLEDGER_DB',str(path)); store=Store(path); p=load_algorithm_demo(store); d=store.datasets(p)[0]['id']
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    app.radio(key='page').set_value('数据清洗').run()
    next(s for s in app.selectbox if s.label=='处理操作').set_value('删除重复行').run()
    next(b for b in app.button if b.label=='预览处理结果').click().run()
    assert len(store.frame(p,d))==121
    next(b for b in app.button if b.label=='保存为新版本').click().run()
    assert not app.error and len(store.frame(p,d))==120
