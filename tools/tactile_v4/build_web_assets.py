#!/usr/bin/env python3
"""Deterministic embedded device UI; retain raw source and vendor license files."""
from pathlib import Path
import gzip,hashlib,json,mimetypes
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'hardware/glove-v4/software-preview'
OUT=ROOT/'firmware/tactile_v4/main/web';OUT.mkdir(exist_ok=True)
files={('/' if p.name=='index.html' else '/'+p.name):p for p in SOURCE.iterdir() if p.suffix in ('.html','.css','.js')}
for p in (ROOT/'static/glove-viewer').iterdir():
    if p.is_file():files['/assets/'+p.name]=p
files['/index.html']=SOURCE/'index.html'
header='#pragma once\n#include <cstddef>\n#include <cstdint>\nstruct WebAsset {const char* path;const char* mime;const uint8_t* data;size_t size;};\nextern const WebAsset webAssets[];\nextern const size_t webAssetCount;\n'
(OUT/'web_assets.hpp').write_text(header)
cpp=['#include "web_assets.hpp"'];entries=[];manifest=[]
for i,(url,path) in enumerate(sorted(files.items())):
    raw=path.read_bytes();data=gzip.compress(raw,compresslevel=9,mtime=0);name=f'asset_{i}';mime='text/javascript' if path.suffix=='.js' else 'model/gltf-binary' if path.suffix=='.glb' else mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    cpp.append('static const uint8_t '+name+'[] = {'+', '.join(map(str,data))+'};')
    entries.append('{'+json.dumps(url)+','+json.dumps(mime)+','+name+',sizeof('+name+')}')
    manifest.append(dict(url=url,mime=mime,source=str(path.relative_to(ROOT)),raw_bytes=len(raw),gzip_bytes=len(data),sha256=hashlib.sha256(raw).hexdigest()))
cpp+=['const WebAsset webAssets[] = {'+',\n'.join(entries)+'};','const size_t webAssetCount=sizeof(webAssets)/sizeof(webAssets[0]);']
(OUT/'web_assets.cpp').write_text('\n'.join(cpp)+'\n')
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(len(files),'embedded routes;',sum(x['gzip_bytes'] for x in manifest),'compressed bytes')
