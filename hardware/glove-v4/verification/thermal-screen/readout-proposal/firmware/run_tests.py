#!/usr/bin/env python3
"""Exercise the unapplied TEMP policy with host ASan/UBSan; no hardware claim."""
import argparse, ast, hashlib, json, re, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
tree=ast.parse((HERE.parent/'calculate.py').read_text())
expected=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TABLE' for t in n.targets))
header=(HERE/'thermal.hpp').read_text();table=header.split('TABLE{{')[1].split('}};')[0]
actual=[tuple(map(float,x)) for x in re.findall(r'\{(-?[0-9.]+),([0-9.]+)\}',table)]
assert actual==expected,(actual,expected)
binary=a.output/'test_thermal'
cmd=['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(HERE/'test_thermal.cpp'),'-o',str(binary)]
subprocess.run(cmd,check=True)
r=subprocess.run([str(binary)],capture_output=True,text=True,check=True)
report=json.loads(r.stdout)
report.update(status='unapplied proposal: host policy tests only',vendor_table_matches=True,
    sanitizers=['ASan','UBSan'],compile_command=cmd,
    sources={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [HERE/'thermal.hpp',HERE/'test_thermal.cpp',Path(__file__).resolve(),HERE.parent/'calculate.py']},
    limitations=['Not included in target app; canonical board has no proposed two-NTC readout.',
                'Does not exercise ADC/mux hardware, ISR timing, actuator acknowledgments or thermal response.',
                'Indicated-temperature trip settings are provisional; assembled thermal bounds remain open.'])
(a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
