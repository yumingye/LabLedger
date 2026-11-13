"""Run from the extracted ZIP's fresh venv; no development imports."""
from pathlib import Path
import json
import os
import sys
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from labledger.db import Store
from labledger.archive import replay

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-crash-reporter','--disable-breakpad','--no-first-run','--disable-features=DevToolsDebuggingRestrictions'])
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True); page.goto(os.environ['DEPLOY_URL'])
    page.get_by_role('heading',name='让每一份实验数据，都有迹可循。').wait_for()
    def check():
        page.wait_for_timeout(900); expect(page.get_by_test_id('stException')).to_have_count(0); assert '操作未完成' not in page.locator('body').inner_text()
    def nav(label): page.get_by_test_id('stSidebar').get_by_text(label,exact=True).click(); check()
    def click(label): page.get_by_role('button',name=label,exact=True).click(); check()
    if os.environ.get('DEPLOY_RESTART')!='1':
        click('加载算法性能演示'); expect(page.get_by_test_id('stMetricValue').first).to_have_text('121')
        nav('专业统计'); click('保存分析快照'); nav('数字档案'); click('封存可执行数字档案'); click('一键重新运行并核对')
        expect(page.get_by_text('重跑结果一致：所有数值在1e-9容差内通过。',exact=True)).to_be_visible()
        nav('高级图表')
        with page.expect_download() as event: click('下载高级图表 PNG')
        target=ROOT/'exports/deployment-chart.png'; event.value.save_as(target); assert target.read_bytes().startswith(b'\x89PNG')
        nav('报告中心'); click('生成完整实验报告')
        with page.expect_download() as event: click('下载报告 ZIP')
        event.value.save_as(ROOT/'exports/deployment-report.zip')
    else:
        expect(page.get_by_test_id('stMetricValue').first).to_have_text('121'); nav('数字档案'); click('一键重新运行并核对')
        expect(page.get_by_text('重跑结果一致：所有数值在1e-9容差内通过。',exact=True)).to_be_visible()
        nav('系统设置')
        with page.expect_download() as event: click('导出完整实验项目 JSON')
        target=ROOT/'exports/deployment-recovered.json'; event.value.save_as(target)
        assert any(r['kind']=='报告导出' for r in json.loads(target.read_text(encoding='utf-8'))['history'])
    check(); page.screenshot(path=str(ROOT/'reports/deployment-smoke.png')); browser.close()
store=Store(ROOT/'data/deployment.sqlite3'); p=store.projects()[0]['id']; assert store.path.resolve().is_relative_to(ROOT)
package=next(r for r in store.history(p) if r['kind']=='数字档案'); assert replay(package['payload'])['status']=='一致'
print('PASS extracted root:',ROOT,'python:',sys.executable,'restart:',os.environ.get('DEPLOY_RESTART','0'))
