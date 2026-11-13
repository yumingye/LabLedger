"""Recover original downloaded wheel ZIPs from this project's pip HTTP cache."""
from pathlib import Path
import email
import json
import shutil
import zipfile
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'final_optimization/experiments/wheels'; out.mkdir(parents=True,exist_ok=True)
found=[]
for body in (ROOT/'.cache/pip').rglob('*.body'):
    if not zipfile.is_zipfile(body): continue
    with zipfile.ZipFile(body) as z:
        wheels=[n for n in z.namelist() if n.endswith('.dist-info/WHEEL')]
        if len(wheels)!=1: continue
        info=email.message_from_bytes(z.read(wheels[0])); tags=info.get_all('Tag',[])
        tag=next((t for t in tags if t.startswith('cp312-')),next((t for t in tags if t.startswith('py3-')),tags[0] if tags else None))
        if not tag: continue
        base=wheels[0].split('/')[0][:-len('.dist-info')]; build=info.get('Build')
        name=base+('-'+build if build else '')+'-'+tag+'.whl'
        target=out/name
        if not target.exists(): shutil.copy2(body,target)
        found.append(name)
(ROOT/'final_optimization/reports/cached-wheel-recovery.json').write_text(json.dumps(sorted(set(found)),indent=2),encoding='utf-8')
print('Recovered',len(set(found)),'original wheel archives from D-drive pip cache')
