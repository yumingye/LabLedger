"""Start -> verify -> stop -> restart a real server against the saved database."""
from pathlib import Path
import json
import subprocess
import sys
import time
from urllib.request import build_opener,ProxyHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from labledger.db import Store
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
store=Store(ROOT/'data/labledger.sqlite3')
project=store.projects()[0];pid=project['id'];did=store.datasets(pid)[0]['id']
expected_rows=len(store.frame(pid,did));expected_layout=store.dashboard(pid)['columns']
opener=build_opener(ProxyHandler({}))
checks=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True,args=['--disable-features=DevToolsDebuggingRestrictions','--disable-crash-reporter'])
    for run in range(2):
        with (ROOT/f'logs/restart-{run}.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.port','8502','--server.address','127.0.0.1','--server.headless','true'],cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                for attempt in range(60):
                    try:
                        if opener.open('http://127.0.0.1:8502/_stcore/health',timeout=1).status==200:break
                    except OSError:time.sleep(.25)
                else:raise RuntimeError('Server did not become healthy')
                context=browser.new_context(viewport={'width':1440,'height':1000})
                page=context.new_page();page.goto('http://127.0.0.1:8502')
                expect(page.get_by_test_id('stMetricValue').first).to_have_text(str(expected_rows),timeout=30000)
                page.get_by_text('仪表盘',exact=True).click()
                page.wait_for_timeout(1500)
                expect(page.get_by_role('radio',name=str(expected_layout),exact=True)).to_be_checked()
                page.locator('.js-plotly-plot').first.wait_for()
                page.wait_for_timeout(1000)
                if run==1:page.screenshot(path=str(ROOT/'screenshots/10_进程重启恢复.png'))
                checks.append({'run':run+1,'pid':process.pid,'rows':expected_rows,'dashboard_columns':expected_layout,'health':200})
                context.close()
            finally:
                process.terminate();process.wait(timeout=15)
    browser.close()
assert checks[0]['pid']!=checks[1]['pid']
(ROOT/'reports/restart-verification.json').write_text(json.dumps({'status':'PASS','database':str(store.path),'project_id':pid,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: two real server processes restored',expected_rows,'rows and',expected_layout,'dashboard columns')
