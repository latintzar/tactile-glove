from pathlib import Path
import importlib.util,json,re,hashlib
root=Path('[original source path]/bela-glove-hardware')
p=root/'hardware/glove-v4/verification/coupled-analog/run.py'
spec=importlib.util.spec_from_file_location('coupled',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
code,meta=m.generate('single_positive')
rows=Path('/tmp/glove-coupled-warmstart-20261023/seed.dat').read_text().splitlines()
values={k:float(v) for k,v in zip(rows[0].split(),rows[1].split())}
seeds=[]
for line in code.splitlines():
 if not line.startswith('X'):continue
 inst=line.split()[0];mpn=line.split()[-1];prefix='xamp.' if mpn=='MCP6001' else 'xopa.'
 for node,v in values.items():
  if node.startswith(prefix) and '#branch' not in node:
   seeds.append(f'.nodeset v({inst}.{node[len(prefix):]})={v:.15g}')
code=code.replace('.control','\n'.join(seeds)+'\n.control',1)
# Preserve original macro equations. All new values are Newton starting guesses,
# copied from a completed typical room-temperature operating point.
code=code.replace('.control\noption klu','.control')
path=Path('/tmp/glove-coupled-warmstart-20261023/full.cir');path.write_text(code)
meta['initialization']='Original single-amplifier DC operating points used as internal nodeset guesses; no device equation changed.'
meta['nodeset_count']=len(seeds);meta['seed_deck_sha256']=hashlib.sha256(path.with_name('seed.cir').read_bytes()).hexdigest()
path.with_name('meta.json').write_text(json.dumps(meta,indent=2)+'\n')
print('nodesets',len(seeds))
