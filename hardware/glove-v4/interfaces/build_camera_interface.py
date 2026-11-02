#!/usr/bin/env python3
"""Pin-accurate camera interface source. Values come from listed manufacturer documents."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
parts=[]
def add(ref,mpn,footprint,pins,purpose,source):
    parts.append(dict(ref=ref,qty=1,mpn=mpn,footprint=footprint,pins={str(k):v for k,v in pins.items()},purpose=purpose,source=source))
def resistor(ref,value,a,b):
    mpn={'100k':'RC0603FR-07100KL','47k':'RC0603FR-0747KL','200k':'RC0603FR-07200KL','2.2k':'RC0603FR-072K2L','33':'RC0603FR-0733RL'}[value]
    add(ref,mpn,'Resistor_SMD:R_0603_1608Metric',{1:a,2:b},value+' ohm','https://www.yageo.com/en/Chart/Download/pdf/RC0603')
def cap(ref,rail,large=False):
    add(ref,'CL21A106KAYNNNE' if large else 'GRM188R71C104KA01D','Capacitor_SMD:C_0805_2012Metric' if large else 'Capacitor_SMD:C_0603_1608Metric',{1:rail,2:'GND'},'10uF 25V X5R, effective >=1uF required' if large else '100nF 16V X7R decoupling','https://product.samsungsem.com/mlcc/CL21A106KAYNNNE.do' if large else 'https://www.murata.com/en-us/products/productdetail?partno=GRM188R71C104KA01%23')
cam_pins={1:'NC',2:'GND',3:'CAM_SDA',4:'CAM_AVDD_2V8',5:'CAM_SCL',6:'CAM_RESET_N',7:'CAM_VSYNC',8:'CAM_PWDN',9:'CAM_HREF',10:'CAM_DVDD_1V5',11:'CAM_DOVDD_1V8',12:'CAM_D7',13:'CAM_XCLK',14:'CAM_D6',15:'GND',16:'CAM_D5',17:'CAM_PCLK',18:'CAM_D4',19:'CAM_D0',20:'CAM_D3',21:'CAM_D1',22:'CAM_D2',23:'NC',24:'NC'}
add('J_CAM','FH12-24S-0.5SH(55)','Connector_FFC-FPC:Hirose_FH12-24S-0.5SH_1x24-1MP_P0.50mm_Horizontal',cam_pins,'24-contact bottom-contact 0.5mm FPC; 0.3mm cable thickness. Module tail/contact-side verification required before layout freeze.','https://www.hirose.com/product/p/CL0586-0521-0-55')
for tag,voltage,mpn in [('IO','1V8','TPS7A2018PDBVR'),('AV','2V8','TPS7A2028PDBVR'),('DV','1V5','TPS7A2015PDBVR')]:
    out={'IO':'CAM_DOVDD_1V8','AV':'CAM_AVDD_2V8','DV':'CAM_DVDD_1V5'}[tag]
    en='CAM_'+tag+'_EN'
    add('U_CAM_'+tag,mpn,'Package_TO_SOT_SMD:SOT-23-5',{1:'3V3_SYS',2:'GND',3:en,4:'NC',5:out},'Separate camera '+voltage+' regulator with active discharge','https://www.ti.com/lit/ds/symlink/tps7a20.pdf')
    resistor('R_CAM_'+tag+'_EN','100k',en,'GND')
    cap('C_CAM_'+tag+'_IN','3V3_SYS',True); cap('C_CAM_'+tag+'_OUT',out,True);cap('C_CAM_'+tag+'_HF',out)
# SN74AXC8T245 DIR2 is inverted relative to DIR1. H/L = all A->B; H/H = bits1:4 A->B, bits5:8 B->A.
base={1:'CAM_DOVDD_1V8',2:'CAM_DOVDD_1V8',11:'GND',12:'GND',13:'GND',22:'CAM_OE_N',23:'3V3_SYS',24:'3V3_SYS'}
data=dict(base)
for i in range(8):data[3+i]='CAM_D'+str(i);data[21-i]='MCU_CAM_D'+str(i)
add('U_CAM_DATA','SN74AXC8T245PWR','Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm',data,'8 data lines 1.8V camera to system MCU','https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf')
ctrl=dict(base);ctrl[11]='CAM_DOVDD_1V8'
for i,n in enumerate(['PCLK','VSYNC','HREF']):ctrl[3+i]='CAM_'+n;ctrl[21-i]='MCU_CAM_'+n
ctrl.update({6:'GND',18:'NC',7:'CAM_XCLK_BUF',17:'MCU_CAM_XCLK',8:'CAM_RESET_N',16:'MCU_CAM_RESET_N',9:'CAM_PWDN',15:'MCU_CAM_PWDN',10:'NC',14:'GND'})
add('U_CAM_CTRL','SN74AXC8T245PWR','Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm',ctrl,'3 sync lines up, XCLK/reset/powerdown down; unused input sides grounded','https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf')
resistor('R_CAM_XCLK','33','CAM_XCLK_BUF','CAM_XCLK')
for ref in ['DATA','CTRL']:
    cap('C_CAM_'+ref+'_A','CAM_DOVDD_1V8');cap('C_CAM_'+ref+'_B','3V3_SYS')
resistor('R_CAM_OE','47k','CAM_DOVDD_1V8','CAM_OE_N')
resistor('R_CAM_IF','100k','CAM_IF_EN','GND')
add('Q_CAM_OE','2N7002,215','Package_TO_SOT_SMD:SOT-23',{1:'CAM_IF_EN',2:'GND',3:'CAM_OE_N'},'Open-drain enable, keeps translator control in camera 1.8V domain','https://assets.nexperia.com/documents/data-sheet/2N7002.pdf')
# PCA9306 VREF2/EN is a transistor gate bias, NOT a push-pull 3.3V supply connection.
add('U_CAM_SCCB','PCA9306DCTR','Package_SO:SSOP-8_2.95x2.8mm_P0.65mm',{1:'GND',2:'CAM_DOVDD_1V8',3:'CAM_SCL',4:'CAM_SDA',5:'I2C_SDA',6:'I2C_SCL',7:'CAM_SCCB_BIAS',8:'CAM_SCCB_BIAS'},'SCCB voltage translation; I2C address 0x3c','https://www.ti.com/lit/ds/symlink/pca9306.pdf')
resistor('R_CAM_SCCB_BIAS','200k','3V3_SYS','CAM_SCCB_BIAS')
resistor('R_CAM_SDA','2.2k','CAM_DOVDD_1V8','CAM_SDA');resistor('R_CAM_SCL','2.2k','CAM_DOVDD_1V8','CAM_SCL')
add('U_CAM_IF_INV','74LVC1G04GW,125','Package_TO_SOT_SMD:SOT-353_SC-70-5',{1:'NC',2:'CAM_IF_EN',3:'GND',4:'CAM_IF_DISABLE',5:'3V3_SYS'},'Hardware default isolates SCCB when interface enable is low','https://assets.nexperia.com/documents/data-sheet/74LVC1G04.pdf')
cap('C_CAM_IF_INV','3V3_SYS')
add('Q_CAM_SCCB','2N7002,215','Package_TO_SOT_SMD:SOT-23',{1:'CAM_IF_DISABLE',2:'GND',3:'CAM_SCCB_BIAS'},'Clamps SCCB gate bias off until camera I/O is powered','https://assets.nexperia.com/documents/data-sheet/2N7002.pdf')
resistor('R_CAM_RESET','47k','CAM_RESET_N','GND');resistor('R_CAM_PWDN','47k','CAM_DOVDD_1V8','CAM_PWDN')
resistor('R_CAM_MCU_RESET','100k','MCU_CAM_RESET_N','GND');resistor('R_CAM_MCU_PWDN','47k','3V3_SYS','MCU_CAM_PWDN')
seq=[dict(t_ms=0,action='prepare',state={'CAM_IF_EN':0,'CAM_IO_EN':0,'CAM_AV_EN':0,'CAM_DV_EN':0,'MCU_CAM_RESET_N':0,'MCU_CAM_PWDN':1,'XCLK':0}),dict(t_ms=1,action='io_rail',state={'CAM_IO_EN':1}),dict(t_ms=21,action='analog_rail',state={'CAM_AV_EN':1}),dict(t_ms=41,action='core_rail',state={'CAM_DV_EN':1}),dict(t_ms=61,action='interface_and_clock',state={'CAM_IF_EN':1,'XCLK':24000000}),dict(t_ms=62,action='leave_powerdown',state={'MCU_CAM_PWDN':0}),dict(t_ms=64,action='release_reset',state={'MCU_CAM_RESET_N':1}),dict(t_ms=90,action='probe_configure',state={})]
d={'schema':1,'revision':'V4 camera interface','module':{'manufacturer':'CamThink','selection':'OV5640 120°FOV, 8CM preset focus','part_number_status':'Store variation identifier and exact supplied mechanical drawing still need capture','source':'https://wiki.camthink.ai/docs/hardware-dev-resources/camera-module-ov5640/','supply_choice_v':{'AVDD':2.8,'DVDD':1.5,'DOVDD':1.8},'body_mm':[8.5,8.5,6.5],'assembly_design_status':'pin-level circuit; connector tail fit and supplied variant not yet production released'},'gpio':{'MCU_CAM_D0':11,'MCU_CAM_D1':9,'MCU_CAM_D2':8,'MCU_CAM_D3':10,'MCU_CAM_D4':12,'MCU_CAM_D5':18,'MCU_CAM_D6':17,'MCU_CAM_D7':16,'MCU_CAM_XCLK':15,'MCU_CAM_PCLK':13,'MCU_CAM_VSYNC':6,'MCU_CAM_HREF':7,'I2C_SDA':4,'I2C_SCL':5},'expander_outputs':['CAM_IO_EN','CAM_AV_EN','CAM_DV_EN','CAM_IF_EN','MCU_CAM_RESET_N','MCU_CAM_PWDN'],'parts':parts,'power_up_sequence':seq,'power_down_sequence':['RESET_N low; PWDN high','stop XCLK','CAM_IF_EN low','CAM_DV_EN low; wait20ms','CAM_AV_EN low; wait20ms','CAM_IO_EN low'],'sources':{'sensor':'https://files.waveshare.com/upload/d/da/OV5640_DataSheet.pdf','translator':'https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf','ldo':'https://www.ti.com/lit/ds/symlink/tps7a20.pdf'},'layout_rules':['Continuous ground plane beneath camera data/clock, no split crossing','Buffer PCLK and data with same translator family; short matched routes, avoid analog charge inputs','Camera flex strain relief and outward heat path; connector pin1/contact side explicit in assembly drawing','100nF at every translator supply; LDO effective output capacitance >=1uF over DC bias/tolerance','3V3_SYS <=3.6V including converter ripple/transients','Host-side I2C pullups owned by main board; budget total bus capacitance and combined sink current','Stop XCLK and isolate all camera I/O before removing rail power'],'validation_scope':'Source maps and arithmetic are design checks; dynamic interface waveforms and sensor operation require target integration.'}
(P/'camera-interface.json').write_text(json.dumps(d,indent=2)+'\n')
print(f'{len(parts)} camera interface components written')
