#!/usr/bin/env python3
"""Exact microSD SPI power, signal and card-detection circuit."""
from pathlib import Path
import json
P = Path(__file__).resolve().parent
parts = []
def add(ref, mpn, footprint, pins, purpose, source, **extra):
    parts.append(dict(ref=ref,qty=1,mpn=mpn,footprint=footprint,
        pins={str(k):v for k,v in pins.items()},purpose=purpose,source=source,**extra))
def resistor(ref,value,a,b):
    mpn={'47k':'RC0603FR-0747KL','100k':'RC0603FR-07100KL','33':'RC0603FR-0733RL'}[value]
    add(ref,mpn,'Resistor_SMD:R_0603_1608Metric',{1:a,2:b},value+' ohm',
        'https://www.yageo.com/en/Chart/Download/pdf/RC0603',value=value)
add('U_SD_POWER','TPS22919DCKR','Package_TO_SOT_SMD:SOT-363_SC-70-6',
    {1:'3V3_SYS',2:'GND',3:'SD_EN',4:'NC',5:'SD_VDD',6:'SD_VDD'},
    'Controlled-rise supply, QOD directly connected to output, default off',
    'https://www.ti.com/lit/ds/symlink/tps22919.pdf',
    pin_functions={'1':'IN','2':'GND','3':'ON','4':'NC','5':'QOD','6':'OUT'})
resistor('R_SD_EN','100k','SD_EN','GND')
for ref,net,mpn,value,fp in [
    ('C_SD_IN','3V3_SYS','GRM21BR61A106KE19L','10uF','C_0805_2012Metric'),
    ('C_SD_BULK','SD_VDD','GRM32ER61A476KE20L','47uF','C_1210_3225Metric'),
    ('C_SD_HF','SD_VDD','GRM188R71C104KA01D','100nF','C_0603_1608Metric')]:
    add(ref,mpn,'Capacitor_SMD:'+fp,{1:net,2:'GND'},value+' local card decoupling',
        'https://www.murata.com/en-us/products/capacitor/mlcc',value=value)
for n in ['SCK','MOSI','CS_N']:resistor('R_SD_'+n,'33','SD_'+n,'CARD_'+n)
for n in ['CS_N','MOSI','MISO','DAT1','DAT2']:
    resistor('R_SD_PULL_'+n,'47k','SD_VDD','CARD_'+n if n in ['CS_N','MOSI'] else 'SD_'+n)
resistor('R_SD_CD','47k','3V3_SYS','SD_CD_N')
contacts={'1':'SD_DAT2','2':'CARD_CS_N','3':'CARD_MOSI','4':'SD_VDD',
          '5':'CARD_SCK','6':'GND','7':'SD_MISO','8':'SD_DAT1','9':'SD_CD_N','10':'GND','11':'GND'}
add('J_SD','DM3AT-SF-PEJM5','Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5',contacts,
    'Push-push microSD, independent detect A/B, shell grounded; CAD numbering reconciled to drawing',
    'https://www.hirose.com/en/product/p/CL0609-0031-0-00')
data=dict(schema=1,revision='V4 microSD SPI interface',parts=parts,
    acquisition=dict(bus='ESP32-S3 SPI3',clock_hz=20000000,
                     gpio=dict(sck=14,mosi=21,miso=47,cs=48),
                     card_detect='IO1 P06, active low',power_enable='IO0 P17'),
    power_sequence=dict(on=['Qualify source','SD_EN high','Wait 5ms','Initialize SPI/card and mount'],
        off=['Stop writes and flush','Unmount and release SPI','SCK/MOSI/CS low; MISO input without pullup','SD_EN low']),
    electrical_limits=dict(card_voltage_min_V=2.7,card_voltage_max_V=3.6,
        design_peak_current_A=.3,switch_Ron_conservative_ohm=.4,
        switched_rail_max_drop_V=.12,nominal_bulk_uF=47,startup_inrush_A_typical=.127),
    validation_scope='Pin and supply design; selected card current remains a design assumption until electrically characterized.')
(P/'sd-interface.json').write_text(json.dumps(data,indent=2)+'\n')
print(f'{len(parts)} SD circuit parts')
