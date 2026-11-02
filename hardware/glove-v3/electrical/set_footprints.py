from pathlib import Path
import json
P=Path(__file__).parent;d=json.loads((P/'components.json').read_text())
special={
'SN74AHC595PWR':'TSSOP-16_4.4x5mm_P0.65mm',
'SM07B-SRSS-TB(LF)(SN)':'JST_SH_SM07B-SRSS-TB_1x07-1MP_P1.00mm_Horizontal',
'102010469':'XIAO-nRF52840-SMD-kicad7',
'MCP6004T-I/ST':'TSSOP-14_4.4x5mm_P0.65mm','OPA4320AIPWR':'TSSOP-14_4.4x5mm_P0.65mm',
'MCP6002T-I/SN':'SOIC-8_3.9x4.9mm_P1.27mm','MCP1501T-25E/SN':'SOIC-8_3.9x4.9mm_P1.27mm',
'CD74HC4067M':'SOIC-24W_7.5x15.4mm_P1.27mm','CD74HC4052M':'SOIC-16_3.9x9.9mm_P1.27mm',
'TCA9534DWR':'SOIC-16W_7.5x10.3mm_P1.27mm','PCF8574T':'SOIC-16W_7.5x10.3mm_P1.27mm',
'MCP33131D-10-I/MS':'MSOP-10_3x3mm_P0.5mm',
'OPA320AIDBVR':'SOT-23-5','TLV75518PDBVR':'SOT-23-5','TPS22919DCKT':'SOT-363_SC-70-6',
'BM06B-GHS-TBT(LF)(SN)':'JST_GH_BM06B-GHS-TBT_1x06-1MP_P1.25mm_Vertical',
'BM08B-GHS-TBT(LF)(SN)':'JST_GH_BM08B-GHS-TBT_1x08-1MP_P1.25mm_Vertical',
'BM14B-GHS-TBT(LF)(SN)':'JST_GH_BM14B-GHS-TBT_1x14-1MP_P1.25mm_Vertical',
'SM04B-SRSS-TB(LF)(SN)':'JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal',
'B2B-PH-K-S(LF)(SN)':'JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
'PTS636SK43SMTR-LFS':'SW_PTS636_SK43_G',
}
for p in d['components']:
 n=special.get(p['mpn'])
 if n is None:
  prefix=p['ref'][0];assert prefix in 'RC',p
  n=prefix+'_'+('0805_2012Metric' if p['package']=='0805' else '0603_1608Metric')
 assert (P/'footprints'/(n+'.kicad_mod')).exists(),n
 p['footprint']='Glove:'+n
(P/'components.json').write_text(json.dumps(d,indent=2)+'\n')
(P/'fp-lib-table').write_text('(fp_lib_table (lib (name "Glove") (type "KiCad") (uri "${KIPRJMOD}/footprints") (options "") (descr "Local verified-source package geometry")))\n')
print('Assigned exact footprint IDs:',len(d['components']))
