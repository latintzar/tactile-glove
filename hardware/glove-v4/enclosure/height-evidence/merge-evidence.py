"""Merge reviewed primary height supplements; retain the initial evidence snapshot."""
from pathlib import Path
import json,csv,hashlib
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
base=json.loads((ROOT/'package-heights.json').read_text())
entries={q['mpn']:q.copy() for q in base['entries']}
for filename in ['mlcc-height-evidence.json','remaining-height-evidence.json','taiyo-height-evidence.json']:
 d=json.loads((ROOT/filename).read_text())
 for q in d.get('entries',[d]):
  old=entries[q['mpn']]
  for f,h in [('source_file','source_sha256'),('cached_text_file','cached_text_sha256')]:
   if q.get(f):assert hashlib.sha256((REPO/q[f]).read_bytes()).hexdigest()==q[h],q['mpn']
  old.update(q)
  old['status']='manufacturer_maximum_verified'
verified=[q for q in entries.values() if q.get('maximum_height_mm') is not None]
for q in verified:
 q['mounting_allowance_mm']=.20
 q['mounting_allowance_status']='Engineering assembly acceptance limit; measured board-to-peak must not exceed manufacturer maximum+0.20mm.'
 q['audited_height_mm']=round(q['maximum_height_mm']+.20,4)
resolved=sum(len(q.get('current_generic_3mm_refs',[])) for q in verified)
remaining=[q['mpn'] for q in entries.values() if q.get('current_generic_3mm_refs') and q.get('maximum_height_mm') is None]
out={'schema':'glove-package-heights-merged/v1','date_utc':'2026-10-22','summary':{'initial_generic_instances':545,'resolved_generic_instances':resolved,'remaining_generic_instances':545-resolved,'verified_mpn_count':len(verified),'remaining_mpn':remaining},'mounting_allowance_mm':.20,'entries':list(entries.values()),'initial_snapshot':'package-heights.json','supplements':['mlcc-height-evidence.json','remaining-height-evidence.json','taiyo-height-evidence.json']}
assert resolved==545 and not remaining,out['summary']
(ROOT/'merged-package-heights.json').write_text(json.dumps(out,indent=2)+'\n')
with (ROOT/'merged-package-heights.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['MPN','References','ManufacturerMaximum_mm','MountingAllowance_mm','AuditedHeight_mm','Datum','SourceURL','LocalEvidence','SHA256','PhysicalPDFPages'])
 for q in verified:w.writerow([q['mpn'],';'.join(q['refs']),q['maximum_height_mm'],.2,q['audited_height_mm'],q['height_datum'],q.get('primary_source_url',q.get('source_url')),q.get('source_file') or q.get('cached_text_file'),q.get('source_sha256') or q.get('cached_text_sha256'),','.join(map(str,q.get('physical_pdf_pages') or []))])
text='# Package-height evidence\n\nAll 545 former generic component instances are covered by 94 selected-MPN manufacturer maxima. The initial snapshot remains in package-heights.json; merged-package-heights.json/CSV are the current CAD inputs.\n\nEvery reduced envelope adds a separate 0.20 mm assembly allowance. This is an engineering assembly acceptance limit, not a manufacturer dimensional claim. The 15 original specific envelopes remain separately modeled; the new fuse and battery header are added by the connector revision.\n\nEvidence includes cached manufacturer PDFs, distributor-hosted manufacturer PDFs, hashed catalog extracts and clearly labeled transcriptions of manufacturer drawings where direct downloads returned 403. Exact references, source URLs, physical pages and evidence hashes are retained in the merged table.\n\n| Selected MPN | Qty | Maximum mm | Assembly envelope mm | Evidence |\n|---|---:|---:|---:|---|\n'
for q in verified:
 u=q.get('primary_source_url',q.get('source_url'));p=','.join(map(str,q.get('physical_pdf_pages') or [])) or 'catalog extract';text+=f"| {q['mpn']} | {len(q['refs'])} | {q['maximum_height_mm']:.2f} | {q['audited_height_mm']:.2f} | [p. {p}]({u}) |\n"
text+='\nRebuild the merged table with `python3 merge-evidence.py`. The original build-evidence.py only regenerates the initial snapshot.\n'
(ROOT/'README.md').write_text(text)
print(out['summary'])
