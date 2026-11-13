from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-features=DevToolsDebuggingRestrictions']); page=b.new_page(viewport={'width':1600,'height':1000}); page.goto('http://127.0.0.1:8506'); page.get_by_test_id('stMetricValue').first.wait_for()
    page.get_by_test_id('stSidebar').get_by_text('系统设置',exact=True).click(); page.wait_for_timeout(1200)
    page.get_by_test_id('stFileUploader').filter(has_text='恢复数据库备份（保留当前库副本）').locator('input').set_input_files(str(ROOT/'exports/v2/browser/LabLedger_backup.sqlite3')); page.wait_for_timeout(800)
    ctl=page.get_by_role('checkbox',name='确认替换当前数据库；恢复前自动保留当前库备份',exact=True); ctl.focus(); ctl.press('Space'); page.wait_for_timeout(800)
    page.get_by_role('button',name='执行数据库恢复',exact=True).click(); page.wait_for_timeout(2000)
    expect(page.get_by_test_id('stException')).to_have_count(0); assert '操作未完成' not in page.locator('body').inner_text(); expect(page.get_by_test_id('stMetricValue').first).to_have_text('120'); b.close()
print('PASS actual database upload and restore in Edge')
