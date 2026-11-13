from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from labledger.db import Store
from labledger.demo import load_demo

@pytest.fixture
def app(tmp_path,monkeypatch):
    path=tmp_path/'ui.db';monkeypatch.setenv('LABLEDGER_DB',str(path))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30)

def assert_clean(app):
    assert not app.exception
    assert not app.error

def test_empty_and_load_demo(app):
    app.run();assert_clean(app)
    next(b for b in app.button if b.label=='一键加载模拟实验').click().run()
    assert_clean(app)
    assert len(app.metric)==4 and app.metric[0].value=='43'

@pytest.mark.parametrize('page',['数据记录','质量中心','统计分析','图表工坊','仪表盘','导出中心'])
def test_all_pages(app,page):
    app.run()
    next(b for b in app.button if b.label=='一键加载模拟实验').click().run()
    app.radio(key='page').set_value(page).run()
    assert_clean(app)

def test_create_project_and_rename(app):
    app.run()
    next(t for t in app.text_input if t.label=='实验名称').set_value('真实交互测试')
    next(b for b in app.button if b.label=='创建实验').click().run()
    assert_clean(app)
    next(t for t in app.text_input if t.label=='修改实验名称').set_value('改名完成')
    next(b for b in app.button if b.label=='保存名称').click().run()
    assert_clean(app)
    assert app.selectbox(key='active_project').value==1

def test_record_forms_and_dashboard(app):
    app.run()
    next(b for b in app.button if b.label=='一键加载模拟实验').click().run()
    app.radio(key='page').set_value('数据记录').run()
    app.text_input(key='add_1_时间/min').set_value('63')
    app.text_input(key='add_1_温度/℃').set_value('25')
    app.text_input(key='add_1_实验组').set_value('测试组')
    app.text_input(key='add_1_观测日期').set_value('2026-11-12')
    app.text_input(key='add_1_备注').set_value('中文新增')
    next(b for b in app.button if b.label=='新增记录').click().run()
    assert_clean(app);assert app.metric[0].value=='44'
    app.text_input(key='upd_1_0_温度/℃').set_value('78.5')
    next(b for b in app.button if b.label=='更新该行').click().run();assert_clean(app)
    assert app.text_input(key='upd_1_0_温度/℃').value=='78.5'
    app.checkbox(key='delconfirm_1').check().run()
    next(b for b in app.button if b.label=='删除该行').click().run()
    assert_clean(app);assert app.metric[0].value=='43'
    app.radio(key='page').set_value('仪表盘').run()
    next(r for r in app.radio if r.label=='布局列数').set_value(3)
    next(b for b in app.button if b.label=='保存布局').click().run()
    assert_clean(app)
    assert next(r for r in app.radio if r.label=='布局列数').value==3

def test_same_name_projects_remain_selected(app):
    app.run()
    next(b for b in app.button if b.label=='一键加载模拟实验').click().run()
    next(b for b in app.button if b.label=='一键加载模拟实验').click().run()
    assert app.selectbox(key='active_project').value==2
    app.radio(key='page').set_value('仪表盘').run()
    assert_clean(app)
    assert app.selectbox(key='active_project').value==2
