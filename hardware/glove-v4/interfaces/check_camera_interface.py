#!/usr/bin/env python3
"""Independent camera interface invariants and bounded electrical calculations."""
import json,math,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
d=json.loads((P/'camera-interface.json').read_text());parts={p['ref']:p for p in d['parts']};checks=[]
def check(name,ok,detail):
    checks.append(dict(name=name,pass_=bool(ok),detail=detail))
def pins(ref):return parts[ref]['pins']
# Truth-table transcription from TI SCES875C Table7-1, not generated from circuit directions.
def directions(d1,d2,oe):
    return ['Z','Z'] if oe else {(0,0):['BA','BA'],(0,1):['BA','AB'],(1,0):['AB','AB'],(1,1):['AB','BA']}[(d1,d2)]
check('data_bank_directions',directions(1,0,0)==['AB','AB'] and pins('U_CAM_DATA')['11']=='GND','All eight image lines must travel camera A to MCU B.')
check('sync_control_bank_directions',directions(1,1,0)==['AB','BA'] and pins('U_CAM_CTRL')['11']=='CAM_DOVDD_1V8','DIR2 has opposite polarity to DIR1 in this exact IC.')
for i in range(8):check(f'data_bit_{i}',pins('U_CAM_DATA')[str(3+i)]==f'CAM_D{i}' and pins('U_CAM_DATA')[str(21-i)]==f'MCU_CAM_D{i}','Independent one-to-one mapping; no data bit permutation.')
check('camera_power_pins',[pins('J_CAM')[str(i)] for i in [4,10,11]]==['CAM_AVDD_2V8','CAM_DVDD_1V5','CAM_DOVDD_1V8'],'AVDD pin4, core pin10, I/O pin11; no reliance on old1V2 net label.')
check('camera_unused_af_pins',all(pins('J_CAM')[str(i)]=='NC' for i in [1,23,24]),'This fixed-focus camera must not receive AF power on NC pins.')
check('sccb_gate_bias',pins('U_CAM_SCCB')['7']==pins('U_CAM_SCCB')['8']=='CAM_SCCB_BIAS' and pins('R_CAM_SCCB_BIAS')=={'1':'3V3_SYS','2':'CAM_SCCB_BIAS'},'200k resistor biases EN/VREF2; these pins are not tied directly to supply.')
check('off_state_isolation',pins('U_CAM_IF_INV')['2']=='CAM_IF_EN' and pins('Q_CAM_SCCB')['1']==pins('U_CAM_IF_INV')['4'] and pins('Q_CAM_SCCB')['3']=='CAM_SCCB_BIAS','Interface low -> inverter high -> NMOS clamps SCCB gate; AXC OE pulled high.')
check('gpio_uniqueness',len(set(d['gpio'].values()))==len(d['gpio']),'Camera + I2C allocation unique.')
check('boot_strap_avoidance',not(set(d['gpio'].values())&{0,3,45,46,35,36,37}),'Avoid S3 strapping and N8R8 PSRAM reserved pins.')
# LDO +/-2% is more conservative than nominal line/load accuracy in this range.
rails={'DOVDD':(1.8*.98,1.8*1.02,1.71,2.8),'AVDD':(2.8*.98,2.8*1.02,2.6,3.0),'DVDD':(1.5*.98,1.5*1.02,1.425,1.575)}
for name,(lo,hi,spec_lo,spec_hi) in rails.items():check(name+'_supply_corner',lo>=spec_lo and hi<=spec_hi,dict(design_range_v=[lo,hi],allowed_v=[spec_lo,spec_hi]))
# Camera VOH/VOL figures are explicitly specified at nominal1.8V; don't claim they are full supply-corner bounds.
logic={'camera_voh_v':1.62,'camera_vol_v':.18,'translator_vih_max_v':.65*1.8*1.02,'translator_vil_min_v':.35*1.8*.98,'camera_input_vih_v':1.26,'camera_input_vil_v':.54,'translator_out_high_at_100ua_v':1.8*.98-.1,'translator_out_low_at_100ua_v':.1}
check('nominal_camera_output_logic_margin',logic['camera_voh_v']>logic['translator_vih_max_v'] and logic['camera_vol_v']<logic['translator_vil_min_v'],logic)
check('camera_control_static_load',1.8*1.02/47000<100e-6,'47k pulls draw <40uA, within the translator 100uA DC output specification; dynamic charging is separate.')
check('nominal_camera_input_logic_margin',logic['translator_out_high_at_100ua_v']>logic['camera_input_vih_v'] and logic['translator_out_low_at_100ua_v']<logic['camera_input_vil_v'],logic)
# I2C budgets are actual imposed design limits, not measurements of an unrouted board.
r=2200;c=100e-12
rise=.8473*r*c
sink=3.55/r+1.836/r
check('i2c_400khz_rise_budget',rise<=300e-9,dict(capacitance_budget_pf=100,rise_ns=rise*1e9,limit_ns=300))
check('shared_i2c_sink_budget',sink<.003,dict(worst_combined_sink_ma=sink*1e3,limit_ma=3,host_pullup_ohm=2200,camera_pullup_ohm=2200))
seq={e['action']:e['t_ms'] for e in d['power_up_sequence']}
check('power_up_order',seq['io_rail']<seq['analog_rail']<seq['core_rail']<seq['leave_powerdown'],'Separate20ms gaps accommodate LDO startup; LDO power-good waveform still verified on assembled board.')
check('core_to_powerdown_delay',seq['leave_powerdown']-seq['core_rail']>=5,dict(delay_ms=seq['leave_powerdown']-seq['core_rail'],minimum_ms=5))
check('powerdown_to_reset_delay',seq['release_reset']-seq['leave_powerdown']>=1,dict(delay_ms=seq['release_reset']-seq['leave_powerdown'],minimum_ms=1))
check('reset_to_sccb_delay',seq['probe_configure']-seq['release_reset']>=20,dict(delay_ms=seq['probe_configure']-seq['release_reset'],minimum_ms=20))
check('clock_before_sccb',seq['probe_configure']-seq['interface_and_clock']>=1,'24MHz source started before probe; lies in sensor6–27MHz specification.')
# Datasheet full-resolution external-core currents used as sizing envelope, not measured VGA current.
current_ma={'analog':40,'digital_core':125,'digital_io':12}
source_max_v=3.55
power={k:source_max_v*v/1000 for k,v in current_ma.items()}
report={'source_sha256':hashlib.sha256((P/'camera-interface.json').read_bytes()).hexdigest(),'check_count':len(checks),'passed':sum(c['pass_'] for c in checks),'checks':checks,'power_sizing':{'camera_datasheet_maximum_rail_current_ma':current_ma,'linear_regulator_input_power_w_at_3v55':sum(power.values()),'ldo_dissipation_w':{'AVDD':(3.55-2.744)*.04,'DVDD':(3.55-1.47)*.125,'DOVDD':(3.55-1.764)*.012}},'not_established_by_checks':['camera supplied-tail thickness/contact orientation','full sensor module operating power at selectedmode','manufactured interconnect edge rate, timing skew and EMC','LDO measured startup at capacitor corners','actual combined I2C capacitance','temperature and image quality']}
(P/'camera-interface-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"{report['passed']}/{report['check_count']} camera design checks pass")
raise SystemExit(any(not c['pass_'] for c in checks))
