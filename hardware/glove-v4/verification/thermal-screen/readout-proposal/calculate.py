#!/usr/bin/env python3
"""Unapplied two-NTC readout proposal: declared corner calculations, not hardware proof."""
from pathlib import Path
import hashlib,itertools,json,math,sys
HERE=Path(__file__).resolve().parent
V4=HERE.parents[2]
ROOT=V4.parents[1]
TABLE=[(-50,329500),(-40,188500),(-30,111300),(-20,67770),(-10,42470),(0,27280),(10,17960),(20,12090),(25,10000),(30,8313),(40,5827),(50,4160),(60,3020),(70,2228),(80,1668),(85,1451),(90,1266),(100,973.1),(110,757.6)]
def resistance(t):
    for (a,ra),(b,rb) in zip(TABLE,TABLE[1:]):
        if a<=t<=b:return math.exp(math.log(ra)+(t-a)/(b-a)*math.log(rb/ra))
    raise ValueError('Temperature outside retained Semitec R-T table')
def temperature(r):
    for (a,ra),(b,rb) in zip(TABLE,TABLE[1:]):
        if rb<=r<=ra:return a+(b-a)*math.log(r/ra)/math.log(rb/ra)
    raise ValueError('Resistance outside retained Semitec R-T table')
def estimate(q_true,ratio,errors,vexc=2.5,r_used=.5):
    # All readings use the same signal path. Linear offset/gain cancel in differences.
    ds=(q_true-ratio)*vexc/3.03*32768+errors[0]
    dm=errors[1]
    de=(1-ratio)*vexc/3.03*32768+errors[2]
    q=r_used+(1-r_used)*(ds-dm)/(de-dm)
    return q

def corners(t,leak=8e-6,buffered=True,mux_r=500):
    # +/-1% R25 and B; selected0.1%25ppm/C pulls/divider, or rejected1%100ppm/C option
    # over an allowed 0..85C board range, +/-7mV VMID buffer qualification
    # allocation, +/-8 counts/read including INL + rounding + noise allocation.
    # Leakage is a REQUIRED total node-current acceptance; TI specifies only
    # off-switch leakage under a different test condition, not this sum.
    rtol=(.001+25e-6*60) if buffered else (.01+100e-6*60)
    ratios=[(1-rtol)/2-.007/2.45,(1+rtol)/2+.007/2.45]
    rows=[]
    for nr,nb,rp,vex,i,rm,e0,e1,e2,sh,wire in itertools.product([-1,1],[-1,1],[-1,1],[2.45,2.55],[-1,1],ratios,[-1,1],[-1,1],[-1,1],[0,.15],[0,1]):
        sensor_t=t+sh
        ntc=resistance(sensor_t)*(1+nr*.01)*math.exp(nb*.01*3435*(1/(sensor_t+273.15)-1/298.15))+wire
        pull=10000*(1+rp*rtol)
        q=ntc/(pull+ntc)
        # Ground displacement is independent of common ADC offset. Its extrema
        # align with sensor-buffer error because both change q monotonically.
        q+=i*.005*pull/(pull+ntc)/vex
        q+=i*((2e-9*(pull*ntc/(pull+ntc))+.007+leak*(101+mux_r)) if buffered else leak*(pull*ntc/(pull+ntc)))/vex
        ref_drop_codes=leak*mux_r/3.03*32768 if buffered else 0
        independent_error=8+.001/3.03*32768
        qest=estimate(q,rm,(e0*independent_error,e1*(independent_error+ref_drop_codes),e2*(independent_error+ref_drop_codes)),vexc=vex)
        if not 0<qest<1:raise ValueError('Corner outside divider range')
        test=temperature(10000*qest/(1-qest))
        rows.append(test)
    # .25C is explicit interpolation acceptance, not specified by Semitec.
    return {'true_C':t,'indicated_C':[min(rows)-.25,max(rows)+.25], 'error_C':[min(rows)-.25-t,max(rows)+.25-t], 'corner_count':len(rows)}

def main():
    normal=[corners(t) for t in [0,25,30,35,36,37,40,45,50,60,85]]
    unbuffered=[corners(t,buffered=False) for t in [35,40,45,60]]
    stress=[corners(t,mux_r=2000) for t in [35,40,45,60]]
    # Explicit signal fault extremes with same ratio/code allocation.
    ratios=[.49875-.007/2.45,.50125+.007/2.45]
    faults={}
    for kind,qs in [('open',[1-(.007+8e-6*2101)/2.45,1]),('short',[0,(.005+.025+.007+8e-6*2101)/2.45])]:
        sample_error=8+.001/3.03*32768
        reference_error=sample_error+8e-6*2000/3.03*32768
        vals=[estimate(q,r,e,vexc=2.45) for q,r,e in itertools.product(qs,ratios,itertools.product([-sample_error,sample_error],[-reference_error,reference_error],[-reference_error,reference_error]))]
        faults[kind]={'estimated_q_range':[min(vals),max(vals)]}
    faults['open']['detected_all_allocated_corners']=faults['open']['estimated_q_range'][0]>.94
    faults['short']['detected_all_allocated_corners']=faults['short']['estimated_q_range'][1]<.06
    assert all(faults[k]['detected_all_allocated_corners'] for k in faults)
    assert all(abs(resistance(t)/r-1)<1e-12 and abs(temperature(r)-t)<1e-9 for t,r in TABLE)
    assert all(abs(temperature(resistance(t))-t)<1e-9 for t in range(-50,111))
    assert abs(temperature(math.sqrt(8313*5827))-35)<1e-10
    assert all(abs(estimate(q,r,[0,0,0],vexc=v,r_used=r)-q)<1e-12 for q,r,v in itertools.product([.1,.368,.5,.9],[.49,.5,.51],[2.45,2.55]))
    load_ntc=2*2.55/(10000*.99)
    load_total=20*2.55/(10000*.99)+load_ntc+2.55/(20000*.99)+8e-6
    out={'status':'engineering proposal; canonical circuit/BOM/firmware unchanged','model':'Semitec nominal R-T table with independent endpoint tolerances and declared engineering allocations','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'nominal_RT_ohm':TABLE,'calibration':'Default uses r=0.5 with the full divider/buffer bound. Factory measurement of actual VMID/VEXC may narrow initial error but requires temperature qualification. GND is not used as an endpoint.','temperature_error_corners':normal,'mux_2kohm_stress':stress,'rejected_unbuffered_1percent_design':unbuffered,'assumptions':{'R25_fraction':.01,'B25_85_fraction':.01,'pullup_and_midpoint_divider_initial_fraction':.001,'resistor_tempco_per_C':25e-6,'board_temperature_range_C':[0,85],'max_temperature_distance_from25_C':60,'VMID_buffer_offset_acceptance_V':.007,'buffer_input_bias_acceptance_A':2e-9,'buffer_offset_acceptance_V':.007,'mux_R_acceptance_ohm':500,'mux_R_not_guaranteed_at3p3V_by_TI':True,'total_mux_node_leakage_acceptance_A':8e-6,'leakage_is_manufacturer_guaranteed_total':False,'ADC_per_sample_error_acceptance_counts':8,'RT_interpolation_acceptance_C':.25,'VEXC_range_V':[2.45,2.55],'ADC_reference_upper_acceptance_V':3.03,'sensor_return_ground_displacement_acceptance_V':.005,'independent_signal_level_path_error_acceptance_V_per_read':.001,'self_heating_acceptance_C':[0,.15],'series_sensor_wire_and_contacts_acceptance_ohm':[0,1]},'faults':faults,'electrical':{'extra_two_sensors_at25_mA':.25,'extra_two_short_sensors_worst_mA':1000*load_ntc,'total_VEXC_worst_mA':1000*load_total,'simulation_load_mA':5.81,'RISO_47ohm_plus1percent_drop_V':.00581*47*1.01,'minimum_analog_supply_V':3.111665494505495,'raw_output_required_worst_V':2.55+.00581*47*1.01,'remaining_output_headroom_V':3.111665494505495-2.55-.00581*47*1.01,'node_cap_max_F':100e-9*1.1*1.15,'open_node_time_constant_s':10160*100e-9*1.1*1.15,'startup_settle_s':.020,'max_sensor_self_heating_W':2.55**2/(4*9900),'typical_still_air_self_heating_C':2.55**2/(4*9900)/.002},'validation':{'all_table_endpoints_and_integer_roundtrips':True,'independent_midpoint_interpolation':abs(temperature(math.sqrt(8313*5827))-35)<1e-10,'ratiometric_formula_with_actual_ratio':all(abs(estimate(q,r,[0,0,0],vexc=v,r_used=r)-q)<1e-12 for q,r,v in itertools.product([.1,.368,.5,.9],[.49,.5,.51],[2.45,2.55]))},'threshold_status':'36C base +3C accepted total indication error +1C total gradient/lag reaches40C with zero reserve; unqualified proposal, not protective guarantee','release':False,'unresolved_guarantees':['TI off-switch leakage is not a guaranteed selected-channel summed leakage specification; buffer isolates the divider, but selected Ron x leakage still needs qualification at3.3V.','MCP6002 typical model does not establish production output swing at 5.81mA, 3.112V, 85C; input bias and offset allocations also require temperature acceptance.','Thermistor R25/B limits do not themselves specify an all-temperature R-T tolerance corridor; confirm two-point/temperature acceptance.','Sensor-to-hottest-cell and sensor-to-contact gradients, sensor lag, post-shutdown stored-heat overshoot and USB standby heating require instrumented assembly tests.','Self-heating, return-ground displacement, input-level dependent analog errors, wire/contact resistance and ADC3.03V ceiling are explicit acceptance allocations, not guaranteed measured bounds.','Cohort-to-cohort and within-cohort VEXC/VMID dynamics, long-term drift and thermistor ageing remain unmodelled.']}
    (HERE/'results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'temperature_error_corners':normal,'faults':faults,'electrical':out['electrical']},indent=2))
if __name__=='__main__':main()
