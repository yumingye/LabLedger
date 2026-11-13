"""Anonymous HTTP verification; no login cookies or Authorization header."""
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
repo = 'https://github.com/yumingye/LabLedger'
checks = []

def fetch(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent':'LabLedger-Anonymous-Release-Verification'}), timeout=45) as response:
                return response.status, response.read(), response.headers.get('Content-Type')
        except OSError:
            if attempt == 2: raise
            time.sleep(2)

status, content, mime = fetch('https://api.github.com/repos/yumingye/LabLedger')
meta = json.loads(content)
assert status == 200 and meta['private'] is False and meta['default_branch'] == 'main'
checks.append({'url':meta['html_url'],'status':'PASS','http':status,'visibility':'public','default_branch':'main'})
status, content, mime = fetch(repo)
assert status == 200 and b'README' in content and b'LabLedger' in content
checks.append({'url':repo,'status':'PASS','http':status,'readme_html':'PASS'})
for name in ['README.md','docs/FINAL_ACCEPTANCE_REPORT.md','demo/recordings/LabLedger_Competition_Final_Demo.mp4']:
    url='https://raw.githubusercontent.com/yumingye/LabLedger/main/'+name
    status, content, mime = fetch(url)
    assert status == 200
    expected = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    actual = hashlib.sha256(content).hexdigest()
    assert actual == expected, name
    checks.append({'url':url,'status':'PASS','http':status,'bytes':len(content),'sha256':actual,'mime':mime})
(OUT/'public-access.json').write_text(json.dumps({'status':'PASS','authentication':'none; no Authorization header or cookies','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print('ANONYMOUS PUBLIC ACCESS PASS',len(checks),'checks including exact video SHA256')
