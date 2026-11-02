#!/usr/bin/env python3
"""Build evidence-only tables; never edits CAD/envelopes/manifests."""
import csv, hashlib, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
V3=ROOT/'hardware/glove-v3/component-evidence'
SRC=OUT/'sources'
rows=[r for r in csv.DictReader((ROOT/'hardware/glove-v4/procurement/bom-source-plan.csv').open()) if r['scope']=='main-board']
envelopes={p['ref']:p['bounds_mm'] for p in json.loads((OUT.parent/'component-envelopes.json').read_text())['main_board']['parts']}
known={}
def add(m,h,kind,path,page,url,note):
 p=pathlib.Path(path);known[m]={'maximum_height_mm':h,'height_datum':kind,'source_file':str(p.relative_to(ROOT)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'physical_pdf_pages':page if isinstance(page,list) else [page],'primary_source_url':url,'evidence':note}
mc='https://ww1.microchip.com/downloads/en/DeviceDoc/20001733L.pdf'
for m,h,p,n in [('MCP6004T-I/ST',1.2,42,'TSSOP-14 overall A max'),('MCP6002T-I/SN',1.75,32,'SOIC-8 overall A max')]:add(m,h,'seating_plane_to_top',V3/'active/datasheets/mcp6004.pdf',p,mc,n)
add('MCP33131D-10-I/MS',1.1,'seating_plane_to_top',V3/'active/datasheets/mcp33131.pdf',53,'https://ww1.microchip.com/downloads/en/DeviceDoc/MCP33131D-Data-Sheet-DS20005947B.pdf','MSOP-10 overall A max')
for m,h,f,p,n in [('OPA320AIDBVR',1.45,'opa320',39,'DBV0005A'),('TLV75518PDBVR',1.45,'tlv755p',37,'DBV0005A'),('CD74HC4067M',2.65,'cd74hc4067',26,'DW R-PDSO-G24 overall max'),('CD74HC4052M',1.75,'cd74hc4052',49,'D R-PDSO-G16 overall max')]:add(m,h,'seating_plane_to_top',V3/f'active/datasheets/{f}.pdf',p,f'https://www.ti.com/lit/ds/symlink/{f}.pdf',n)
add('ISM330DHCXTR',.86,'package_bottom_to_top',ROOT/'hardware/glove-v4/interfaces/sources/ism330dhcx-DS13012-rev7.pdf',146,'https://www.st.com/resource/en/datasheet/ism330dhcx.pdf','Figure 24: LGA height H 0.86 MAX; solder stand-off separate')
for m in ['C0603C123J3GACAUTO','C0603C153J3GACAUTO']:add(m,.87,'body_thickness',V3/'passives/kemet-c0g-auto.pdf',[6,8],'https://yageogroup.com/content/datasheet/asset/file/KEM_C1022_C0G_AUTO_SMD','25 V code 3, 12/15 nF map to CF in Table 1A; Table 2 CF 0.80 ±0.07')
# Exact selected order-code manufacturer spec sheets, individually checked.
for r in rows:
 m=r['manufacturer_mpn'];p=SRC/(m+'.txt')
 if m.startswith(('RC0','RT0','RV0')) and p.exists():
  match=re.search(r'^\s*T\s+([\d.]+)mm\s*\+/-([\d.]+)mm',p.read_text(),re.M)
  assert match,m
  h=round(float(match[1])+float(match[2]),4)
  add(m,h,'body_thickness',p.with_suffix('.pdf'),1,'https://yageogroup.com/component-documentation/download/specsheet/'+m,'Exact MPN Dimensions T = '+match[1]+' ± '+match[2]+' mm')
# Exact selected package suffix → drawing (never use a different package in the same PDF).
ti=[('LM393LVDGKR','lm393lv',42,1.1,'DGK0008A'),('OPA4323IPWR','opa4323',57,1.2,'PW0014A'),('PCA9306DCTR','pca9306',28,1.3,'DCT0008A'),('REF3330AIDBZR','ref33',33,1.12,'DBZ0003A'),('SN74AHC595PWR','sn74ahc595',33,1.2,'PW0016A'),('SN74AXC8T245PWR','sn74axc8t245',29,1.2,'PW0024A'),('SN74LVC1G00DBVR','sn74lvc1g00',40,1.45,'DBV0005A'),('SN74LVC1G04DBVR','sn74lvc1g04',23,1.45,'DBV0005A'),('SN74LVC1G08DBVR','sn74lvc1g08',27,1.45,'DBV0005A'),('SN74LVC1G17DBVR','sn74lvc1g17',23,1.45,'DBV0005A'),('SN74LVC1G32DBVR','sn74lvc1g32',41,1.45,'DBV0005A'),('SN74LVC1G74DCUR','sn74lvc1g74',22,.9,'DCU0008A'),('TCA9535PWR','tca9535',38,1.2,'PW0024A'),('TLV3012BIDBVR','tlv3012',37,1.45,'DBV0006A'),('TPS22919DCKR','tps22919',24,1.1,'DCK0006A'),('TPS22950YBHR','tps22950',21,.4,'YBH0006-C02'),('TPS2553DBVR','tps2553',41,1.45,'DBV0006A'),('TPS63070RNMR','tps63070',39,1.,'RNM0015A'),('TUSB320LAIRWBR','tusb320lai',35,.4,'RWB0012A')]
for m in ['TPS7A2015PDBVR','TPS7A2018PDBVR','TPS7A2028PDBVR','TPS7A2033PDBVR']:ti.append((m,'tps7a20',56,1.45,'DBV0005A'))
for m,f,p,h,d in ti:
 text=(SRC/(f+'.txt')).read_text().split('\f')[p-1]
 assert d in text and re.search(r'max height',text,re.I),(m,p)
 add(m,h,'seating_plane_to_top',SRC/(f+'.pdf'),p,f'https://www.ti.com/lit/ds/symlink/{f}.pdf',d+' package outline explicitly states maximum height')
add('DMP2035U-7',1.15,'seating_plane_to_top',SRC/'DMP2035U.pdf',6,'https://www.diodes.com/assets/Datasheets/DMP2035U.pdf','SOT23 standard overall A = 0.90..1.15 mm; A2 body is not overall A')
add('TAJA685K010RNJ',1.8,'package_bottom_to_top',SRC/'TAJA685K010RNJ.pdf',1,'https://datasheets.kyocera-avx.com/TAJ.pdf','TAJ A case height H 1.60 +0.20/-0.10 mm; termination included in overall outline, solder separate')
out=[]
for r in rows:
 refs=r['refs'].split(';');m=r['manufacturer_mpn'];generic=[a for a in refs if a in envelopes and a != 'J_IMU_CUFF' and abs(envelopes[a][5]-envelopes[a][2]-3)<1e-6]
 entry={'mpn':m,'main_board_qty':len(refs),'refs':refs,'current_generic_3mm_refs':generic,'footprint':r['footprint'],'mounting_allowance_mm':None,'mounting_allowance_status':'Assembly-process solder stand-off/tolerance must be set separately before lowering CAD envelopes.'}
 if m in known:entry.update(status='manufacturer_maximum_verified',**known[m])
 elif generic:entry.update(status='remaining_primary_height_evidence',maximum_height_mm=None,primary_source_url=r['source_url'])
 else:entry.update(status='existing_specific_envelope_outside_initial_generic_audit',maximum_height_mm=None,primary_source_url=r['source_url'])
 out.append(entry)
generic_n=sum(len(e['current_generic_3mm_refs']) for e in out);covered=sum(len(e['current_generic_3mm_refs']) for e in out if e['status']=='manufacturer_maximum_verified')
summary={'generic_instances':generic_n,'generic_instances_with_manufacturer_maximum':covered,'generic_instances_remaining':generic_n-covered,'verified_mpn_count':sum(e['status']=='manufacturer_maximum_verified' for e in out),'total_main_board_mpn_count':len(out),'cad_modified':False,'mounting_allowances_released':False}
doc={'schema':'glove-package-height-evidence/v1','date_utc':'2026-10-22','scope':'Selected main-board MPNs; evidence checkpoint only. CAD remains unchanged.','policy':'Maxima include manufacturer dimensional tolerance; mounting allowance is a separate assembly-process requirement. Physical PDF pages are 1-based. Null is unresolved, not zero. Generic current envelope counts are calculated from actual published solids, excluding the deliberately specific 3 mm JST SH connector.','summary':summary,'entries':out}
(OUT/'package-heights.json').write_text(json.dumps(doc,indent=2)+'\n')
fields=['mpn','main_board_qty','status','maximum_height_mm','height_datum','mounting_allowance_mm','physical_pdf_pages','source_file','source_sha256','primary_source_url','refs']
with (OUT/'package-heights.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
 for e in out:w.writerow({k:';'.join(map(str,v)) if isinstance(v,list) else v for k,v in e.items() if k in fields})
lines=['# Package-height evidence','',f"Initial evidence covers {covered}/{generic_n} generic component instances across {summary['verified_mpn_count']} selected MPNs. {generic_n-covered} instances retain an explicit evidence gap. CAD and audited envelopes are unchanged.",'','Manufacturer maximum is distinct from solder stand-off. The mounting allowance remains unset for this evidence checkpoint; use a separately approved assembly-process limit before reducing a CAD envelope. PDF page numbers below are physical 1-based pages. Full hashes, exact references and local evidence paths are in `package-heights.json` and `package-heights.csv`.','','| Selected MPN | Qty | Maximum mm | Datum | Evidence page |','|---|---:|---:|---|---|']
for e in out:
 if e['status']=='manufacturer_maximum_verified':lines.append(f"| {e['mpn']} | {e['main_board_qty']} | {e['maximum_height_mm']:.2f} | {e['height_datum']} | [p. {','.join(map(str,e['physical_pdf_pages']))}]({e['primary_source_url']}) |")
lines+=['','## Remaining evidence','','| Selected MPN | Generic instances | Status |','|---|---:|---|']
for e in out:
 if e['status']=='remaining_primary_height_evidence':lines.append(f"| {e['mpn']} | {len(e['current_generic_3mm_refs'])} | Manufacturer height not yet verified |")
lines+=['','Download logs preserve failed exact primary URL attempts. Nexperia requests returned 403; some Murata URLs returned 403/404. Three RT0603 exact order-code sheets returned 404. These failures do not establish dimensions or invalidate the selected part. Family-equivalent heights have not been silently substituted.','']
(OUT/'README.md').write_text('\n'.join(lines));print(json.dumps(summary,indent=2))
