from pathlib import Path
import pcbnew as k,json,re,sys
P=Path(__file__).resolve().parent;src=Path(sys.argv[1]);dst=Path(sys.argv[2]);b=k.LoadBoard(str(src));__import__("routing_layers").assert_stack(b)
assert k.ExportSpecctraDSN(b,str(dst));s=dst.read_text()
for l in ['In1.Cu','In3.Cu','In4.Cu','In6.Cu','GND_TOP','POWER_A','POWER_B','GND_BOTTOM']:s=s.replace('(layer '+l+'\n      (type signal)','(layer '+l+'\n      (type power)')
E=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware/glove-v4/electrical';parts=json.loads((E/'components.json').read_text())['components'];owners={}
for c in parts:
 for n in c['pins'].values():owners.setdefault(n,set()).add(c['subsystem'])
protected={n for n,ss in owners.items() if ss=={'tactile'}}|{'GND','VSYS','VBAT','VBAT_ENTRY','USB_CHARGER_IN','USB_VBUS','3V3_SYS','3V3_A','MAIN_L1','MAIN_L2','CHG_SW','CHG_BTST','CHG_PMID','CHG_REGN','VREF_SUPPLY'}
counts={'protected':0,'movable':0}
def wire(m):
 whole=m.group(0);n=m.group(2).strip('"');w=float(m.group(1));protect=w>=250 or n in protected;counts['protected' if protect else 'movable']+=1
 return whole.replace('(type route)','(type protect)') if protect else whole
def via(m):
 whole=m.group(0);n=m.group(1).strip('"');protect=n in protected;counts['protected' if protect else 'movable']+=1
 return whole.replace('(type route)','(type protect)') if protect else whole
s=re.sub(r'\(wire \(path \S+ ([\d.]+) .*?\)\(net (.*?)\)\(type route\)\)',wire,s,flags=re.S)
s=re.sub(r'\(via "[^"]+"  [^()]*\(net (.*?)\)\(type route\)\)',via,s)
dst.write_text(s);print(counts)
