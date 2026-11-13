"""Create a reproducible source/evidence archive with verified SHA256 entries."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def main() -> None:
    output=ROOT/'交付成果';output.mkdir(exist_ok=True)
    roots=['labledger','tests','scripts','docs','demo','reports','screenshots','.streamlit']
    files=[f for f in ROOT.iterdir() if f.is_file() and (f.suffix in ('.py','.md','.txt','.ps1') or f.name=='.gitignore')]
    for name in roots:
        files.extend(f for f in (ROOT/name).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc',) and f.name not in ('pytest-output.txt','ui-diagnostic.txt','browser-diagnostic.txt'))
    # Include only the final verified recording, not failed-run video fragments.
    files=[f for f in files if not ('recordings' in f.parts and f.suffix=='.webm') and not f.name.startswith('restart-diagnostic-')]
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    manifest='\n'.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(ROOT).as_posix()}' for f in files)+'\n'
    (output/'SHA256SUMS.txt').write_text(manifest,encoding='utf-8')
    archive=output/'LabLedger_Final_Submission.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for f in files:z.write(f,f.relative_to(ROOT).as_posix())
        z.writestr('SHA256SUMS.txt',manifest.encode('utf-8'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for line in manifest.splitlines():
            digest,name=line.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'LabLedger_Final_Submission.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='utf-8')
    result={'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files),'sha256':digest,'crc':'PASS','all_entries_sha256':'PASS'}
    (output/'package-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
