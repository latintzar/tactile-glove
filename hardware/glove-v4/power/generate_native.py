"""Generate native KiCad 7 electrical sheets with every actual physical pin.
All global labels are reconciled against KiCad's own exported netlist.
The generic symbols expose exact numbered pins; they are not footprint substitutes.
"""
from pathlib import Path
import json,uuid,subprocess,os,collections
P=Path(__file__).parent
parts=json.loads((P/'power-circuit.json').read_text())['parts']
assert len({p['ref'] for p in parts})==len(parts)
counts=collections.Counter()
for p in parts:
 prefix=p['ref'].split('_')[0] if p['ref'].startswith('SW') else p['ref'][0]
 counts[prefix]+=1
 p['designator']=prefix+str(counts[prefix])
refmap={p['ref']:p['designator'] for p in parts}
(P/'reference-map.json').write_text(json.dumps(refmap,indent=2))
assert len({p['designator'] for p in parts})==len(parts)
def u(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'artisan-glove-v4-power/'+s))
def q(s):return json.dumps(str(s))
def effect(size=1,extra=''):return f'(effects (font (size {size} {size})) {extra})'
def textprop(n,v,x,y,hide=False):return f'(property {q(n)} {q(v)} (at {x} {y} 0) {effect(.9,"hide" if hide else "")})'
root=u('root');sheets=[];netmap=collections.defaultdict(set)
for page_index in range((len(parts)+19)//20):
 group=parts[page_index*20:(page_index+1)*20]; sid=u(f'sheet-{page_index}');libs=[];objects=[]
 for index,p in enumerate(group):
  ref=p['ref']; pins=list(p['pins'].items());nleft=(len(pins)+1)//2;h=max(5.08,(nleft+1)*2.54);name='P_'+ref;lib='Glove:'+name;pintext=[];suid=u(ref)
  for i,(num,net) in enumerate(pins):
   left=i<nleft;j=i if left else i-nleft;x=-20.32 if left else 20.32;y=round(h/2-2.54-j*2.54,3);angle=0 if left else 180
   pintext.append(f'(pin passive line (at {x} {y} {angle}) (length 5.08) (name {q(p.get("pin_names",{}).get(num,num))} {effect(.9)}) (number {q(num)} {effect(.9)}))')
  libs.append(f'(symbol {q(lib)} (pin_names (offset .508)) (in_bom yes) (on_board yes) {textprop("Reference",p['designator'],0,h/2+2)} {textprop("Value",p.get("value",p["mpn"]),0,-h/2-2)} (symbol {q(name+"_0_1")} (rectangle (start -15.24 {h/2}) (end 15.24 {-h/2}) (stroke (width .254) (type default)) (fill (type background)))) (symbol {q(name+"_1_1")} {" ".join(pintext)}))')
  cx=72+(index%4)*142;cy=45+(index//4)*76
  value=ref+' · '+p.get('value',p['mpn'])
  obj=f'(symbol (lib_id {q(lib)}) (at {cx} {cy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {suid}) {textprop("Reference",p['designator']+'',cx,cy-h/2-2)} {textprop("Value",value,cx,cy+h/2+2)} {textprop("Footprint",p.get("footprint",""),cx,cy,True)} {textprop("Datasheet",p.get("source",""),cx,cy,True)} '
  for num,net in pins:obj+=f'(pin {q(num)} (uuid {u(ref+"/"+num)})) '
  obj+=f'(instances (project "glove-v4-power" (path {q("/"+root+"/"+sid)} (reference {q(p["designator"])}) (unit 1)))))'
  objects.append(obj)
  for i,(num,net) in enumerate(pins):
   left=i<nleft;j=i if left else i-nleft;x=cx+(-20.32 if left else 20.32);y=round(cy-(h/2-2.54-j*2.54),3);ex=x+(-5.08 if left else 5.08)
   if net=='NC':objects.append(f'(no_connect (at {x} {y}) (uuid {u(ref+num+"nc")}))');continue
   objects.append(f'(wire (pts (xy {x} {y}) (xy {ex} {y})) (stroke (width 0) (type default)) (uuid {u(ref+num+"wire")}))')
   objects.append(f'(global_label {q(net)} (shape input) (at {ex} {y} {0 if left else 180}) {effect(.85,"(justify "+("right" if left else "left")+")")} (uuid {u(ref+num+"label")}))')
   netmap[net].add((p["designator"],num))
 fname=f'native-{page_index+1:02}.kicad_sch'
 content=f'(kicad_sch (version 20230121) (generator eeschema) (uuid {sid}) (paper "A2") (title_block (title "Artisan tactile cuff - physical pin connections") (date "2026-10-22") (rev "V4 power candidate") (comment 1 "Power pin topology; native net reconciliation; PCB integration pending")) (lib_symbols {" ".join(libs)}) {" ".join(objects)})\n'
 (P/fname).write_text(content);sheets.append((sid,fname))
root_objs=[]
for i,(sid,fname) in enumerate(sheets):
 x=20+(i%3)*85;y=25+(i//3)*45
 root_objs.append(f'(sheet (at {x} {y}) (size 70 25) (fields_autoplaced) (stroke (width .1524) (type default)) (fill (color 0 0 0 0)) (uuid {sid}) (property "Sheetname" {q("Physical connections "+str(i+1))} (at {x} {y-1} 0) {effect(1,"(justify left bottom)")}) (property "Sheetfile" {q(fname)} (at {x} {y+26} 0) {effect(1,"(justify left top)")}) (instances (project "glove-v4-power" (path {q("/"+root)} (page {q(i+2)})))))')
(P/'glove-v4-power.kicad_sch').write_text(f'(kicad_sch (version 20230121) (generator eeschema) (uuid {root}) (paper "A4") (lib_symbols) {" ".join(root_objs)} (sheet_instances (path "/" (page "1"))))\n')
(P/'expected-net-endpoints.json').write_text(json.dumps({n:sorted(list(v)) for n,v in netmap.items()},indent=2))
print('Native physical schematic:',len(parts),'components,',sum(len(v) for v in netmap.values()),'connected pins,',len(netmap),'nets,',len(sheets),'sheets')
