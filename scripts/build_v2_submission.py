"""V2 source/evidence allowlist; never touches V1 artifacts or real databases."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'交付成果'

def main():
    browser=json.loads((ROOT/'reports/browser-v2.json').read_text(encoding='utf-8'))
    assert browser['restart']=='PASS' and not browser['page_errors'] and 180<=browser['duration']<=220
    files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.py','.md','.txt','.ps1')]
    for folder in ['labledger','tests','docs','.streamlit','demo/templates']:
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    files.extend(p for p in (ROOT/'scripts').glob('*') if p.suffix in ('.py','.ps1') and not p.name.startswith('diagnose'))
    files.extend(p for p in (ROOT/'reports').glob('*') if p.name in ('browser-v2.json','junit-v2.xml','pytest-v2.txt','licenses.json','v2-safety.json'))
    files.extend((ROOT/'screenshots').glob('v2_[0-9]*.png'))
    files.append(ROOT/'demo/recordings/LabLedger_3min_真实浏览器演示_v2.mp4')
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    manifest=''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}\n' for p in files)
    archive=OUT/'LabLedger_V2_Final_Submission.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files: z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('SHA256SUMS_V2.txt',manifest)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for line in manifest.splitlines():
            digest,name=line.split('  ',1); assert hashlib.sha256(z.read(name)).hexdigest()==digest
        assert not any(n.endswith(('.sqlite3','.db','.env')) or '.venv/' in n for n in z.namelist())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (OUT/'SHA256SUMS_V2.txt').write_text(manifest+f'{digest}  {archive.name}\n',encoding='utf-8')
    evidence={'status':'PASS','archive':str(archive),'sha256':digest,'files':len(files),'bytes':archive.stat().st_size,'crc':'PASS','every_file_sha256':'PASS'}
    (OUT/'package-verification-v2.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(evidence,ensure_ascii=False))

if __name__=='__main__': main()
