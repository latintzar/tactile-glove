"""Check provenance transitions using a tiny scratch Git repository."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inventory_refresh',ROOT/'tools/refresh_inventory.py')
refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

def git(root,*args):
    subprocess.run(['git',*args],cwd=root,check=True,capture_output=True)

def read(root):
    return json.loads((root/'provenance/public-files.json').read_text())

@pytest.fixture
def repository(tmp_path):
    git(tmp_path,'init','--quiet')
    (tmp_path/'provenance').mkdir()
    original=b'original engineering bytes\n'
    (tmp_path/'part.txt').write_bytes(original)
    digest=hashlib.sha256(original).hexdigest()
    manifest={'schema':1,'source_snapshot':'f40271c6331db255bce6df60d84f0953fbe18355','files':[{'path':'part.txt','bytes':len(original),'sha256':digest,'mode':'0o644','source_class':'exact-retained-source','retained_source_sha256':digest}]}
    (tmp_path/'provenance/public-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
    git(tmp_path,'add','part.txt','provenance/public-files.json')
    return tmp_path

def test_unchanged_edit_new_and_idempotent_provenance(repository):
    before=read(repository)
    refresh.refresh(repository)
    assert read(repository)==before
    (repository/'part.txt').write_text('intentional design revision\n')
    (repository/'new.txt').write_text('new module\n')
    (repository/'tools').mkdir()
    (repository/'tools/check_package.py').write_bytes((ROOT/'tools/check_package.py').read_bytes())
    git(repository,'add','part.txt','new.txt','tools/check_package.py')
    refresh.refresh(repository)
    changed=read(repository)
    assert changed['source_snapshot']==before['source_snapshot']
    rows={row['path']:row for row in changed['files']}
    assert rows['part.txt']['source_class']=='post-release-change'
    assert rows['part.txt']['retained_source_sha256']==before['files'][0]['sha256']
    assert rows['part.txt']['baseline_public_sha256']==before['files'][0]['sha256']
    assert rows['part.txt']['baseline_source_class']=='exact-retained-source'
    assert rows['new.txt']['source_class']=='post-release-change'
    assert 'retained_source_sha256' not in rows['new.txt']
    check=subprocess.run([sys.executable,str(repository/'tools/check_package.py')],cwd=repository,capture_output=True,text=True)
    assert check.returncode==0,check.stdout+check.stderr
    frozen=(repository/'provenance/public-files.json').read_bytes()
    refresh.refresh(repository)
    assert (repository/'provenance/public-files.json').read_bytes()==frozen
    (repository/'part.txt').write_text('second intentional revision\n')
    refresh.refresh(repository)
    row=next(row for row in read(repository)['files'] if row['path']=='part.txt')
    assert row['baseline_public_sha256']==before['files'][0]['sha256']

def test_removal_keeps_prior_hash(repository):
    before=read(repository)['files'][0]
    git(repository,'rm','--force','part.txt')
    refresh.refresh(repository)
    after=read(repository)
    assert after['files']==[]
    assert after['removed_files'][0]['sha256']==before['sha256']
    assert after['removed_files'][0]['change_kind']=='removed-public-file'

def test_untracked_files_excluded_and_outside_symlink_rejected(repository,tmp_path_factory):
    (repository/'private-untracked.txt').write_text('kept outside the inventory\n')
    refresh.refresh(repository)
    assert len(read(repository)['files'])==1
    outside=tmp_path_factory.mktemp('outside')/'part.txt';outside.write_text('external\n')
    (repository/'alias.txt').symlink_to(outside)
    git(repository,'add','alias.txt')
    before=(repository/'provenance/public-files.json').read_bytes()
    with pytest.raises(ValueError):refresh.refresh(repository)
    assert (repository/'provenance/public-files.json').read_bytes()==before
