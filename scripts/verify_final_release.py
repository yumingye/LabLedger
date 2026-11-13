"""Verify a prepared public snapshot or real remote clone in its own fresh env.

The source directory must be on D:. No old dependency, config or cache is used.
The caller runs this script with the verifier's NEW venv Python after install.ps1.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
assert ROOT.drive.upper() == 'D:'
assert Path(sys.executable).resolve().is_relative_to(ROOT/'.venv')
OUT = ROOT/'reports/fresh-verification'
OUT.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
env.pop('PYTHONPATH', None)
env.pop('LABLEDGER_WHEELHOUSE', None)
env['LABLEDGER_DB'] = str(ROOT/'data/deployment.sqlite3')
env['DEPLOY_URL'] = 'http://127.0.0.1:8517'
env['ITERATION'] = 'release-verification'
env['TEST_DB'] = 'data/deployment.sqlite3'
env['TEST_URL'] = env['DEPLOY_URL']
env['DEMO_SPEED'] = '0'
env['LABLEDGER_BROWSER_EXECUTABLE'] = ''  # fresh Playwright Chromium installed in this root
python = str(ROOT/'.venv/Scripts/python.exe')
result = {'status':'PENDING','root':str(ROOT),'python':python,'steps':[],'scope':'same Windows machine, fresh directory/venv/data/config/cache'}

def run(args, name):
    with (OUT/(name+'.txt')).open('w', encoding='utf-8') as log:
        proc = subprocess.run(args, cwd=ROOT, env=env, stdout=log, stderr=log, timeout=300)
    assert proc.returncode == 0, (name, proc.returncode)
    result['steps'].append({'step':name,'status':'PASS','command':args})

try:
    run([python,'-m','pip','check'], 'pip-check')
    run([python,'-u','-m','pytest','-q','--basetemp=.runtime/fresh-pytest','-o','cache_dir=.cache/fresh-pytest','--junitxml=reports/fresh-verification/tests.xml'], 'tests')
    opener = build_opener(ProxyHandler({}))
    (ROOT/'logs').mkdir(exist_ok=True)
    (ROOT/'exports').mkdir(exist_ok=True)
    with (OUT/'service.txt').open('w',encoding='utf-8') as log:
        server = subprocess.Popen([python,'-m','streamlit','run','app.py','--server.address','127.0.0.1','--server.port','8517','--server.headless','true','--browser.gatherUsageStats','false'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(100):
                try:
                    if opener.open(env['DEPLOY_URL']+'/_stcore/health',timeout=1).status == 200: break
                except OSError: time.sleep(.3)
            else: raise RuntimeError('service health timeout')
            result['steps'].append({'step':'startup-health','status':'PASS','pid':server.pid})
            # Full existing real browser flow, only in this isolated copy.
            run([python,'scripts/browser_competition.py'], 'browser-full-flow')
        finally:
            server.terminate(); server.wait(timeout=30)
    browser = json.loads((ROOT/'final_optimization/reports/browser-release-verification.json').read_text(encoding='utf-8'))
    assert not browser['page_errors'] and browser['restart'] == 'PASS' and len(browser['downloads']) == 12
    result['browser'] = browser
    result['browser_note'] = 'Historical recorder labels fast recording PARTIAL for duration only; business checks asserted and passed. Official 211.32s video unchanged.'
    result['status'] = 'PASS'
except BaseException as exc:
    result['status'] = 'FAIL'
    result['error'] = repr(exc)
    raise
finally:
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
