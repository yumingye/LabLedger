"""Extract the actual ZIP, install into a NEW venv, test, launch and restart."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from urllib.request import build_opener,ProxyHandler
ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'交付成果/LabLedger_Competition_Final.zip'
target=ROOT/'final_optimization/releases'/('deploy_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')); target.mkdir(parents=True)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    manifest=json.loads(z.read('MANIFEST_SHA256.json')); assert len(z.namelist())==len(manifest)+1
    for info in z.infolist():
        path=(target/info.filename).resolve()
        assert path.is_relative_to(target.resolve()) and not info.filename.startswith(('/', '\\'))
    z.extractall(target)
for row in manifest:
    content=(target/row['path']).read_bytes(); assert len(content)==row['size'] and hashlib.sha256(content).hexdigest()==row['sha256']
env=os.environ.copy(); env.pop('PYTHONPATH',None)
for key,sub in {'TEMP':'.runtime/tmp','TMP':'.runtime/tmp','PIP_CACHE_DIR':'.cache/pip','PYTHONPYCACHEPREFIX':'.cache/pycache','MPLCONFIGDIR':'.runtime/matplotlib','USERPROFILE':'.runtime/home','APPDATA':'.runtime/appdata','LOCALAPPDATA':'.runtime/appdata'}.items():
    path=target/sub; path.mkdir(parents=True,exist_ok=True); env[key]=str(path)
env['LABLEDGER_DB']=str(target/'data/deployment.sqlite3'); env['DEPLOY_URL']='http://127.0.0.1:8510'; env['PYTHONUTF8']='1'
env['LABLEDGER_WHEELHOUSE']=str(ROOT/'final_optimization/experiments/wheels')
log_path=ROOT/'final_optimization/reports'/f'install_{target.name}.txt'
def run(args,run_env=None):
    with log_path.open('a',encoding='utf-8') as log:
        result=subprocess.run(args,cwd=target,env=run_env or env,stdout=log,stderr=log)
    if result.returncode: raise RuntimeError(f'Independent command failed ({result.returncode}); see {log_path}')
run([sys.executable,'-m','venv',str(target/'.venv')])
python=target/'.venv/Scripts/python.exe'
run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(target/'install.ps1')])
run([str(python),'-m','pip','check'])
run([str(python),'-m','pytest','-q','--basetemp=.runtime/independent-pytest','-o','cache_dir=.cache/pytest','--junitxml=reports/independent-tests.xml'])
opener=build_opener(ProxyHandler({})); processes=[]
for repeat in range(2):
    with (target/f'logs/deploy-{repeat}.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(python),'-m','streamlit','run','app.py','--server.port','8510'],cwd=target,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(process.pid)
        try:
            for _ in range(120):
                try:
                    if opener.open(env['DEPLOY_URL']+'/_stcore/health',timeout=1).status==200: break
                except OSError: time.sleep(.25)
            else: raise RuntimeError('Independent service did not start')
            env['DEPLOY_RESTART']=str(repeat)
            # The external browser driver uses the known-good host tool profile;
            # the APPLICATION and all its tests use only the extracted new venv.
            driver_env=os.environ.copy()
            for key in ('LABLEDGER_DB','DEPLOY_URL','DEPLOY_RESTART'): driver_env[key]=env[key]
            run([sys.executable,str(target/'scripts/deployment_smoke.py')],driver_env)
        finally: process.terminate(); process.wait(timeout=20)
result={'status':'PASS','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'directory':str(target),'new_virtualenv':str(python),'installed_from':'locked original wheel archives, --no-index; not copied site-packages','payload_files_verified':len(manifest),'all_sizes_and_hashes':'PASS','fresh_database':'PASS','browser_chart_report_and_dossier':'PASS','restart':'PASS','process_ids':processes,'install_log':str(log_path),'browser_driver':'external host Playwright driver; application server and full tests use only the extracted NEW venv','scope':'new venv and data in a new directory on the same Windows machine; not a second OS or machine'}
(ROOT/'final_optimization/reports/independent-deployment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False))
