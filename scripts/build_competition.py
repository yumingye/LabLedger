"""Build an allowlisted submission and verify every payload byte."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'交付成果'

def main():
    files=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.py','.md','.txt','.ps1','.ini')]
    for directory in ['labledger','tests','docs','.streamlit','demo/templates','final_optimization/reports']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log','.db','.sqlite3','.bundle'))
    for name in ['env.ps1','migrate_v2.py','browser_competition.py','build_competition.py','independent_verify.py','deployment_smoke.py','benchmark_final.py']:
        path=ROOT/'scripts'/name
        if path.exists(): files.append(path)
    files.extend(p for p in (ROOT/'reports').glob('*') if p.name in ('junit-v2.xml','pytest-v2.txt','browser-v2.json','v2-safety.json','licenses.json'))
    video=ROOT/'demo/recordings/LabLedger_Competition_Final_Demo.mp4'
    if video.exists(): files.append(video)
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    content=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
    archive=OUT/'LabLedger_Competition_Final.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in files: z.write(path,path.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST_SHA256.json',content)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(manifest)+1
        for row in manifest:
            data=z.read(row['path']); assert len(data)==row['size'] and hashlib.sha256(data).hexdigest()==row['sha256']
        assert not any('/.venv/' in '/'+n or n.endswith(('.sqlite3','.db','.env','.log','.pyc')) for n in z.namelist())
    sha=hashlib.sha256(archive.read_bytes()).hexdigest(); manifest_sha=hashlib.sha256(content).hexdigest()
    lines=f'{sha}  {archive.name}\n{manifest_sha}  MANIFEST_SHA256.json (inside ZIP)\n'
    bundle=OUT/'LabLedger_Competition_History.bundle'
    if bundle.exists(): lines+=f'{hashlib.sha256(bundle.read_bytes()).hexdigest()}  {bundle.name}\n'
    (OUT/'LabLedger_Competition_Final_SHA256.txt').write_text(lines,encoding='utf-8')
    result={'status':'PASS','archive':str(archive),'files':len(manifest)+1,'payload_files':len(manifest),'bytes':archive.stat().st_size,'sha256':sha,'manifest_sha256':manifest_sha,'all_payload_hashes':'PASS','all_sizes':'PASS','CRC':'PASS'}
    (OUT/'competition-package-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
