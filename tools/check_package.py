#!/usr/bin/env python3
"""Check the released file hashes and Markdown path references locally."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
inventory=json.loads((ROOT/'provenance/public-files.json').read_text())
for row in inventory['files']:
    f=ROOT/row['path']
    if f.is_symlink() or not f.is_file() or not f.resolve().is_relative_to(ROOT):
        errors.append('missing/unsafe inventory path: '+row['path']); continue
    if f.stat().st_size!=row['bytes'] or hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:
        errors.append('inventory bytes changed: '+row['path'])
links=0
for f in ROOT.rglob('*.md'):
    if any(x in f.parts for x in ['.git','.venv','node_modules']):continue
    for raw in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)',f.read_text()):
        u=urlsplit(raw.strip('<>'))
        if u.scheme or raw.startswith('//') or not u.path:continue
        links+=1;target=(f.parent/unquote(u.path)).resolve()
        if not target.is_relative_to(ROOT) or not target.exists():
            errors.append(str(f.relative_to(ROOT))+': missing '+raw)
print(json.dumps({'files':len(inventory['files']),'local_markdown_links':links,'errors':errors},indent=2))
sys.exit(bool(errors))
