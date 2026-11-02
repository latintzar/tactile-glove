"""Retrieve public manufacturer characteristics used to size bulk capacitors."""
from pathlib import Path
import requests,json
P=Path(__file__).resolve().parent;S=P/'sources';S.mkdir(exist_ok=True)
request=[{'partnumber':n,'chara_type':'c_dcbias_capacitance','parameter':{'tc':str(t),'ac':'0.5'},'WorkInfo':{'color':'#000000','graph_set_y_name':''}} for n in ['GRM21BC81C226ME44','GRM32ER61C476KE15'] for t in [-20,25,85]]
params={'callback':'nothing','ReqType':'Characteristics','ReqChara':json.dumps(request),'CallBack':'mycallback','WorkInfo':'graph1'}
r=requests.get('https://ds.murata.com/simserve/characteristics',params=params,timeout=30);r.raise_for_status();data=r.json();(S/'mlcc-dc-bias.json').write_text(json.dumps(data,indent=2)+'\n');(S/'mlcc-request.json').write_text(json.dumps({'url':'https://ds.murata.com/simserve/characteristics','params':params,'interpretation':'Manufacturer typical characteristic, not guaranteed production limits; use tolerance, temperature and aging margin.'},indent=2)+'\n')
print(len(data.get('JsonCharaData',[])),'curves')
