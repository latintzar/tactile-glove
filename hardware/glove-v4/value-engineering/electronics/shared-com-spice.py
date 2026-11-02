#!/usr/bin/env python3
"""Bounded native ngspice check for the proposed 4067 shared-COM bus.

This is a proxy deck: four 4067 COM parasitic capacitors are placed on the
shared bus, one selected bank is represented by a voltage-controlled switch,
and the retained OPA320 positive/negative ADC paths and 22-ohm/1-nF/31-pF
loads are preserved. Switch charge injection, decoder skew, and PCB parasitics
are deliberately outside this check.
"""
from pathlib import Path
import argparse, gzip, hashlib, json, os, re, shutil, subprocess
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
VENDOR = REPO / "hardware/glove-v3/simulation/vendor"
NG = Path("/tmp/glove-eda-runtime/usr/bin/ngspice")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def deck(rmux, rsrc, label):
    # Bank 0 is enabled from time zero for precharge; the source steps at 10 us. The other three COM pins remain present as
    # explicit capacitances on the common bus, matching the proposed topology.
    # Each switch is the one 4067 RON; do not add a second series R for the COM
    # pin. The four CCOM terms are the deliberately conservative COM load.
    sources = []
    switches = []
    controls = []
    for i in range(4):
        if i == 0:
            if rsrc:
                sources.append(f"VIN{i} src{i} 0 PULSE(0 2.5 10u 1n 1n 100u 200u)")
                sources.append(f"RSRC{i} src{i} sensor{i} {rsrc}")
            else:
                sources.append(f"VIN{i} sensor{i} 0 PULSE(0.1 2.5 10u 1n 1n 100u 200u)")
        else:
            sources.append(f"VQUIET{i} sensor{i} 0 1.25")
        if i == 0:
            controls.append(f"VCTRL{i} ctrl{i} 0 5")
        else:
            controls.append(f"VCTRL{i} ctrl{i} 0 0")
        switches.append(f"SBANK{i} sensor{i} bus ctrl{i} 0 SW4067")
    caps = [f"CCOM{i} bus 0 80p" for i in range(4)]
    return f'''* Proposed V4 shared-COM 4067 bus, case={label}
.include "{VENDOR / 'OPAx320-prefixed.lib'}"
.param RMUX={rmux}
.model SW4067 SW(Ron={{RMUX}} Roff=1e12 Vt=2.5 Vh=0.1)
VDD vdd 0 3.3
VBIAS vmid 0 1.25
{chr(10).join(sources)}
{chr(10).join(controls)}
{chr(10).join(switches)}
{chr(10).join(caps)}
* Only the selected switch conducts; the four CCOM terms remain on the bus
* even when their corresponding bank is disabled.
XDRV bus driverout vdd 0 driverout opa320_OPAx320
XNEG vmid negout vdd 0 negout opa320_OPAx320
RISO driverout adcplus 22
CBUCKET adcplus 0 1n
RNEGIS negout adcminus 22
CNEGBUCKET adcminus 0 1n
RSAMPLEP adcplus sampleplus 200
CSAMPLEP sampleplus 0 31p
RSAMPLEN adcminus sampleminus 200
CSAMPLEN sampleminus 0 31p
.options method=gear reltol=1e-5 abstol=1e-12 gmin=1e-12 itl1=500 itl4=100
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran 1n 80u 0 1n
let actual_simulation_end=time[length(time)-1]
print actual_simulation_end
wrdata waveform.dat v(bus) v(driverout) v(adcplus) v(adcminus) v(sampleplus) v(sampleminus)
quit
.endc
.end
'''

def run_case(work, rmux, rsrc, settle, label):
    w = work / label
    w.mkdir(parents=True, exist_ok=True)
    d = w / "circuit.cir"
    d.write_text(deck(rmux, rsrc, label))
    log = w / "run.log"
    scripts = work.resolve() / "scripts"
    scripts.mkdir(exist_ok=True)
    cm = NG.parent.parent / "lib/x86_64-linux-gnu/ngspice"
    code_models = NG.resolve().parent.parent / "lib/x86_64-linux-gnu/ngspice"
    (scripts / "spinit").write_text("".join(f"codemodel {x}\n" for x in sorted(code_models.glob("*.cm"))) + "set ngbehavior=ps\n")
    env = {**os.environ, "SPICE_SCRIPTS": str(scripts), "LD_LIBRARY_PATH": str(NG.parent.parent / "lib/x86_64-linux-gnu")}
    with log.open("w") as f:
        try:
            p = subprocess.run([str(NG), "-b", str(d.resolve())], cwd=w.resolve(), env=env, stdout=f, stderr=subprocess.STDOUT, timeout=45)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = 124
    text = log.read_text(errors="replace")
    errors = [x for x in text.splitlines() if re.search(r"aborted|timestep too small|error:|singular matrix|no convergence", x, re.I)]
    ends = re.findall(r"actual_simulation_end\s*=\s*([-+0-9.eE]+)", text)
    out = {"case": label, "rmux_ohm": rmux, "source_ohm": rsrc, "settle_us": settle, "returncode": rc,
           "native_end_s": float(ends[-1]) if ends else None, "errors": errors[-8:], "deck_sha256": sha(d), "log_sha256": sha(log)}
    wf = w / "waveform.dat"
    if rc == 0 and wf.exists() and not errors:
        x = np.loadtxt(wf, skiprows=1)
        t = x[:, 0]
        raw_sha = sha(wf)
        gz = w / "waveform.dat.gz"
        with wf.open("rb") as src, gzip.open(gz, "wb", compresslevel=9) as dst:
            shutil.copyfileobj(src, dst)
        wf.unlink()
        out.update({"samples": int(len(x)), "waveform_sha256": raw_sha, "waveform_gz_sha256": sha(gz),
                    "waveform_file": "waveform.dat.gz", "waveform_encoding": "gzip of original ngspice wrdata text; decompress for replay",
                    "bus_min_V": float(x[:, 1].min()), "bus_max_V": float(x[:, 1].max())})
        # Positive/negative sample residual at the end of the stated wait.
        # The actual ADC differential value is sampleplus - sampleminus.
        diff = x[:, 5] - x[:, 6]
        target_t = (10 + settle) * 1e-6
        residual = float(np.interp(target_t, t, diff) - diff[-1])
        half_lsb = 3.0 / 65536.0
        out.update({"differential_final_V": float(diff[-1]), "sample_residual_V": residual,
                    "half_lsb_V": half_lsb, "sample_within_half_lsb": bool(abs(residual) <= half_lsb),
                    "native_complete": bool(abs(t[-1] - 80e-6) < 1e-12)})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    a.work = a.work.resolve()
    a.work.mkdir(parents=True, exist_ok=True)
    cases = []
    for rmux in (1000, 2000):
        cases.append(run_case(a.work, rmux, 0, 6, f"dynamic-r{rmux}"))
        cases.append(run_case(a.work, rmux, 10000, 24, f"pressure-r{rmux}"))
    hazard = {"transition": "HC139 bank code 01 to 10", "risk": "address-bit propagation skew can select an intermediate wrong decode; overlapping active-low enables are not guaranteed glitch-free", "required_sequence": ["drive the spare SN74AHC595 blank-enable bit active", "wait through decoder/output skew and switch turn-off", "preload the next bank code", "release blank-enable"], "status": "required design constraint; not covered by analog deck"}
    result = {"model": "TI OPA320 original vendor model; four 80 pF 4067 COM parasitics on common bus; retained 22 ohm/1 nF/31 pF positive and negative ADC loads",
              "cases": cases,
              "hc139_bank_transition": hazard,
              "limits": ["4067 switch charge injection omitted", "HC139 decoder propagation/skew omitted", "HC139 bank transition must blank all enables before asserting the next one", "switch off leakage and PCB parasitics omitted", "vendor op-amp model and ideal 3.3 V/1.25 V rails are not production guarantees"]}
    (a.work / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
