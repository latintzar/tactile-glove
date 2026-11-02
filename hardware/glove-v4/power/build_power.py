#!/usr/bin/env python3
"""V4 exact power/controller connectivity, with manufacturer pin numbers."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
parts=[]
TI='https://www.ti.com/lit/ds/symlink/'
F={'r':'Resistor_SMD:R_0603_1608Metric','c':'Capacitor_SMD:C_0603_1608Metric','c8':'Capacitor_SMD:C_0805_2012Metric','q':'Package_TO_SOT_SMD:SOT-23','q5':'Package_TO_SOT_SMD:SOT-23-5','q6':'Package_TO_SOT_SMD:SOT-23-6'}
def add(ref,mpn,fp,pins,purpose,source,names=None,value=None):
 p=dict(ref=ref,qty=1,mpn=mpn,footprint=F.get(fp,fp),pins={str(k):v for k,v in pins.items()},purpose=purpose,source=source)
 if names:p['pin_names']={str(k):v for k,v in names.items()}
 if value:p['value']=value
 parts.append(p)
def r(ref,v,a,b,tol=1):
 if 'k' in v:code=v.rstrip('k').replace('.','K');code=code if 'K' in code else code+'K'
 elif 'M' in v:code=v.rstrip('M').replace('.','M');code=code if 'M' in code else code+'M'
 else:code=v.replace('.','R');code=code if 'R' in code else code+'R'
 add(ref,('RT0603BRD07' if tol==.1 else 'RC0603FR-07')+code+'L','r',{1:a,2:b},f'{v} ohm {tol}%','https://www.yageo.com/en/Chart/Download/pdf/RC0603',value=v);parts[-1]['tolerance_pct']=tol

def c(ref,a,b='GND',v='100n'):
 m,fp={'100n':('GRM188R71C104KA01D','c'),'1u':('GRM188R61C105KA93D','c'),'10u':('GRM21BC71E106ME11L','c8'),'22u':('GRM21BC81C226ME44L','c8'),'47n':('GRM188R71H473KA61D','c'),'4.7u':('GRM21BR71A475KA73L','c8')}[v]
 add(ref,m,fp,{1:a,2:b},v+' F ceramic','https://www.murata.com/en-us/products/capacitor/mlcc',value=v)
def q(ref,g,s,d,p=False):add(ref,'DMP2035U-7' if p else '2N7002,215','q',{1:g,2:s,3:d},'P-channel rail switch' if p else 'N-channel control', 'https://www.diodes.com/assets/Datasheets/DMP2035U.pdf' if p else 'https://assets.nexperia.com/documents/data-sheet/2N7002.pdf',{1:'G',2:'S',3:'D'})
def logic(ref,typ,a,y,b=None):
 add(ref,'SN74LVC1G'+typ+'DBVR','q5',{1:'NC' if b is None else a,2:a if b is None else b,3:'GND',4:y,5:'3V3_SYS'},'Power-state logic',TI+'sn74lvc1g'+typ+'.pdf');c('C_'+ref,'3V3_SYS')
# USB port and two parallel independently limited branches.
usb={**{k:'GND' for k in ['A1','A12','B1','B12','SH']},**{k:'USB_VBUS' for k in ['A4','A9','B4','B9']},'A5':'USB_CC1','B5':'USB_CC2','A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM','A8':'NC','B8':'NC'}
add('J_USB','TYPE-C-31-M-12','Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',usb,'USB-C USB2 sink; connector shell grounded','https://www.hrocn.com/ProductDetail.aspx?id=199');c('C_USB_RAW','USB_VBUS',v='1u')
add('U_USB_RECOVERY','TPS22950YBHR','GlovePower:TI_YBH0006_C02',{'A1':'USB_RECOVERY_ON','A2':'USB_RECOVERY_FAULT_N','B1':'USB_VBUS','B2':'USB_CHARGER_IN','C1':'GND','C2':'USB_RECOVERY_ILIM'},'Specified34–66mA recovery; exactYBH WCSP, notC SOTversion',TI+'tps22950.pdf')
r('R_USB_RECOVERY_ILIM','19.2k','USB_RECOVERY_ILIM','GND',.1);r('R_USB_RECOVERY_ON','100k','USB_VBUS','USB_RECOVERY_ON');q('Q_USB_SUSPEND','USB_SUSPEND','GND','USB_RECOVERY_ON')
add('U_USB_HIGH','TPS2553DBVR','q6',{1:'USB_VBUS',2:'GND',3:'USB_HIGH_ON',4:'USB_LIMIT_FAULT_N',5:'USB_HIGH_ILIM',6:'USB_CHARGER_IN'},'Configured/high-current branch; includes recovery current in total bound',TI+'tps2553.pdf',{1:'IN',2:'GND',3:'EN',4:'FAULT',5:'ILIM',6:'OUT'})
r('R_USB_HIGH_ILIM','71.5k','USB_HIGH_ILIM','GND',.1);r('R_USB_CC_ILIM','30.9k','USB_HIGH_ILIM','USB_CC_RLOW',.1);q('Q_USB_CC_ILIM','HIGH_CURRENT','GND','USB_CC_RLOW');r('R_USB_HIGH_ON','100k','USB_HIGH_ON','GND')
for n in ['USB_LIMIT_FAULT_N','USB_RECOVERY_FAULT_N']:r('R_'+n,'47k','3V3_SYS',n)
c('C_USB_LIMITED','USB_CHARGER_IN',v='1u')
add('U_CC','TUSB320LAIRWBR','Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm',{1:'USB_CC1',2:'USB_CC2',3:'GND',4:'USB_VBUS_DET',5:'NC',6:'NC',7:'CC_OUT1',8:'CC_OUT2',9:'NC',10:'GND',11:'GND',12:'3V3_SYS'},'Sink-only GPIOmode; internaldeadbatteryRd; noexternalRd',TI+'tusb320lai.pdf',{1:'CC1',2:'CC2',3:'PORT',4:'VBUS_DET',5:'ADDR',6:'OUT3',7:'OUT1',8:'OUT2',9:'ID',10:'GND',11:'EN_N',12:'VDD'})
c('C_CC','3V3_SYS');r('R_CC_VBUS','887k','USB_VBUS','USB_VBUS_DET',.1)
for n in ['CC_OUT1','CC_OUT2']:r('R_'+n,'10k','3V3_SYS',n)
logic('U_CC_HIGH','04','CC_OUT1','HIGH_CURRENT');logic('U_CC_ATTACH','00','CC_OUT1','USB_ATTACHED','CC_OUT2');logic('U_CFG_CLEAR','08','USB_ATTACHED','USB_CFG_ATTACH_N','USB_CONFIG_CLR_N');logic('U_CFG_RESET','08','USB_CFG_ATTACH_N','USB_CFG_CLEAR_N','ESP_EN')
add('U_USB_CFG','SN74LVC1G74DCUR','Package_SO:VSSOP-8_2.3x2mm_P0.5mm',{1:'USB_CONFIG_SET',2:'3V3_SYS',3:'NC',4:'GND',5:'USB_CONFIGURED',6:'USB_CFG_CLEAR_N',7:'3V3_SYS',8:'3V3_SYS'},'Enumeration latch, asynchronously clears ondetach/firmwareclear',TI+'sn74lvc1g74.pdf',{1:'CLK',2:'D',3:'Q_N',4:'GND',5:'Q',6:'CLR_N',7:'PRE_N',8:'VCC'});c('C_USB_CFG','3V3_SYS')
logic('U_USB_ALLOW','32','HIGH_CURRENT','USB_HIGH_ALLOW','USB_CONFIGURED');logic('U_USB_NOSUSP','04','USB_SUSPEND','USB_NOT_SUSPEND');logic('U_USB_ON','08','USB_HIGH_ALLOW','USB_HIGH_ON','USB_NOT_SUSPEND')
# Switching charger:1.205A;4.2V;8–12h safety timer. External current limit authoritative.
cp={1:'USB_CHARGER_IN',2:'NC',3:'NC',4:'NC',5:'CHG_STAT_N',6:'GND',7:'USB_PG_N',8:'CHG_ILIM',9:'CHG_CE_N',10:'CHG_ICHG',11:'BAT_TS',12:'NC',13:'VBAT',14:'VBAT',15:'VSYS',16:'VSYS',17:'GND',18:'GND',19:'CHG_SW',20:'CHG_SW',21:'CHG_BTST',22:'CHG_REGN',23:'CHG_PMID',24:'USB_CHARGER_IN',25:'GND'}
add('U_CHARGER','BQ25616RTWR','GlovePower:TI_RTW0024_BQ25616',cp,'VSETfloating4.2V;OTGground;D+/D-isolated;powerpath',TI+'bq25616.pdf',dict(enumerate(['VAC','ACDRV','D+','D-','STAT','OTG','PG','ILIM','CE_N','ICHG','TS','VSET','BAT','BAT','SYS','SYS','GND','GND','SW','SW','BTST','REGN','PMID','VBUS','EP'],1)))
r('R_CHG_ICHG','562','CHG_ICHG','GND',.1);r('R_CHG_ILIM','390','CHG_ILIM','GND',.1)
c('C_CHG_BTST','CHG_BTST','CHG_SW','47n');c('C_CHG_REGN','CHG_REGN',v='4.7u');c('C_CHG_PMID','CHG_PMID',v='10u');c('C_BAT','VBAT',v='22u')
for i in range(2):c('C_SYS'+str(i),'VSYS',v='22u')
for ref,a,b in [('L_CHARGER','CHG_SW','VSYS'),('L_MAIN','MAIN_L1','MAIN_L2')]:add(ref,'XFL4020-152MEC','GlovePower:Coilcraft_XFL4020',{1:a,2:b},'1.5uH shieldedpowerinductor','https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xfl/xfl4020/',value='1.5u')
for n in ['CHG_STAT_N','USB_PG_N']:r('R_'+n,'47k','3V3_SYS',n)
add('J_BAT','43045-0200','Connector_Molex:Molex_Micro-Fit_3.0_43045-0200_2x01_P3.00mm_Horizontal',{1:'VBAT_ENTRY',2:'GND'},'Protected pack; pin1 positive red, pin2 ground black; 43025-0200 housing and 43030-0007 AWG22 contacts','https://www.molex.com/pdm_docs/sd/430450201_sd.pdf')
add('J_NTC','B2B-PH-K-S(LF)(SN)','Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',{1:'BAT_TS',2:'GND'},'External Semitec103AT-2 pack thermistor','https://www.jst-mfg.com/product/pdf/eng/ePH.pdf')
add('F_BAT','045102.5MRL','Fuse:Fuse_Littelfuse-NANO2-451_453',{1:'VBAT_ENTRY',2:'VBAT'},'2.5A fast fuse before ALL board battery branches; Micro-Fit AWG22 fault coordination required','https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1',value='2.5A fast')
# Independent hardwaretemperatureguard,nominal15..40C;BQTS remainsactive.
r('R_TS_TOP','5.23k','CHG_REGN','BAT_TS',.1);r('R_TS_BOTTOM','30.9k','BAT_TS','GND',.1);c('C_TS','BAT_TS')
add('U_BAT_WINDOW','LM393LVDGKR','Package_SO:VSSOP-8_3x3mm_P0.65mm',{1:'NTC_VALID',2:'BAT_TS',3:'NTC_COLD_THRESHOLD',4:'GND',5:'BAT_TS',6:'NTC_HOT_THRESHOLD',7:'NTC_VALID',8:'CHG_REGN'},'WiredAND cold/hotchargeguard;open/shortNTCdisablescharge',TI+'lm393lv.pdf');c('C_BAT_WINDOW','CHG_REGN')
for tag,top in [('COLD','52.3k'),('HOT','107k')]:r('R_NTC_'+tag+'_TOP',top,'CHG_REGN','NTC_'+tag+'_THRESHOLD',.1);r('R_NTC_'+tag+'_BOT','100k','NTC_'+tag+'_THRESHOLD','GND',.1)
r('R_NTC_PULL','10k','CHG_REGN','NTC_VALID');r('R_NTC_COLD_HYST','10M','NTC_VALID','NTC_COLD_THRESHOLD');r('R_NTC_HOT_HYST','10M','NTC_VALID','BAT_TS');q('Q_CHG_ENABLE','NTC_VALID','GND','CHG_CE_N');r('R_CHG_CE','10k','CHG_REGN','CHG_CE_N');q('Q_CHG_DISABLE','CHG_DISABLE','GND','NTC_VALID')
# MAIN3.416V, adjustableUVLO;PWMcapture/PFMstandby.
add('U_MAIN','TPS63070RNMR','GlovePower:TI_RNM0015A',{1:'REG_PFM',2:'MAIN_PG',3:'MAIN_VAUX',4:'GND',5:'MAIN_FB',6:'GND',7:'3V3_SYS',8:'3V3_SYS',9:'MAIN_L2',10:'GND',11:'MAIN_L1',12:'VSYS',13:'VSYS',14:'MAIN_EN',15:'GND'},'3.416Vbuckboost',TI+'tps63070.pdf')
for ref,v,a,b in [('R_MAIN_TOP','327k','3V3_SYS','MAIN_FB'),('R_MAIN_BOT','100k','MAIN_FB','GND'),('R_MAIN_EN_TOP','300k','VSYS','MAIN_EN'),('R_MAIN_EN_BOT','100k','MAIN_EN','GND')]:r(ref,v,a,b,.1)
c('C_MAIN_AUX','MAIN_VAUX')
for i in range(2):c('C_MAIN_IN'+str(i),'VSYS',v='10u')
for i in range(3):c('C_MAIN_OUT'+str(i),'3V3_SYS',v='22u')
for tag,net in [('IN','VSYS'),('OUT','3V3_SYS')]:c('C_MAIN_LOCAL_'+tag,net,v='10u');parts[-1].update(mpn='TMK107BBJ106MA-T',footprint=F['c'])
r('R_MAIN_PG','47k','3V3_SYS','MAIN_PG')
add('U_BAT_READY','TLV3012BIDBVR','q6',{1:'BAT_READY',2:'GND',3:'BAT_READY_DIV',4:'BAT_READY_REF',5:'BAT_READY_REF',6:'3V3_SYS'},'HystereticbatteryreadypreventsweakUSBbootoscillation',TI+'tlv3012.pdf');c('C_BAT_READY','3V3_SYS')
r('R_READY_TOP','158k','VBAT','BAT_READY_DIV',.1);r('R_READY_BOTTOM','100k','BAT_READY_DIV','GND',.1);r('R_READY_HYST','2.15M','BAT_READY','BAT_READY_DIV',.1)
logic('U_BOOT_SOURCE','32','BAT_READY','BOOT_POWER','HIGH_CURRENT');logic('U_BOOT_PG','08','BOOT_POWER','BOOT_ENABLE','MAIN_PG');r('R_BOOT_DELAY','10k','BOOT_ENABLE','BOOT_DELAY');c('C_BOOT_DELAY','BOOT_DELAY',v='1u');logic('U_BOOT_SCHMITT','17','BOOT_DELAY','ESP_EN')
# Quietanalograilplusgatedreferencefeed;rapidVREFdischargeonshutdown.
add('U_ANALOG_LDO','TPS7A2033PDBVR','q5',{1:'3V3_SYS',2:'GND',3:'ANALOG_EN',4:'NC',5:'3V3_A'},'Quietanalograil,145mVmaxdropoutboundat300mA',TI+'tps7a20.pdf');c('C_ANALOG_IN','3V3_SYS',v='10u')
for i in range(3):c('C_ANALOG_OUT'+str(i),'3V3_A',v='22u')
r('R_ANALOG_EN','100k','ANALOG_EN','GND');q('Q_REF_FEED','REF_GATE','3V3_SYS','REF_MAIN_SW',True);r('R_REF_GATE','100k','3V3_SYS','REF_GATE');q('Q_REF_GATE','ANALOG_EN','GND','REF_GATE');r('R_REF_FILTER','10','REF_MAIN_SW','VREF_SUPPLY');c('C_REF_SUPPLY','VREF_SUPPLY',v='1u');logic('U_ANALOG_OFF','04','ANALOG_EN','ANALOG_OFF');
for suffix,net in [('OUT','VREF3V0'),('IN','VREF_SUPPLY')]:
 add('Q_VREF_BLEED_'+suffix,'PMV16XN,215','q',{1:'REF_BLEED_GATE_'+suffix,2:'GND',3:'REF_BLEED_'+suffix},'LowvoltagepowerNMOSactivelydischargesreferenceonanalogoff','https://assets.nexperia.com/documents/data-sheet/PMV16XN.pdf',{1:'G',2:'S',3:'D'})
 r('R_VREF_BLEED_'+suffix,'22',net,'REF_BLEED_'+suffix);parts[-1].update(mpn='RC0805FR-0722RL',footprint='Resistor_SMD:R_0805_2012Metric')
 r('R_VREF_GATE_'+suffix,'220','ANALOG_OFF','REF_BLEED_GATE_'+suffix)

# Switched2:1batterydivider;50mssettle.
q('Q_BAT_MEAS','BAT_MEAS_GATE','VBAT','BAT_MEAS_TOP',True);r('R_BAT_MEAS_GATE','100k','VBAT','BAT_MEAS_GATE');q('Q_BAT_MEAS_GATE','BAT_DIV_EN','GND','BAT_MEAS_GATE');r('R_BAT_ADC_TOP','100k','BAT_MEAS_TOP','BAT_SENSE',.1);r('R_BAT_ADC_BOTTOM','100k','BAT_SENSE','GND',.1);c('C_BAT_ADC','BAT_SENSE')
gpio={1:'BAT_SENSE',2:'BUTTON_N',4:'I2C_SDA',5:'I2C_SCL',6:'MCU_CAM_VSYNC',7:'MCU_CAM_HREF',8:'MCU_CAM_D2',9:'MCU_CAM_D1',10:'MCU_CAM_D3',11:'MCU_CAM_D0',12:'MCU_CAM_D4',13:'MCU_CAM_PCLK',14:'SD_SCK',15:'MCU_CAM_XCLK',16:'MCU_CAM_D7',17:'MCU_CAM_D6',18:'MCU_CAM_D5',19:'MCU_USB_DM',20:'MCU_USB_DP',21:'SD_MOSI',38:'MUX_LATCH',39:'ADC_SCK',40:'ADC_SDO',41:'ADC_CNV',42:'MUX_DATA',43:'MUX_SHIFT_CLK',44:'ANALOG_EN',47:'SD_MISO',48:'SD_CS_N',0:'BOOT0',3:'NC',45:'STRAP45',46:'STRAP46',35:'NC',36:'NC',37:'NC'}
pg={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,13:19,14:20,15:3,16:46,17:9,18:10,19:11,20:12,21:13,22:14,23:21,24:47,25:48,26:45,27:0,28:35,29:36,30:37,31:38,32:39,33:40,34:41,35:42,36:44,37:43,38:2,39:1}
mp={1:'GND',2:'3V3_SYS',3:'ESP_EN',40:'GND',41:'GND',**{p:gpio[g] for p,g in pg.items()}}
add('U_MCU','ESP32-S3-WROOM-1-N8R8','RF_Module:ESP32-S3-WROOM-1',mp,'8MBflash8MBPSRAM;35–37reserved','https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf',{**{p:'GPIO'+str(g) for p,g in pg.items()},1:'GND',2:'3V3',3:'EN',40:'GND',41:'EPAD'});c('C_MCU','3V3_SYS');c('C_MCU_BULK','3V3_SYS',v='22u')
for n,pull in [('BOOT0','3V3_SYS'),('STRAP45','GND'),('STRAP46','GND'),('MUX_LATCH','GND')]:r('R_'+n,'10k',n,pull)
for n in ['DP','DM']:r('R_USB_'+n,'22','USB_'+n,'MCU_USB_'+n)
for n in ['SDA','SCL']:r('R_I2C_'+n,'2.2k','3V3_SYS','I2C_'+n)
add('SW_USER','PTS636SK43SMTR-LFS','Glove:SW_PTS636_SK43_G',{1:'BUTTON_CONTACT',2:'GND'},'Singlebuttonwithlargecaseactuator','https://www.ckswitches.com/media/2565/pts636.pdf');r('R_BUTTON_SERIES','1k','BUTTON_CONTACT','BUTTON_N');r('R_BUTTON_PULL','47k','3V3_SYS','BUTTON_N');c('C_BUTTON','BUTTON_N')
outputs=['CAM_IO_EN','CAM_AV_EN','CAM_DV_EN','CAM_IF_EN','MCU_CAM_RESET_N','MCU_CAM_PWDN','LED_R_N','LED_G_N','LED_B_N','BAT_DIV_EN','REG_PFM','USB_CONFIG_SET','USB_CONFIG_CLR_N','USB_SUSPEND','CHG_DISABLE','SD_EN']
inputs=['CC_OUT1','CC_OUT2','CHG_STAT_N','USB_PG_N','USB_LIMIT_FAULT_N','BAT_READY','SD_CD_N','IO1_UNUSED_P07','CUFF_IMU_INT1','USB_RECOVERY_FAULT_N']+['IO1_SPARE'+str(i) for i in range(6)]
for idx,nets in enumerate([outputs,inputs]):
 ps={1:'NC',2:'GND',3:'GND',12:'GND',21:'3V3_SYS' if idx else 'GND',22:'I2C_SCL',23:'I2C_SDA',24:'3V3_SYS',**dict(zip(list(range(4,12))+list(range(13,21)),nets))}
 add('U_IO'+str(idx),'TCA9535PWR','Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm',ps,f'I2C0x{0x20+idx:02x}control/status',TI+'tca9535.pdf');c('C_IO'+str(idx),'3V3_SYS')
for n in outputs:
 if n.startswith(('CAM_','MCU_CAM_')) or n=='SD_EN':continue # camera-subtreeownsitsdefaultpulls
 r('R_DEFAULT_'+n,'47k' if n in ['LED_R_N','LED_G_N','LED_B_N'] else '100k',n,'3V3_SYS' if n in ['LED_R_N','LED_G_N','LED_B_N'] else 'GND')
for n in inputs:
 if 'SPARE' in n or n=='IO1_UNUSED_P07':r('R_'+n,'10k',n,'GND')
add('D_RGB','APTF1616LSEEZGKQBKC','GlovePower:Kingbright_APTF1616',{1:'3V3_SYS',2:'LED_R_K',3:'LED_G_K',4:'LED_B_K'},'CommonanodeRGBstatuslight','https://www.kingbrightusa.com/images/catalog/spec/aptf1616lseezgkqbkc.pdf')
for color,value in [('R','1k'),('G','680'),('B','680')]:r('R_LED_'+color,value,'LED_'+color+'_K','LED_'+color+'_N')
for ref,a,b in [('D_USB_DATA','USB_DP','USB_DM'),('D_USB_CC','USB_CC1','USB_CC2')]:
 add(ref,'PESD5V0U2BT,215','q',{1:a,2:b,3:'GND'},'DualultralowcapacitanceUSB/CCESDprotection','https://assets.nexperia.com/documents/data-sheet/PESD5V0U2BT.pdf')
for ref,k,a in [('D_REF_REVERSE','VREF_SUPPLY','VREF3V0'),('D_ANALOG_REVERSE','3V3_SYS','3V3_A')]:
 add(ref,'PMEG2010ER,115','GlovePower:Nexperia_CFP3_SOD123W',{1:k,2:a},'Schottkyreverse-dischargeprotection','https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf',{1:'K',2:'A'})
# BulkcapacitanceusesmanufacturerDCbiasdata;47uF1210retainsmarginunderbias/tolerance/temperature.
for part in parts:
 if part['ref']=='C_BAT' or part['ref'].startswith(('C_SYS','C_MAIN_OUT','C_ANALOG_OUT')):
  part.update(mpn='GRM32ER61C476KE15L',value='47u',footprint='Capacitor_SMD:C_1210_3225Metric',purpose='47uF16V10pctX5Rbulk;DCbiascharacteristicretainedinsources',source='https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM32ER61C476KE15-01A.pdf')
ports={'power_out':['3V3_SYS','3V3_A','VREF_SUPPLY'],'power_in':['VREF3V0'],'mcu_gpio':gpio,'adc_vio':'3V3_SYS','ioexpander':{f'0x{0x20+i:02x}':{f'P{j//8}{j%8}':n for j,n in enumerate(ns)} for i,ns in enumerate([outputs,inputs])}}
d={'schema':1,'revision':'V4 power exact circuit candidate','parts':parts,'ports':ports,'battery':{'mpn':'Jauch250480 LI18650JLS HB1S2P+PCM+FUSE+2WIRES70MM','min_capacity_Ah':6.5,'nominal_voltage':3.6,'charge_temperature_C':[10,45],'max_charge_A':2.0,'external_ntc':'Semitec103AT-2'},'physical_validation_status':'unbuilt; calculations and native pin reconciliation do not establish physical validation'}
(P/'power-circuit.json').write_text(json.dumps(d,indent=2)+'\n')
(P/'firmware-contract.json').write_text(json.dumps({'main_nominal_V':3.416,'expander_ports':ports['ioexpander'],'gpio':gpio,'battery_divider':{'ratio':2,'settle_ms':50,'warning_V':3.4,'stop_V':3.2,'resume_V':3.55},'cc_states':{'11':'unattached','10':'default','01':'1.5A','00':'3A'},'button':{'gpio':2,'active':0,'on_hold_ms':800,'pair_hold_ms':3000,'off_hold_ms':1500,'sleep_after_release':True}},indent=2)+'\n')
print(len(parts),'parts',len({n for p in parts for n in p['pins'].values() if n!='NC'}),'nets')
