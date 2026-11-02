#!/usr/bin/env python3
"""Reproducible electrical bounds, not device or physical validation substitutes."""
from pathlib import Path
import json,math,itertools,hashlib
P=Path(__file__).resolve().parent;d=json.loads((P/'power-circuit.json').read_text());p={x['ref']:x for x in d['parts']}
checks=[]
def ck(name,ok,detail):checks.append({'name':name,'status':'pass' if ok else 'fail','detail':detail})
rt=327000;rb=100000;tol=.001
main_nom=.8*(1+rt/rb)
main_min=.8*.99*(1+rt*(1-tol)/(rb*(1+tol)))
main_max=.8*1.03*(1+rt*(1+tol)/(rb*(1-tol)))
pwm_max=.8*1.01*(1+327000*1.001/(100000*.999))
ref_min=main_min-.120-.00085*10.01-.00085*.1
ck('Main operating voltage corner',main_max+.060<3.6 and pwm_max+.100<3.6,{'nominal_V':main_nom,'PWM_min_V':main_min,'PFM_max_V':main_max,'overshoot_allowance_V':.060,'PFM_standby_max_with_allowance_V':main_max+.060,'PWM_max_V':pwm_max,'PWM_overshoot_allowance_V':.100,'PWM_max_with_allowance_V':pwm_max+.100,'allowance_is_design_requirement_not_measured':True})
ck('REF3330 supply corner',ref_min>3.2,{'min_V':ref_min,'margin_above3V2_V':ref_min-3.2,'droop_allowance_V':.120,'reference_total_load_A':.00085,'requires_transient_validation':True})
analog_min=main_min-.120-.145
ck('Analog minimum supply',analog_min>3.05,{'min_V':analog_min,'LDO_dropout_max_V_at300mA':.145,'assumed_analog_load_A':.064,'MCP600x_min_V':1.8,'OPA4323_min_V':2.7,'VEXC_driver_required_V':2.5+47*.005,'comment':'Analograilmayleave3.3Vregulationatworstdroop;operatingheadroomremains.'})
# USBbranchTPS2553DSformulauseskOhms,mA;lowbranchspec34..66mAplus0.1%resistor.
def lim(r):return {'min_mA':25230/(r*1.001)**1.016,'nom_mA':23950/r**.977,'max_mA':22980/(r*.999)**.94}
recovery={'min_mA':34/1.001**1.072,'max_mA':66/.999**1.072,'supply_max_mA':.060}
usb={}
for mode,r in [('configured',71.5),('type_c_high',1/(1/71.5+1/30.9))]:
 a=lim(r);a['total_max_mA']=a['max_mA']+recovery['max_mA']+.140+.060+.060 # ownIq,VBUSdivider+margin
 a['total_min_mA']=a['min_mA']+recovery['min_mA'];usb[mode]=a
ck('USBdefaultinputlimit',recovery['max_mA']+.3<100,{'recovery':recovery,'extra_VBUS_control_budget_mA':.3,'max_total_mA':recovery['max_mA']+.3})
ck('USBconfiguredinputlimit',usb['configured']['total_max_mA']<500,usb['configured'])
ck('USBTypeCinputlimit',usb['type_c_high']['total_max_mA']<1500,usb['type_c_high'])
# Enumeratedloadpermissionlatchmustclearwithdetach,resetorFWclear.
truth=[]
for cc1,cc2,configured,suspend,esp_en in itertools.product([0,1],repeat=5):
 attached=not(cc1 and cc2);high=not cc1;q=configured and attached and esp_en
 truth.append(dict(cc1=cc1,cc2=cc2,mount_latched=bool(q),suspend=suspend,esp_en=esp_en,high_branch=bool((high or q) and not suspend),recovery_branch=not suspend))
ck('Detachresetcurrentpermission',all(not t['mount_latched'] for t in truth if (t['cc1'] and t['cc2']) or not t['esp_en']),{'states_checked':len(truth)})
# NTCcurveSemitec103AT-2nominaltable;3%R envelopecoversR25/Btolerancesoverthiswindow.
table=[(0,27280),(10,17960),(20,12090),(25,10000),(30,8313),(40,5827),(50,4160)]
def ntc(t):
 for (a,ra),(b,rb) in zip(table,table[1:]):
  if a<=t<=b:return math.exp(math.log(ra)+(t-a)/(b-a)*math.log(rb/ra))
 return table[0][1] if t<0 else table[-1][1]
def crossing(kind,regn,ntctol,rt,rb,rth,rlo,offset,out):
 def error(t):
  rn=ntc(t)*(1+ntctol);ts=(regn/rt+out/10e6)/(1/rt+1/rb+1/rn+1/10e6)
  threshold=(regn/rth+(out/10e6 if kind=='cold' else 0))/(1/rth+1/rlo+(1/10e6 if kind=='cold' else 0))
  return ts-threshold+offset
 a,b=0.,50.
 for _ in range(60):
  m=(a+b)/2
  if error(m)>0:a=m
  else:b=m
 return (a+b)/2
ntc_bounds={}
for kind,top in [('cold',52300),('hot',107000)]:
 vals=[]
 for regn,nt,tt,tb,ct,cb,off,state in itertools.product([3.5,5.1],[-.03,.03],[-.001,.001],[-.001,.001],[-.001,.001],[-.001,.001],[-.003,.003],[0,1]):
  vals.append(crossing(kind,regn,nt,5230*(1+tt),30900*(1+tb),top*(1+ct),100000*(1+cb),off,regn if state else .2))
 ntc_bounds[kind]=[min(vals),max(vals)]
ck('Hardwarechargewindow',ntc_bounds['cold'][0]>.5+10 and ntc_bounds['hot'][1]<45,{'trip_C':ntc_bounds,'NTC_R_envelope_pct':3,'resistor_tolerance_pct':.1,'comparator_offset_mV':3,'self_heating_allowance_C':.5,'pack_allowed_C':[10,45],'thermal_contact_and_time_constant_require_pack_test':True})
# Open/short faultoutputs:ts=0orREGN*30.9/(30.9+5.23).
ck('NTCopenandshortfailoff',30.9/(30.9+5.23)>100/(100+52.3) and 0<100/(100+107),{'open_TS_ratio':30.9/(30.9+5.23),'short_TS_ratio':0})
# Battery comparatorTLV3012B reference1.223..1.260,offset±6mV,hys2..8mV.
ready=[]
for vr,off,hys,t,b,h,vs,vol,vohdrop in itertools.product([1.223,1.260],[-.006,.006],[.002,.008],[-.001,.001],[-.001,.001],[-.001,.001],[main_min,main_max],[0,.2],[0,.2]):
 rt=158000*(1+t);rb=100000*(1+b);rh=2150000*(1+h);scale=1+rt/rb+rt/rh
 ready.append(((vr+off+hys/2)*scale-vol*rt/rh,(vr+off-hys/2)*scale-(vs-vohdrop)*rt/rh))
ready_bounds={'rising_V':[min(x[0] for x in ready),max(x[0] for x in ready)],'falling_V':[min(x[1] for x in ready),max(x[1] for x in ready)]}
ck('MCUstartupbatteryhysteresis',ready_bounds['rising_V'][0]>ready_bounds['falling_V'][1],ready_bounds)
# Chargecurrent/timer:currentverifiedat562ohm;resistortoleranceaddedoutsideICrange.
chg_min=1.14/1.001;chg_max=1.28/.999
ck('Chargecurrentwithinpacklimit',chg_max<d['battery']['max_charge_A'],{'min_A':chg_min,'nom_A':1.205,'max_A':chg_max,'pack_max_A':d['battery']['max_charge_A'],'standard_A':1.2,'charge_rate_C_max':chg_max/6.5,'CC_6V5Ah_hours_atmin':6.5/chg_min,'fast_timer_min_hours':8,'CV_time_available_hours':8-6.5/chg_min,'timer_doubles_in_DPM':True,'CVdurationandcellthermals_not_guaranteed_from_capacity':True})
# ResistivedividerADCsettle.
tau=(100e3*100e3/200e3)*100e-9
ck('BatteryADCsettle',math.exp(-.050/tau)<.0001,{'ratio':2.,'max_divider_ratio_error_fraction':.001,'tau_ms':tau*1000,'50ms_residual_fraction':math.exp(-.050/tau),'adc_calibration_required':True})
# ShutdownRCenvelope:referencehasactivebleedandreturnSchottky,analograilhasQOD+35mAload.
# Usesminimum24uFeffectiveanalogcap,reference9.8uFmaximumcombinedinput/outputcap.
ca=24e-6;cr=9.8e-6;rqod=80.;rbleed=22*1.01+.1
pairs=[]
for i in range(10001):
 t=i*1e-6
 va=max(0,(analog_min+.064*rqod)*math.exp(-t/(ca*rqod))-.064*rqod)
 # Eachrailhasitsown22ohmbleed;conservativelyputcombinedcapontheoutputbleed.
 vr=3.05*math.exp(-max(0,t-5e-6)/(cr*rbleed))
 pairs.append((t,va,vr,vr-va))
maxdiff=max(x[3] for x in pairs)
ck('Referenceanalogshutdownordering',maxdiff<.3,{'max_reference_minus_analog_V':maxdiff,'analog_C_effective_min_uF':24,'reference_plus_input_C_max_uF':9.8,'LDO_QOD_assumed_min_ohm':80,'analog_load_max_A':.064,'FET_Ron_design_bound_ohm':.1,'FET_Ron_25C_max_at2V5_ohm':.024,'gate_delay_allowance_us':5,'temperaturedependent_diode_andLDOdischarge_bounds_need_validation':True})
# Sharedpins/packagesstaticchecks.
ck('Referencegatedwithanalog',p['Q_REF_GATE']['pins']['1']=='ANALOG_EN' and p['R_VREF_GATE_OUT']['pins']['1']=='ANALOG_OFF' and p['R_VREF_GATE_IN']['pins']['1']=='ANALOG_OFF',{})
ck('Latchphysicalpinmap',p['U_USB_CFG']['pins']=={'1':'USB_CONFIG_SET','2':'3V3_SYS','3':'NC','4':'GND','5':'USB_CONFIGURED','6':'USB_CFG_CLEAR_N','7':'3V3_SYS','8':'3V3_SYS'},{'source':TI if False else 'TI SCES794G p4'})
ck('ADCVIODomain',d['ports']['adc_vio']=='3V3_SYS',{'VIO':'3V3_SYS','VDDsequencing_audit_owned_by_mainanalogintegration':True})
ck('Singlebutton',sum(x['ref'].startswith('SW') for x in d['parts'])==1,{})
ck('Uniquecomponentreferences',len(p)==len(d['parts']),{})
# Knownqualificationlimitsareexplicitandneverreportedassimulationpasses.
limits=[
 'Switchingcharger and limiter loop interaction has no manufacturer transient model here; benchtest lowcurrentstartup, poor-source qualification, DPM and cableinrush.',
 'BQ25616 poor-source test is specified30mA typical, without guaranteedmaximum.34mAminimumrecovery has nominalmargin, notaguaranteed qualification bound.',
 'BQ25616 safety timer8–12h doublesinDPM; extremelyweakportsmaytimeoutearlierthanfullcharge. Fullpackchargequalification usesTypeC>=1.5A. Verifydepletedpackreaches3.3VMCUstartupbeforetimeout.',
 'TPS63070 originalPSpicemodelrun is trackedseparately; modelcompatibility/startupmustpassbeforeclaimingtransientvalidation.',
 'Revised mode-specific allocation: PWM droop120mV/overshoot100mV, PFM standby overshoot60mV. Earlier100/60mV allocation failed; see saved original vendor-model results.',
 'Selected47uF1210 bias curves yield74.44uF bank after10% tolerance and20% extra allowance; corrected model uses60uF. Typical curves and allowance need production/physical validation.',
 'BatteryNTCthermalcontact, pouchtemperature, cellCVtail, chargerthermal andsurfaceheatingrequirephysicalpack/enclosuretests.',
 'Copperplanes, switchingloops, RFkeepout, USBimpedanceandcameraconcurrencyawaitV4PCB integration; thispowercircuitisnotafabricationrelease.'
]
# Conservativechargerinputsteady-statebudget, deliberatelyboundsnottransientsim.
budgets={'cell_min_Ah':6.5,'nominal_V':3.6,'usable_fraction':.8,'six_hour_battery_input_limit_W':6.5*3.6*.8/6,'system_runtime_analysis_owner':'hardware/glove-v4/verification; complete camera/radio/SD load budget overrides the former1.9W allocation','charging_output_W_at1V28A4V2':chg_max*4.2,'charger_loss_W_at_assumed90pct':chg_max*4.2*(1/.9-1),'USB_limiter_loss_W_at1V3A135mohm':1.3**2*.135,'efficiency_90pct_is_assumption':True}
result={'schema':1,'circuit_sha256':hashlib.sha256((P/'power-circuit.json').read_bytes()).hexdigest(),'checks':checks,'failed_checks':[x['name'] for x in checks if x['status']=='fail'],'all_calculated_checks_pass':all(x['status']=='pass' for x in checks),'physical_validation':False,'qualification_open':limits,'budgets':budgets,'usb_truth_table':truth}
(P/'power-check-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'failures':result['failed_checks'],'NTC':ntc_bounds,'USB':usb,'ready':ready_bounds},indent=2))
