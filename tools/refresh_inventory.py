#!/usr/bin/env python3
"""Explicitly refresh public file hashes after reviewed, intentional source edits."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


def refresh(root: Path) -> dict:
    root = root.resolve()
    inventory = root / 'provenance/public-files.json'
    document = json.loads(inventory.read_text())
    previous = {row['path']: row for row in document['files']}
    if len(previous) != len(document['files']):
        raise ValueError('duplicate paths in the existing inventory')
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=root)
    files = []
    seen = set()
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        git_mode, _, stage = metadata.decode().split()
        relative = os.fsdecode(raw_path)
        if relative == 'provenance/public-files.json':
            continue
        path = root / relative
        if stage != '0' or git_mode not in ('100644', '100755'):
            raise ValueError('resolve conflict or unsupported file type: ' + relative)
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('missing or unsafe tracked file: ' + relative)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        mode = '0o755' if git_mode == '100755' else '0o644'
        old = previous.get(relative)
        row = dict(old) if old else {'path': relative}
        if old is None:
            row.update(source_class='post-release-change', change_kind='new-public-file')
        elif digest != old['sha256'] or mode != old.get('mode', mode):
            row.setdefault('baseline_public_sha256', old['sha256'])
            row.setdefault('baseline_source_class', old['source_class'])
            row.update(source_class='post-release-change', change_kind='edited-public-file')
        row.update(bytes=len(data), sha256=digest, mode=mode)
        files.append(row)
        seen.add(relative)
    # A removed tracked file keeps its previous evidence in an explicit tombstone.
    removed = {row['path']: row for row in document.get('removed_files', [])}
    for relative in previous.keys() - seen:
        removed[relative] = dict(previous[relative], change_kind='removed-public-file')
    for relative in seen:
        removed.pop(relative, None)
    document['files'] = sorted(files, key=lambda row: row['path'])
    if removed:
        document['removed_files'] = sorted(removed.values(), key=lambda row: row['path'])
    else:
        document.pop('removed_files', None)
    # source_snapshot and all retained_source_sha256 fields remain unchanged.
    encoded = json.dumps(document, indent=2) + '\n'
    if encoded != inventory.read_text():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=inventory.parent, prefix='.public-files-', delete=False) as output:
                temporary = Path(output.name)
                output.write(encoded)
            temporary.chmod(0o644)
            temporary.replace(inventory)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {'files': len(files), 'post_release_changes': sum(row['source_class'] == 'post-release-change' for row in files), 'removed_files': len(removed)}


if __name__ == '__main__':
    print(json.dumps(refresh(Path(__file__).resolve().parents[1]), indent=2))
