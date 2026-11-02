#!/usr/bin/env python3
"""Exact two-ISM330DHCX mode-1 wiring and glove harness contract."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
DS='https://www.st.com/resource/en/datasheet/ism330dhcx.pdf'
FP='GloveV4:ST_ISM330DHCX_LGA14_0.35mm'
parts=[]
def add(ref,mpn,fp,pins,purpose,assembly,source):
 parts.append(dict(ref=ref,mpn=mpn,qty=1,footprint=fp,pins={str(k):v for k,v in pins.items()},purpose=purpose,assembly=assembly,source=source))
def capacitor(ref,net,assembly,bulk=False):
 add(ref,'GRM188R61A475KE15D' if bulk else 'GRM188R71C104KA01D','GloveV4:C_0603_1608Metric',{1:net,2:'GND'},'4.7uF 10V X5R local reservoir' if bulk else '100nF16V X7R at IMU supply pin',assembly,'https://www.murata.com/en-us/products/capacitor/mlcc')
for suffix,address,assembly in [('CUFF',0x6a,'cuff'),('HAND',0x6b,'hand-tile')]:
 local='HAND_' if suffix=='HAND' else ''
 pins={1:'3V3_SYS' if suffix=='HAND' else 'GND',2:'GND',3:'GND',4:'CUFF_IMU_INT1' if suffix=='CUFF' else 'NC',5:'3V3_SYS',6:'GND',7:'GND',8:'3V3_SYS',9:'NC',10:'NC',11:'NC',12:'3V3_SYS',13:local+'I2C_SCL',14:local+'I2C_SDA'}
 add('U_IMU_'+suffix,'ISM330DHCXTR',FP,pins,'Six-axis mode1 I2C, address '+hex(address),assembly,DS)
 capacitor('C_IMU_'+suffix+'_VDD','3V3_SYS',assembly)
 capacitor('C_IMU_'+suffix+'_IO','3V3_SYS',assembly)
 capacitor('C_IMU_'+suffix+'_BULK','3V3_SYS',assembly,True)
for suffix,assembly in [('CUFF','cuff'),('HAND','hand-tile')]:
 add('J_IMU_'+suffix,'SM04B-SRSS-TB(LF)(SN)','GloveV4:JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',{1:'GND',2:'3V3_SYS',3:'I2C_SDA',4:'I2C_SCL'},'Keyed 4-wire power and I2C, QT/Qwiic pin order',assembly,'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf')
for n in ['SDA','SCL']:
 add('R_IMU_HAND_'+n,'RC0603FR-0722RL','GloveV4:R_0603_1608Metric',{1:'I2C_'+n,2:'HAND_I2C_'+n},'22ohm series damping at hand tile connector', 'hand-tile','https://www.yageo.com/en/Chart/Download/pdf/RC0603')
d={'schema':1,'revision':'V4 dual precision IMU','parts':parts,
 'devices':[{'id':0,'role':'cuff-camera','address':106,'ref':'U_IMU_CUFF','mount':'Cuff PCB fixed rigidly to camera seat. Keep antenna/converter heat away. The camera-to-cuff transform is calibrated once after assembly.'},{'id':1,'role':'dorsal-hand','address':107,'ref':'U_IMU_HAND','mount':'Thin rigid tile in keyed soft pocket over third metacarpal, clear of knuckles. Arrow toward middle finger; plug toward wrist. The hand can move relative to the cuff at the wrist.'}],
 'acquisition':{'bus_hz':400000,'odr_hz':833,'accelerometer_full_scale_g':4,'gyroscope_full_scale_dps':1000,'accelerometer_mg_per_lsb':0.122,'gyroscope_mdps_per_lsb':35,'timestamp_tick_us':25,'timestamp_batch_decimation':8,'fifo_record_bytes':7,'fifo_capacity_records':512,'fifo_capacity_wire_bytes':3584,'fifo_read':'Long auto-increment burst 0x78..0x7e wrapping to0x78, ST AN5398 section4.7.1','poll_interval_target_ms':10,'use_hand_irq':False,'temperature':'Record sensor raw temperature and calibration temperature; manufacturer nominal256LSB/C and25Czero are not a calibrated skin temperature measurement.'},
 'harness':{'stock_cable':'Adafruit4210','source':'https://www.adafruit.com/product/4210','length_mm':100,'connector_each_end':'JST SH 4pin female, keyed','pin_order':{'1':'GND black','2':'3V3_SYS red','3':'I2C_SDA blue','4':'I2C_SCL yellow'},'routing':'Run above the back of the wrist in a fabric tunnel. Leave a shallow S loop for flexion; fasten the cable jacket8mm behind both plugs. Keep it away from high impedance PVDF leads. Disconnect power before plugging.','factory_test':'Check every conductor pin1-to-pin1 throughpin4-to-pin4 and for adjacent shorts; do not infer continuity from wire colour alone.'},
 'bus_budget':{'main_pullup_ohm':2200,'camera_pullup_ohm':2200,'capacitance_budget_pf':150,'pullup_tolerance_fraction':0.01,'allocation_pf':{'two_imus_and_expanders':45,'traces_connectors_and_levelshifter':35,'100mm_harness':30,'camera_side_reflected_and_margin':40},'note':'Capacitance allocations are design limits; verify the final routed/harness total against the300ns fast-mode rise-time limit. No extra pullups on the hand tile.'},
 'layout':{'tile_outline_mm':[16,16,0.8],'sensor_body_mm':[3,2.5,0.86],'pad1_topview':'upper-left; pins1..4 downleft,5..7bottom,8..11upright,12..14top right-to-left','supply_decoupling_distance_mm_max':1.5,'connector_at':'wrist-facing edge','mechanics':'Soft cover only over the rigid tile. No assembly glue, screw or enclosure point load on the MEMS package. The tile pocket keys rotation and has a visible toward-fingers arrow.'},
 'calibration':{'per_unit':'Boot ID/readback, factory self-test under ST procedure; six-orientation accelerometer calibration; stationary gyro offset with sensor temperature; axis/sign fixture verification; camera intrinsics/extrinsics; offset/clock fit stored with serial number.','runtime':'Retain raw samples and metadata; FIFO overrun, clock gaps, saturation and transport loss are explicit. Quiet motion tests inform stationary probability; contact pressure alone is not a zero-velocity measurement.','tracking':'A separate cuff-camera trajectory and hand orientation are estimated. Wrist flexion invalidates a fixed camera-to-hand transform. Blind position uncertainty grows until a visual/known-contact constraint becomes available.'}}
(P/'imu-interface.json').write_text(json.dumps(d,indent=2)+'\n')
print(f'{len(parts)} exact parts: cuff and keyed remote hand tile')
