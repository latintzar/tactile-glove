"""Run with the KiCad7 Python environment; this does not edit the input board."""
from pathlib import Path
import subprocess,sys
p=Path(__file__).parent;board=Path(sys.argv[1]).resolve()
def run(*args):subprocess.run([sys.executable,*map(str,args)],check=True)
run(p/'power-model/run_audit.py',board,p/'power-results')
for step in [.1,.075]:run(p/'plane_dc_current_audit.py',board,p/'power-results'/('vbus-inlet-'+str(step)+'.json'),step,p/'vbus-inlet-config.json')
run(p/'audit_usb_pair.py',board,p/'usb-pair-audit.json')
run(p/'finalize_review.py',board)
