#!/usr/bin/env python3
"""Preserve the exact target build, source hashes and pinned dependency evidence."""
import argparse,gzip,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--project',required=True,type=Path);p.add_argument('--idf',required=True,type=Path);p.add_argument('--log',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
root=a.project.parent.parent
if 'Project build complete' not in a.log.read_text():raise SystemExit('Build log has no successful completion; evidence not published')
a.output.mkdir(parents=True,exist_ok=True)
def digest(data):return hashlib.sha256(data).hexdigest()
files={'artisan_tactile_v4.bin':a.build/'artisan_tactile_v4.bin','bootloader.bin':a.build/'bootloader/bootloader.bin','partition-table.bin':a.build/'partition_table/partition-table.bin','flasher_args.json':a.build/'flasher_args.json','sdkconfig':a.project/'sdkconfig','dependencies.lock':a.project/'dependencies.lock','target-build.log.gz':a.log,'artisan_tactile_v4.map.gz':a.build/'artisan_tactile_v4.map','artisan_tactile_v4.elf.gz':a.build/'artisan_tactile_v4.elf'}
# Prove the pinned camera override is compiled, not merely present on disk.
if (a.project/'camera_override').is_dir():
 manifest_path=a.build/'camera_override/manifest.json'
 camera_manifest=json.loads(manifest_path.read_text())
 commands=json.loads((a.build/'compile_commands.json').read_text())
 compiled=[Path(row['file']).resolve() for row in commands]
 for name,expected in camera_manifest['generated_sources'].items():
  generated=(a.build/'camera_override'/name).resolve()
  if digest(generated.read_bytes())!=expected or compiled.count(generated)!=1:
   raise SystemExit('Camera override compile/source mismatch: '+name)
  if any(path.name==name and 'managed_components' in path.parts for path in compiled):
   raise SystemExit('Original managed camera source still compiled: '+name)
 files['camera-override-manifest.json']=manifest_path
artifacts={}
for name,source in files.items():
 data=source.read_bytes();stored=gzip.compress(data,mtime=0) if name.endswith('.gz') else data
 (a.output/name).write_bytes(stored);artifacts[name]={'sha256':digest(stored),'bytes':len(stored),'uncompressed_sha256':digest(data),'uncompressed_bytes':len(data)}
# Portable factory files use the flat artifact directory, while the original
# IDF flasher_args.json is preserved byte-for-byte as compiler evidence.
factory=json.loads((a.output/'flasher_args.json').read_text())
for offset in factory['flash_files']:factory['flash_files'][offset]=Path(factory['flash_files'][offset]).name
for key in ('bootloader','app','partition-table'):factory[key]['file']=Path(factory[key]['file']).name
arguments=factory['write_flash_args'][:]
for offset,name in sorted(factory['flash_files'].items(),key=lambda item:int(item[0],16)):arguments.extend([offset,name])
derived={'factory-flasher-args.json':json.dumps(factory,indent=2)+'\n','flash.args':'\n'.join(arguments)+'\n','SHA256SUMS':''.join(artifacts[name]['sha256']+'  '+name+'\n' for name in ('bootloader.bin','partition-table.bin','artisan_tactile_v4.bin'))}
for name,value in derived.items():
 data=value.encode();(a.output/name).write_bytes(data);artifacts[name]={'sha256':digest(data),'bytes':len(data),'uncompressed_sha256':digest(data),'uncompressed_bytes':len(data)}
sourcefiles=[a.project/'CMakeLists.txt',a.project/'sdkconfig.defaults',a.project/'partitions.csv']+sorted((a.project/'main').rglob('*'))+[f for f in sorted((a.project/'camera_override').rglob('*')) if f.suffix in {'.c','.h','.cmake','.py'}]+[a.project.parent/'tactile_v3/tactile_v3_protocol.h',a.project.parent/'tactile_v3/button_control.h']
sources={str(f.relative_to(root)):digest(f.read_bytes()) for f in sourcefiles if f.is_file()}
source_identity=digest(json.dumps(sources,sort_keys=True,separators=(',',':')).encode())
def output(cmd):return subprocess.check_output(cmd,text=True).strip()
report={'status':'target compile pass; hardware validation pending','created_utc':datetime.now(timezone.utc).isoformat(),'hardware_programmed':False,'idf_version':'5.4.2','idf_commit':output(['git','-C',str(a.idf),'rev-parse','HEAD']),'compiler':output(['xtensa-esp32s3-elf-gcc','--version']).splitlines()[0],'cmake':output(['cmake','--version']).splitlines()[0],'ninja':output(['ninja','--version']),'source_set_sha256':source_identity,'sources':sources,'artifacts':artifacts,'limits':['No physical radio/ADC/camera/SD timing measurement','Native tests do not execute ESP-IDF hardware drivers','Six-hour endurance and thermal behavior remain unmeasured']}
(a.output/'build-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'source_set_sha256':source_identity,'binary_sha256':artifacts['artisan_tactile_v4.bin']['sha256'],'binary_bytes':artifacts['artisan_tactile_v4.bin']['bytes']}))
