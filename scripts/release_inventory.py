"""Inventory current distributable files, scan history, validate links and SHA256.

Run with --seal after reports stop changing. No credentials are printed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/final-release-20261113'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--seal', action='store_true')
args = parser.parse_args()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

files = sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode('utf-8').split('\0')) - {''})
files = [f for f in files if (ROOT/f).is_file()]
patterns = {
    'github_token': r'gh[pousr]_[A-Za-z0-9]{30,}',
    'github_pat': r'github_pat_[A-Za-z0-9_]{50,}',
    'private_key': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
    'aws_access': r'AKIA[A-Z0-9]{16}',
    'openai_key': r'sk-(?:proj-)?[A-Za-z0-9_-]{30,}',
}
# Derive identities locally; never embed personal identity in public source.
personal = {email for email in git('log','--all','--format=%ae%n%ce').decode().splitlines()
            if email and not email.endswith('@users.noreply.github.com')}
hits = []
for name in files:
    raw = (ROOT/name).read_bytes()
    if b'\0' in raw[:8192]:
        continue
    text = raw.decode('utf-8', errors='replace')
    for kind, pattern in patterns.items():
        if re.search(pattern, text): hits.append({'path': name, 'kind': kind})
    if any(email in text for email in personal): hits.append({'path': name, 'kind': 'personal_identity'})

history = git('rev-list', '--all').decode().splitlines()
objects = git('rev-list', '--objects', '--all').decode('utf-8', errors='replace').splitlines()
history_hits = []
for entry in objects:
    oid, _, name = entry.partition(' ')
    if git('cat-file', '-t', oid).strip() != b'blob': continue
    raw = git('cat-file', 'blob', oid)
    if b'\0' in raw[:8192]: continue
    text = raw.decode('utf-8', errors='replace')
    for kind, pattern in patterns.items():
        if re.search(pattern, text): history_hits.append({'object': oid, 'path': name, 'kind': kind})
    if any(email in text for email in personal): history_hits.append({'object': oid, 'path': name, 'kind': 'personal_identity'})

links = []
for label, target in re.findall(r'\[([^\]]*)\]\(([^)]+)\)', (ROOT/'README.md').read_text(encoding='utf-8')):
    if re.match(r'https?://', target):
        if target.startswith('http://127.0.0.1:'):
            links.append({'label':label,'target':target,'status':'NOT APPLICABLE','scope':'documented local address, startup verified separately'})
        else:
            try:
                with urlopen(target, timeout=20) as response:
                    links.append({'label':label,'target':target,'status':'PASS' if response.status == 200 else 'FAIL','http':response.status})
            except Exception as exc:
                links.append({'label':label,'target':target,'status':'BLOCKED','error':str(exc)})
    else:
        path = ROOT/unquote(target.split('#')[0])
        links.append({'label':label,'target':target,'status':'PASS' if path.exists() else 'FAIL'})

result = {'files':len(files),'commits_including_tool_refs':len(history),'current_sensitive_hits':hits,
          'history_blob_hits':history_hits,'readme_links':links,
          'scope':'Pattern scan of candidate text and all reachable historical text blobs. Binary media require visual review; not a complete vulnerability audit.'}
(OUT/'inventory-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
if args.seal:
    # Inventory and seal are generated once after every mutable report is finalized.
    manifest = '# 最终仓库文件清单\n\n'+str(len(files))+' 个可分发文件；排除 .git、原始身份快照、数据库、缓存、运行环境和本地历史 Bundle。\n\n'
    manifest += '公开历史依用户授权从干净发布快照开始；原始历史本地保留。\n\n| 路径 | 字节数 |\n|---|---:|\n'
    manifest += '\n'.join('| '+f+' | '+('自身/哈希清单不计固定字节数' if f in ('docs/FINAL_REPOSITORY_MANIFEST.md','docs/FINAL_RELEASE_SHA256.txt') else str((ROOT/f).stat().st_size))+' |' for f in files)+'\n'
    (ROOT/'docs/FINAL_REPOSITORY_MANIFEST.md').write_text(manifest, encoding='utf-8')
    files = sorted(set(files) | {'docs/FINAL_REPOSITORY_MANIFEST.md'})
    checksum = ROOT/'docs/FINAL_RELEASE_SHA256.txt'
    files = [f for f in files if f != 'docs/FINAL_RELEASE_SHA256.txt']
    checksum.write_text(''.join(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()+'  '+f+'\n' for f in files), encoding='utf-8')
    for line in checksum.read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ',1)
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    print('SHA256 PASS', len(files), 'files; checksum file itself excluded')
print(json.dumps({'files':len(files),'sensitive_hits':len(hits),'history_blob_hits':len(history_hits),'broken_local_links':sum(x['status']=='FAIL' for x in links)}))
