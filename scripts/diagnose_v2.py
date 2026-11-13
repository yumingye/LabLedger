from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-features=DevToolsDebuggingRestrictions'])
    page=b.new_page(viewport={'width':1600,'height':1000}); page.goto('http://127.0.0.1:8502'); page.wait_for_timeout(1500)
    page.get_by_text('数据清洗',exact=True).click(); page.wait_for_timeout(1200)
    ctl=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('处理操作',exact=True)); print(ctl.inner_html())
    field=ctl.get_by_role('combobox'); field.fill('删除重复行'); field.press('ArrowDown'); page.wait_for_timeout(500); print('OPTIONS',page.get_by_role('option').all_text_contents()); field.press('Enter'); page.wait_for_timeout(1000); print('VALUE',field.input_value()); print(page.locator('body').inner_text()[-1000:]); page.screenshot(path=str(ROOT/'screenshots/v2_diagnostic2.png'))
    b.close()
