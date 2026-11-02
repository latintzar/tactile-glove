#!/usr/bin/env python3
"""Compile and execute the exact V4 core used in the target firmware."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path(tempfile.gettempdir())/'tactile-v4-native');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
cmd=['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-g',str(root/'tools/tactile_v4/test_core.cpp'),'-o',str(a.output/'test_core')]
subprocess.run(cmd,check=True)
r=subprocess.run([str(a.output/'test_core'),str(a.output/'actual-core.bin'),str(root/'hardware/glove-v3/verification/signal-chain/piezo-to-firmware.csv')],check=True,capture_output=True,text=True)
report=json.loads(r.stdout)
http_cmd=['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-g','-I',str(root/'tools/tactile_v4'),str(root/'tools/tactile_v4/test_http.cpp'),'-o',str(a.output/'test_http')]
subprocess.run(http_cmd,check=True)
http=subprocess.run([str(a.output/'test_http'),str(a.output/'actual-core.bin.browser-status')],check=True,capture_output=True,text=True)
report.update(json.loads(http.stdout))
report['sanitizers']=['ASan','UBSan']
sources=['firmware/tactile_v4/main/core.hpp','firmware/tactile_v4/main/shutdown.hpp','firmware/tactile_v4/main/http.cpp','firmware/tactile_v4/main/http.hpp','firmware/tactile_v4/main/packet.hpp','firmware/tactile_v4/main/video_frame.hpp','firmware/tactile_v3/tactile_v3_protocol.h','firmware/tactile_v3/button_control.h','tools/tactile_v4/test_core.cpp','tools/tactile_v4/test_http.cpp','tools/tactile_v4/http_native_stubs.hpp','hardware/glove-v3/verification/signal-chain/piezo-to-firmware.csv']
report['sources']={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in sources}
report['fixtures']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.glob('actual-core.bin*')}
(a.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
