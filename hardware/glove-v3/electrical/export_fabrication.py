"""Export manufacturing files only after the routed board passes KiCad DRC."""
from pathlib import Path
import argparse,json,subprocess,hashlib,os
P=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',default='kicad-cli');ap.add_argument('--output',type=Path,default=P/'manufacturing');args=ap.parse_args()
report=json.loads((P/'routing-verification.json').read_text())
assert report['drc_pass'], 'KiCad DRC must pass before fabrication export'
assert report['counts'].get('unconnected pads')==0, 'All nets must be connected'
assert report['canonical_sha256']==hashlib.sha256((P/'components.json').read_bytes()).hexdigest(), 'Canonical components changed after routing verification'
out=args.output;out.mkdir(parents=True,exist_ok=True);board=str(P/'glove-v3-routed.kicad_pcb')
assert report['board_sha256']==hashlib.sha256(Path(board).read_bytes()).hexdigest(), 'Board changed after routing verification'
for folder in ('gerbers','drill'):(out/folder).mkdir(parents=True,exist_ok=True)
def run(*a):subprocess.run([args.kicad_cli,*a,board],check=True)
run('pcb','export','gerbers','--output',str(out/'gerbers')+'/', '--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts','--subtract-soldermask')
run('pcb','export','drill','--output',str(out/'drill')+'/','--format','excellon','--excellon-units','mm','--excellon-separate-th','--generate-map','--map-format','pdf')
run('pcb','export','pos','--output',str(out/'component-positions.csv'),'--format','csv','--units','mm','--side','both')
files=[p for p in out.rglob('*') if p.is_file() and p.name!='manifest.json']
manifest={'board':Path(board).name,'board_sha256':hashlib.sha256(Path(board).read_bytes()).hexdigest(),'canonical_sha256':report['canonical_sha256'],'files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print('Manufacturing export:',len(files),'files at',out)
