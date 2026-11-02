#!/usr/bin/env python3
"""Package-specific lands transcribed from the cited manufacturer drawings."""
from pathlib import Path
import json,hashlib,shutil,requests
P=Path(__file__).resolve().parent;F=P/'footprints';F.mkdir(exist_ok=True)
source={}
def make(name,w,h,pads,url,note):
 s=[f'(module {name} (layer F.Cu) (tedit 0) (attr smd)',f'(descr "{note}; {url}")',f'(fp_text reference REF** (at 0 {-h/2-1}) (layer F.SilkS) (effects (font (size .8 .8) (thickness .12))))',f'(fp_text value {name} (at 0 {h/2+1}) (layer F.Fab) (effects (font (size .8 .8) (thickness .12))))']
 for layer,extra,width in [('F.Fab',0,.1),('F.CrtYd',.25,.05)]:
  x=w/2+extra;y=h/2+extra
  for a,b in [((-x,-y),(x,-y)),((x,-y),(x,y)),((x,y),(-x,y)),((-x,y),(-x,-y))]:s.append(f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer {layer}) (width {width}))')
 for pad in pads:
  n,x,y,pw,ph,*opt=pad;shape='circle' if opt and opt[0]=='circle' else 'rect';layers=opt[1] if len(opt)>1 else '*.Cu F.Paste F.Mask';layers=layers.replace('*.Cu','F.Cu');s.append(f'(pad "{n}" smd {shape} (at {x} {y}) (size {pw} {ph}) (layers {layers}))')
 s.append(')');(F/(name+'.kicad_mod')).write_text('\n'.join(s)+'\n');source[name]={'url':url,'method':'Manufacturer drawing transcribed','drawing':note}
# BQ25616 RTW:2.7mm thermal copper,signal0.28x0.85,outer4.8,0.5pitch.
pads=[]
for n in range(1,25):
 side=(n-1)//6;i=(n-1)%6
 if side==0:x,y,dx,dy=-1.975,-1.25+i*.5,.85,.28
 elif side==1:x,y,dx,dy=-1.25+i*.5,1.975,.28,.85
 elif side==2:x,y,dx,dy=1.975,1.25-i*.5,.85,.28
 else:x,y,dx,dy=1.25-i*.5,-1.975,.28,.85
 pads.append((n,x,y,dx,dy))
pads.append((25,0,0,2.7,2.7,'rect','F.Cu F.Mask'))
for x in [-.7,.7]:
 for y in [-.7,.7]:pads.append(('',x,y,1.1,1.1,'rect','F.Paste'))
make('TI_RTW0024_BQ25616',4.8,4.8,pads,'https://www.ti.com/lit/ds/symlink/bq25616.pdf','RTW4211120-3D05/15:2.7EP,0.5pitch,4x1.1pasteapertures;EPthermalviasrequiresfilledcappedifinpad')
# TPS22950 exactYBH0006-C02: topviewA1upperleft,0.4pitch,0.2mmNSMDcopper.
make('TI_YBH0006_C02',.726,1.126,[(row+str(col+1),(-.2,.2)[col],(-.4,0,.4)[i],.2,.2,'circle','F.Cu F.Mask') for i,row in enumerate('ABC') for col in range(2)]+[('',x,y,.21,.21,'circle','F.Paste') for x in [-.2,.2] for y in [-.4,0,.4]],'https://www.ti.com/lit/ds/symlink/tps22950.pdf','YBH0006-C02drawing4226594A03/2021;NSMD0.20copper;0.21pasteaperturesand75umstencilassemblyreview')
f=F/'TI_YBH0006_C02.kicad_mod'
f.write_text(f.read_text().replace('(layers F.Cu F.Mask))','(layers F.Cu F.Mask) (solder_mask_margin .04))'))
# TPS63070 RNM0015A physical15pin,overlapping7/8and12/13same-netcopperbridges.
pads=[(i,-1.15,-.75+(i-1)*.5,.6,.25) for i in range(1,5)]
pads += [(5,-.725,1.4,.25,.6),(6,-.225,1.4,.25,.6),(7,.275,1.4,.25,.6),(8,.775,1.4,.25,.6),(9,.775,.5,1.35,.25),(10,.6,0,1.7,.25),(11,.775,-.5,1.35,.25),(12,.775,-1.4,.25,.6),(13,.275,-1.4,.25,.6),(14,-.225,-1.4,.25,.6),(15,-.725,-1.4,.25,.6),(7,.525,1.225,.75,.25),(13,.525,-1.225,.75,.25)]
make('TI_RNM0015A',3,3.4,pads,'https://www.ti.com/lit/ds/symlink/tps63070.pdf','RNM0015A4222000B03/2020;physicalpadnumberspreserved;7/8and12/13same-netbridge;assemblymask/stencildrawingreviewrequired')
make('Coilcraft_XFL4020',4.3,4.3,[(1,-1.185,0,.98,3.4),(2,1.185,0,.98,3.4)],'https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf','745-3Rev03/10/26:0.98x3.4pads,2.37centerpitch;4.0±.3body')
make('Kingbright_APTF1616',2.6,1.6,[(1,.875,.5,.85,.5),(2,-.875,.5,.85,.5),(3,-.875,-.5,.85,.5),(4,.875,-.5,.85,.5)],'https://www.kingbrightusa.com/images/catalog/spec/aptf1616lseezgkqbkc.pdf','DSAO4453V9B03/19/2025p1:2.6x1.5landextent,0.9horizontalgap;pin1commonanodebottomright')
# NexperiaCFP3/SOD123W:manufacturer2023datasheetp9,viewedreflowdrawing20-02-28.
pads=[]
for n,x in [(1,-1.4),(2,1.4)]:
 pads.extend([(n,x,0,1.2,1.2,'rect','F.Cu'),('',x,0,1.4,1.4,'rect','F.Mask'),('',x,0,1.1,1.1,'rect','F.Paste')])
make('Nexperia_CFP3_SOD123W',4.4,2.1,pads,'https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf','Manufacturer2023p9sod123w_fr20-02-28:2.8padcenterpitch,1.2squarecopper,1.4mask,1.1paste,100umstencil;1K2A')
# Copyalready-source-pinnedKiCadpassiveandpackagefootprints.
d=json.loads((P/'power-circuit.json').read_text())
old=next(a for a in Path(__file__).resolve().parents if (a / 'hardware/glove-v4').is_dir()) / 'hardware/glove-v3/electrical/footprints'
for p in d['parts']:
 lib,name=p['footprint'].split(':');dst=F/(name+'.kicad_mod')
 if not dst.exists() and (old/dst.name).exists():shutil.copyfile(old/dst.name,dst)
 if not dst.exists():
  url=f'https://raw.githubusercontent.com/KiCad/kicad-footprints/7ebfa6b23cc292a56f751b7b5f4a0e12eeef69dd/{lib}.pretty/{name}.kicad_mod'
  resp=requests.get(url,timeout=25)
  if resp.status_code==200:dst.write_bytes(resp.content)
  else:print('MISSING',name,resp.status_code);continue
 if name not in source:source[name]={'url':f'https://raw.githubusercontent.com/KiCad/kicad-footprints/7ebfa6b23cc292a56f751b7b5f4a0e12eeef69dd/{lib}.pretty/{name}.kicad_mod','method':'Existing source-pinnedKiCadlibrary or retained V3customswitch','drawing':'Compare manufacturerpackage inpower-circuit.json'}
for name,d in source.items():d['sha256']=hashlib.sha256((F/(name+'.kicad_mod')).read_bytes()).hexdigest()
(P/'footprint-sources.json').write_text(json.dumps(source,indent=2)+'\n')
print(len(source),'footprintsources')
