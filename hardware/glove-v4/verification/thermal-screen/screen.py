#!/usr/bin/env python3
"""Five-node steady thermal screening; algebraic network, not CFD/FEA.
Standard-library only. Reads current authored power/CAD evidence; writes results.
"""
from pathlib import Path
import hashlib,itertools,json,math
HERE=Path(__file__).resolve().parent
V4=HERE.parents[1]
SIGMA=5.670374419e-8
ENERGY=json.loads((V4/'verification/energy-budget.json').read_text())
CHECKS=json.loads((V4/'power/power-check-results.json').read_text())
MECH=json.loads((V4/'enclosure/clearance-report.json').read_text())
by_check={q['name']:q['detail'] for q in CHECKS['checks']}
by_case={q['name']:q for q in ENERGY['cases']}
NAMES=['electronics_mean','pack_mean','exposed_shell_mean','wrist_facing_base_mean','internal_air_mean']
W,L,H=.112,.104,.0455
CORNER=.010
A_BASE=W*L-(4-math.pi)*CORNER**2
PERIMETER=2*(W+L)-8*CORNER+2*math.pi*CORNER
A_EXPOSED=A_BASE+PERIMETER*H
A_PCB=.100*.080
A_PACK=.072*.039
A_PACK_SIDE=2*(.072+.039)*.021
A_FOAM=sum(q['solid_volume_cm3'] for q in MECH['mass_budget']['parts'] if q['file'].startswith('battery-foam-pad-'))*1e-6/.0017
HOT=by_check['Hardwarechargewindow']['trip_C']['hot']
I_USB=[by_check['USBTypeCinputlimit']['total_min_mA']/1000,by_check['USBTypeCinputlimit']['total_max_mA']/1000]
I_CHG=[by_check['Chargecurrentwithinpacklimit']['min_A'],by_check['Chargecurrentwithinpacklimit']['max_A']]
R_PATH=ENERGY['boundary']['battery_path_resistance_allocation_ohm']
ETA_MAIN=ENERGY['boundary']['converter_efficiency']
# These ranges are declared engineering sensitivities, not measured guarantees.
R_PACK_INTERNAL=[.03,.15]
ENTROPIC_HEAT_W=[0,.10]
ETA_CHARGER=[.85,.94]
USB_SERIES_R=.135
CONTROL_W=.020

def upper_current(power,v,r):
    disc=v*v-4*r*power
    if disc<=0:raise ValueError('Electrical power unavailable')
    return 2*power/(v+math.sqrt(disc))

def charge_power(system_output_w,vbat,eta,usb_limit,ichg_set,r_internal,entropy):
    main_input=system_output_w/ETA_MAIN
    available=eta*(5*usb_limit-usb_limit**2*USB_SERIES_R-CONTROL_W)
    if available<main_input:raise ValueError('This high-current USB case requires battery supplement')
    allowed=2*(available-main_input)/(vbat+math.sqrt(vbat*vbat+4*R_PATH*(available-main_input)))
    ichg=min(ichg_set,allowed)
    path=ichg*ichg*R_PATH
    nvdc=main_input+vbat*ichg+path
    charger_loss=nvdc*(1/eta-1)
    iusb=upper_current(nvdc/eta+CONTROL_W,5,USB_SERIES_R)
    limiter=iusb*iusb*USB_SERIES_R
    pcb_heat=main_input+path+charger_loss+limiter+CONTROL_W
    pack_heat=ichg*ichg*r_internal+entropy
    stored=vbat*ichg-pack_heat
    assert abs(5*iusb-pcb_heat-pack_heat-stored)<1e-9
    assert iusb<=usb_limit+1e-9
    return {'electronics_heat_w':pcb_heat,'pack_heat_w':pack_heat,'USB_input_w':5*iusb,'charge_current_A':ichg,'charger_loss_w':charger_loss,'USB_limiter_loss_w':limiter,'stored_chemical_power_w':stored,'charge_setting_A':ichg_set,'USB_limit_A':usb_limit,'charger_efficiency':eta,'pack_voltage_V':vbat,'system_output_w':system_output_w}

def power_inputs():
    modes={}
    for label,ref in [('recording_duty','realistic_duty_budget'),('recording_sustained','conservative_sustained_design')]:
        d=by_case[ref]['result'];i=d['battery_current_at_low_voltage_ma']/1000
        modes[label]=[{'electronics_heat_w':d['battery_input_power_w_at_3v55'],'pack_heat_w':i*i*r+e,'battery_output_w':d['battery_input_power_w_at_3v55'],'battery_current_A':i,'pack_internal_R_ohm':r,'additional_entropic_heat_w':e} for r,e in itertools.product(R_PACK_INTERNAL,ENTROPIC_HEAT_W)]
    for label,loads in [('charging_acquisition_off',[.10,.40]),('charging_and_recording_duty',[by_case['realistic_duty_budget']['result']['system_power_w_at_3v55']]),('charging_and_recording_sustained',[by_case['conservative_sustained_design']['result']['system_power_w_at_3v55']])]:
        modes[label]=[charge_power(load,v,eff,limit,setting,r,e) for load,v,eff,limit,setting,r,e in itertools.product(loads,[3.2,3.6,4.2],ETA_CHARGER,I_USB,I_CHG,R_PACK_INTERNAL,ENTROPIC_HEAT_W)]
    for label,loads in [('USB_charge_inhibited_acquisition_off',[.10,.40]),('USB_charge_inhibited_recording_duty',[by_case['realistic_duty_budget']['result']['system_power_w_at_3v55']]),('USB_charge_inhibited_recording_sustained',[by_case['conservative_sustained_design']['result']['system_power_w_at_3v55']])]:
        modes[label]=[charge_power(load,3.6,eff,limit,0,0,0) for load,eff,limit in itertools.product(loads,ETA_CHARGER,I_USB)]
    return modes

def residual_for(temps,heat,ambient,boundary,params):
    # Solid nodes E, B, S, D plus an internal-air mixing node A. Gap
    # conduction and enclosure radiation remain explicit parallel paths.
    hc,eps,kpa,kfoam,internal_eps,hmix=params
    residual=[-heat[0],-heat[1],0.,0.,0.]
    def link(i,j,flow):
        residual[i]+=flow;residual[j]-=flow
    def gas_and_radiation(i,j,area,gap,wall=True):
        ti,tj=temps[i]+273.15,temps[j]+273.15
        conductance=area*(.026/gap+internal_eps*SIGMA*(ti+tj)*(ti*ti+tj*tj))
        if wall:conductance=1/(1/conductance+.0013/(kpa*area))
        link(i,j,conductance*(temps[i]-temps[j]))
    gas_and_radiation(0,2,A_PCB,.0136)
    gas_and_radiation(0,1,A_PACK,.005,wall=False)
    gas_and_radiation(0,3,A_PCB-A_PACK,.0277)
    gas_and_radiation(1,2,A_PACK_SIDE,.020)
    foam_g=1/(.0017/(kfoam*A_FOAM)+.0013/(kpa*A_FOAM))
    link(1,3,foam_g*(temps[1]-temps[3]))
    link(2,3,kpa*.0013*PERIMETER/H*(temps[2]-temps[3]))
    # hmix is an ADDITIONAL internal circulation sensitivity. hmix=0.1
    # approaches stagnant gaps;3 supplies a deliberately favorable mixing
    # path. It is not a measured cavity correlation or a fan boundary.
    for i,area in [(0,2*A_PCB),(1,A_PACK+A_PACK_SIDE),(2,A_EXPOSED),(3,A_BASE-A_FOAM)]:
        g=hmix*area
        if i in (2,3):g=1/(1/g+.0013/(kpa*area))
        link(i,4,g*(temps[i]-temps[4]))
    areas=[0,0,A_EXPOSED,A_BASE if boundary=='bench_all_faces_exposed' else 0,0]
    exterior=0
    for i,area in enumerate(areas):
        if area:
            q=area*(hc*(temps[i]-ambient)+eps*SIGMA*((temps[i]+273.15)**4-(ambient+273.15)**4))
            residual[i]+=q;exterior+=q
    phantom=(temps[3]-34)/15 if boundary=='34C_phantom_R15' else 0
    residual[3]+=phantom
    return residual,exterior,phantom

def solve_linear(a,b):
    n=len(b);a=[row[:]+[val] for row,val in zip(a,b)]
    for i in range(n):
        j=max(range(i,n),key=lambda j:abs(a[j][i]));a[i],a[j]=a[j],a[i]
        v=a[i][i]
        if abs(v)<1e-14:raise ValueError('Singular thermal network')
        a[i]=[x/v for x in a[i]]
        for j in range(n):
            if j!=i:
                f=a[j][i];a[j]=[x-f*y for x,y in zip(a[j],a[i])]
    return [row[-1] for row in a]

def thermal(heat,ambient,boundary,params):
    temps=[ambient+10]*5
    for iteration in range(40):
        residual,out,phantom=residual_for(temps,heat,ambient,boundary,params)
        if max(map(abs,residual))<1e-10:break
        # Central difference Jacobian; step is a temperature increment in K.
        columns=[];step=.0001
        for i in range(5):
            upper=temps[:];lower=temps[:];upper[i]+=step;lower[i]-=step
            rp=residual_for(upper,heat,ambient,boundary,params)[0]
            rm=residual_for(lower,heat,ambient,boundary,params)[0]
            columns.append([(p-m)/(2*step) for p,m in zip(rp,rm)])
        delta=solve_linear([list(x) for x in zip(*columns)],[-x for x in residual])
        temps=[t+d for t,d in zip(temps,delta)]
    else:raise ValueError('Thermal solve did not converge')
    error=out+phantom-sum(heat)
    assert abs(error)<1e-8
    assert min(temps)>=min(ambient,34 if boundary=='34C_phantom_R15' else ambient)-1e-7
    return temps,error,phantom

def write_report(result):
    ranges=result['power_ranges'];cases=result['thermal_cases']
    def span(v):return f'{v[0]:.1f}–{v[1]:.1f}'
    def power_span(v):return f'{v[0]:.2f}–{v[1]:.2f}'
    labels={'recording_duty':'Recording, duty budget','recording_sustained':'Recording, sustained budget','charging_acquisition_off':'Charging, acquisition off','charging_and_recording_duty':'Charging + duty recording','charging_and_recording_sustained':'Charging + sustained recording','USB_charge_inhibited_acquisition_off':'USB, charge inhibited, acquisition off','USB_charge_inhibited_recording_duty':'USB, charge inhibited, duty recording','USB_charge_inhibited_recording_sustained':'USB, charge inhibited, sustained recording'}
    lines=['# Closed-cuff thermal screening','',
        '**The present design has a thermal qualification gap.** External surface area can reject the recording load at room temperature, but the internal battery/PCB gaps and the wrist contact path are unmeasured. The sensitivity cases cross pack and contact targets. Sustained recording at 35–40 °C ambient needs a verified thermal path and operating envelope before wearable release.','',
        'This is an executable five-node, steady-state thermal-resistance calculation, not FEA, CFD, a six-hour transient simulation, or proof of actual temperatures. It screens the frozen 112 × 104 × 45.5 mm case and 112 × 105.6 × 47.1 mm assembly. CAD, components and routing are unchanged.','',
        '## Heat generation','',
        '| Mode | Electronics heat, W | Internal pack heat, W | Charge current, A |',
        '|---|---:|---:|---:|']
    for mode,r in ranges.items():
        lines.append(f"| {labels[mode]} | {power_span(r['electronics_heat_w'])} | {power_span(r['pack_heat_w'])} | {power_span(r['charge_current_A']) if 'charge_current_A' in r else 'discharging'} |")
    lines += ['',
        'Recording starts with the authored [energy budget](../energy-budget.json): 2.440 W duty or 3.110 W sustained at pack output, including main-converter and 190 mΩ external-path losses. All output is assigned as assembly heat, without credit for escaped RF or the external hand tile. Extra cell/PCM heating uses an **unmeasured** 0.03–0.15 Ω internal-resistance sensitivity plus 0–0.10 W entropic allowance. The 20% energy reserve is capacity headroom, not a heat source.','',
        'The BQ25616 is a switching NVDC charger. The model subtracts energy stored in the battery from USB input, applies the actual 1.146–1.348 A USB limit and 1.139–1.281 A charge setting, and solves charge-current reduction under simultaneous load. It sweeps buck-stage efficiency 85–94%, while accounting for battery-path losses separately. Acquisition-off output of 0.10–0.40 W is a measurement assumption. USB is fixed at nominal 5 V; source/cable voltage extremes remain a test condition. The [TI datasheet](https://www.ti.com/lit/ds/symlink/bq25616.pdf) provides topology and a typical efficiency example, not a guarantee for this assembly.','',
        '## Temperature sensitivity','',
        'The table uses a **defined 34 °C wrist phantom with 15 K/W effective contact resistance**, including textile/contact/body-side resistance. It is a reproducible comparison boundary, not a validated human model. Ranges combine electrical and heat-transfer corners; independent heat extrema remove electrical correlations conservatively. Node temperatures are averages, with local hot spots unresolved.','',
        '| Mode | Ambient, °C | Exposed shell, °C | Pack, °C | Wrist-facing base, °C |',
        '|---|---:|---:|---:|---:|']
    for c in cases:
        if c['boundary']=='34C_phantom_R15' and c['mode'] in ('recording_duty','recording_sustained','charging_acquisition_off','charging_and_recording_sustained'):
            t=c['temperature_range_C'];lines.append(f"| {labels[c['mode']]} | {c['ambient_C']} | {span(t['exposed_shell_mean'])} | {span(t['pack_mean'])} | {span(t['wrist_facing_base_mean'])} |")
    lines += ['',
        '**Charging rows show requested-power equilibrium before temperature control.** In the hardware, the NTC/CE circuit inhibits charging at 39.01–41.23 °C. The high equilibrium numbers indicate likely interruption or cycling, not uninterrupted real charging at those temperatures. USB power to SYS continues after inhibition; the explicit charge-inhibited cases in [results.json](results.json) retain that heat. At 40 °C ambient the charge-enable window itself leaves almost no thermal headroom. NTC bonding, cell-to-NTC gradient and response lag still determine protection performance.','',
        'The [selected Jauch pack](https://www.jauch.com/downloadfile/61f0fb7230945444b292c0fac704609f8/6700%20mAh,%20LI18650JLS%20HB%201s2p,%20Mat.%20250480.pdf) specifies 10–45 °C for charging and −20–60 °C for discharge. This screen proposes a 40 °C sustained-contact goal and 43 °C fixture stop. These are engineering acceptance proposals, not a glove certification: [NASA contact guidance](https://www.nasa.gov/reference/9-0-hardware-and-equipment-vol-2/) treats 43 °C skin temperature as a relevant pain/performance threshold and requires contact-duration/material analysis. Base temperature is a contact-surface proxy.','',
        'The JSON also includes all-face bench cooling and an insulated-base stress boundary with zero wearer cooling. At 25 °C, that insulated-base sustained case reaches 48.6–82.3 °C at the base. It deliberately exposes reliance on body/contact heat removal; the upper values are extrapolated steady stress solutions, not expected normal-use temperatures. Neither boundary is a guaranteed bound on a worn product.','',
        '## Passive heat paths','',
        f'Top/sides expose {A_EXPOSED:.5f} m²; the base has {A_BASE:.5f} m². The projecting window/carrier receive no extra-area credit. The model separates PCB, pack, exposed shell, base and internal air. It uses PCB Z29–30.6 mm, lid underside 44.2 mm, pack top 24 mm, 1.3 mm floor and 1.7 mm foam over {A_FOAM:.5f} m². The pack clearance box approximates the two-cylinder pack surface.','',
        '| Path or parameter | Screening assumption |',
        '|---|---|',
        '| PCB → lid | 13.6 mm stagnant-air gap and radiation, then 1.3 mm nylon |',
        '| PCB → pack | 5 mm stagnant-air gap and radiation |',
        '| PCB → base outside pack | 27.7 mm gap and radiation, then nylon |',
        '| Pack → sides | 20 mm representative gap and radiation, then nylon |',
        '| Pack → base | Actual foam area/thickness in series with nylon floor |',
        '| Shell → base | Nylon sidewall conduction; no isothermal metal-case assumption |',
        '| Additional internal mixing | Separate air node; 0.1–3 W/(m² K) beyond stagnant-gap paths |',
        '| Outside natural convection | 3–8 W/(m² K), still-air/orientation sensitivity |',
        '| Radiation | Nonlinear Stefan–Boltzmann; outer emissivity 0.75–0.95, internal effective emissivity/view factor 0.45–0.85 |',
        '| PA12 / foam conductivity | 0.127–0.30 / 0.03–0.10 W/(m K), unqualified material ranges |','',
        'The heat-transfer ranges are sensitivities, not statistical intervals or manufacturer maxima. [NASA’s thermal guide, p.43](https://ntrs.nasa.gov/api/citations/20220006584/downloads/NASAPassiveThermalGuidebookv5%201Public.pdf) places Earth natural convection near 5 W/(m² K); [NIST](https://www.nist.gov/el/fire-research-division-73300/firegov-fire-service/fire-dynamics) gives representative air conductivity 0.026 W/(m K). [EOS PA2200, p.1](https://www.protiq.com/out/marketplace/merchants/0dab15bdac1ae142211675f47bd25f37/datasheets/13_pa2200_product_information_07-2020_en.pdf) provides a PA12 analogy, not the selected HP MJF property. [Rogers HT-800, p.2](https://www.sealanddesign.com/wp-content/uploads/2019/03/BISCO-HT-800.pdf) provides a 0.09 W/(m K) foam example; production foam is still unspecified.','',
        'The current design specifies no intentional board-to-exterior thermal contact. The model omits detailed copper/thermal vias, nylon ribs, fastener/wire conduction, adhesive contacts and spatial spreading. These can redistribute heat in either direction. The exposed shell node is also an average; nylon does not guarantee uniform surface temperature. BQ25616’s 110 °C typical junction regulation and 31.9 K/W JEDEC junction-to-ambient value cannot prove installed junction temperature.','',
        '## Heat-rejection requirement','',
        'An independent outside-only check holds every exposed top/side surface at 40 °C, with the base insulated. This is optimistic because it omits internal temperature drops:','',
        '| Ambient, °C | Heat rejected at 40 °C, W |',
        '|---|---:|']
    for ta,v in result['optimistic_exposed_shell_heat_rejection_at40C_W'].items():lines.append(f'| {ta} | {power_span(v)} |')
    qmin=sum(ranges['recording_sustained'][k][0] for k in ['electronics_heat_w','pack_heat_w'])
    qmax=sum(ranges['recording_sustained'][k][1] for k in ['electronics_heat_w','pack_heat_w'])
    rej=result['optimistic_exposed_shell_heat_rejection_at40C_W']['35']
    lines += ['',
        f'At 35 °C, sustaining the current workload while keeping all those surfaces at 40 °C needs another **{qmin-rej[1]:.2f}–{qmax-rej[0]:.2f} W** of heat removal through a verified boundary, or that amount of heat-load reduction. At 40 °C ambient, passive air cooling has zero capacity at a 40 °C surface. Improving an internal heat spreader alone cannot remove this external heat-rejection constraint.','',
        '**Engineering disposition:** preserve the current prototype for instrumented bench/phantom characterization. Thermal release requires measured operating limits. If cell temperatures or contact targets fail at the intended ambient/workload, revise the heat path toward the outward shell while limiting the wrist path, and/or reduce workload or charging current. Any spreader must preserve the RF keepout and electrical insulation; no geometry for such a change has been selected or installed. Simultaneous charging and recording remains a qualification case, not an approved wearable use claim.','',
        '## Physical acceptance test','',
        '1. Instrument both cells, NTC bond, PCM region, charger/adjacent PCB, TPS63070/inductor, ESP module, SD card, inner/outer floor, actual textile contact, lid and ambient. Use bonded thin thermocouples and calibrated IR; record 1 Hz temperatures, battery/USB/rail V/I, CE/status, frame rate and dropped frames.',
        '2. Test the fully closed final stack at 25/35/40 °C in still air ≤0.1 m/s and intended orientations. Compare all-face bench with actual strap/textile on a characterized warm wrist phantom. Specify contact resistance, pressure and phantom temperature; include a hotter-skin sensitivity. Human wear follows fixture acceptance.',
        '3. Run actual maximum supported continuous camera/tactile/dual-IMU/SD/radio workload for six hours, including low battery. Test acquisition-off charge from low SOC through CC/CV termination, then simultaneous recording/charging at low/mid/high SOC on a ≥1.5 A Type-C source, including voltage/cable extremes. Record input limiting and thermal cycles.',
        '4. Continue plateaus until all monitored temperatures change <0.2 °C per 10 minutes for 30 minutes, or a stop limit. Record full warmup/cooldown to determine thermal capacitance and NTC delay. Verify cell ≤45 °C during charging, ≤60 °C during discharge and measured charge cutoff/gradient/lag margin.',
        '5. Stop at 43 °C contact, 45 °C charging cell, 60 °C discharging cell, or the applicable component limit. Validate recording after CE inhibition. Repeat with final foam, seal, adhesives and strap tension after thermal cycling; publish the measured ambient/workload envelope or revise the design.','',
        '## Reproduction','',
        'Run `python3 hardware/glove-v4/verification/thermal-screen/screen.py`. [sources.json](sources.json) separates primary facts from assumptions. [results.json](results.json) exports source/script hashes, electrical ranges, every boundary case and maximizing corners. The standard-library solver checks energy conservation, zero-load equilibrium and monotonic heating. It models no warmup/cutoff timing, human perfusion, direct sun or local semiconductor junctions.','',
        f"Validation: {result['electrical_power_scenario_count']} electrical scenarios; {result['thermal_solution_count']} thermal corner solutions; maximum steady energy residual {result['validation']['max_steady_energy_residual_W']:.2g} W.", '']
    (HERE/'README.md').write_text('\n'.join(lines))

def main():
    assert MECH['case_dimensions_mm']=={'width':112,'length':104,'height':45.5}
    powers=power_inputs()
    ranges={}
    for mode,rows in powers.items():
        keys=sorted(set.intersection(*[set(r) for r in rows]))
        ranges[mode]={key:[min(r[key] for r in rows),max(r[key] for r in rows)] for key in keys}
    profiles=list(itertools.product([3,8],[.75,.95],[.127,.30],[.03,.10],[.45,.85],[.1,3]))
    cases=[];max_residual=0
    for mode,power in ranges.items():
        heats=list(itertools.product(power['electronics_heat_w'],power['pack_heat_w']))
        for ambient,boundary in itertools.product([25,35,40],['bench_all_faces_exposed','worn_no_body_sink','34C_phantom_R15']):
            rows=[]
            for heat,profile in itertools.product(heats,profiles):
                ts,err,body=thermal(heat,ambient,boundary,profile);max_residual=max(max_residual,abs(err))
                rows.append({'temperatures_C':dict(zip(NAMES,ts)),'heat_w':list(heat),'parameters':dict(zip(['outside_h_W_m2K','emissivity','PA12_k_W_mK','foam_k_W_mK','internal_effective_emissivity_viewfactor','additional_internal_mixing_h_W_m2K'],profile)),'phantom_heat_flow_W':body})
            extrema={n:[min(r['temperatures_C'][n] for r in rows),max(r['temperatures_C'][n] for r in rows)] for n in NAMES}
            pack=extrema['pack_mean'];base=extrema['wrist_facing_base_mean']
            cases.append({'mode':mode,'ambient_C':ambient,'boundary':boundary,'sampled_parameter_corners':len(rows),'temperature_range_C':extrema,'pack_charge_cutoff_possible':pack[1]>=HOT[0],'pack_charge_cutoff_all_corners':pack[0]>=HOT[1],'pack_discharge_60C_exceeded_some_corners':pack[1]>60,'base_40C_comfort_target_exceeded_some_corners':base[1]>40,'base_43C_stop_target_exceeded_some_corners':base[1]>43,'pack_maximizing_corner':max(rows,key=lambda r:r['temperatures_C']['pack_mean']),'base_maximizing_corner':max(rows,key=lambda r:r['temperatures_C']['wrist_facing_base_mean'])})
    # Independently solvable checks: equilibrium at zero heat; monotone heating;
    # electrical energy balance in every power scenario; all heat exits model.
    zero,err,_=thermal((0,0),25,'worn_no_body_sink',(5,.85,.20,.06,.65,1.5))
    assert max(abs(t-25) for t in zero)<1e-7
    zero_phantom,_,_=thermal((0,0),34,'34C_phantom_R15',(5,.85,.20,.06,.65,1.5))
    assert max(abs(t-34) for t in zero_phantom)<1e-7
    a,_,_=thermal((1,.05),25,'worn_no_body_sink',(5,.85,.20,.06,.65,1.5))
    b,_,_=thermal((2,.05),25,'worn_no_body_sink',(5,.85,.20,.06,.65,1.5))
    assert all(y>x for x,y in zip(a,b))
    # Analytical outside-only optimistic limit at a40C surface, without internal
    # thermal drops and with the underside insulated by wrist/textile.
    heat_capacity_at_40={str(ta):[A_EXPOSED*(h*(40-ta)+e*SIGMA*((40+273.15)**4-(ta+273.15)**4)) for h,e in [(3,.75),(8,.95)]] for ta in [25,35,40]}
    inputs=['verification/energy-budget.json','power/power-check-results.json','power/battery-path-check-results.json','power/firmware-contract.json','enclosure/clearance-report.json','enclosure/print-manifest.json']
    result={'schema':2,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources_sha256':hashlib.sha256((HERE/'sources.json').read_bytes()).hexdigest(),'analysis':'five-node nonlinear steady-state thermal resistance screening','FEA':False,'physical_validation':False,'date':'2026-10-23','input_sha256':{f:hashlib.sha256((V4/f).read_bytes()).hexdigest() for f in inputs},'geometry':{'case_mm':[112,104,45.5],'assembly_mm':[112,105.6,47.1],'shell_exposed_top_sides_m2':A_EXPOSED,'base_m2':A_BASE,'battery_foam_effective_area_m2':A_FOAM,'window_carrier_surface_credit':False},'nodes':NAMES,'power_ranges':ranges,'electrical_power_scenario_count':sum(map(len,powers.values())),'thermal_solution_count':sum(c['sampled_parameter_corners'] for c in cases),'charge_hardware_hot_window_C':HOT,'charge_enabled_cases_are_unregulated_requested_power':True,'thermal_release':False,'recommended_disposition':'instrumented bench/phantom characterization; thermal path and operating envelope unresolved','optimistic_exposed_shell_heat_rejection_at40C_W':heat_capacity_at_40,'thermal_cases':cases,'network_parameter_ranges':{'external_convection_W_m2K':[3,8],'surface_emissivity':[.75,.95],'PA12_conductivity_W_mK':[.127,.30],'foam_conductivity_W_mK':[.03,.10],'internal_effective_emissivity_viewfactor':[.45,.85],'additional_internal_mixing_h_W_m2K':[.1,3],'air_conductivity_W_mK':.026,'pack_internal_resistance_ohm':R_PACK_INTERNAL,'additional_pack_heat_W':ENTROPIC_HEAT_W,'charger_efficiency':ETA_CHARGER,'USB_limiter_R_ohm':USB_SERIES_R,'charge_only_system_output_W':[.10,.40],'34C_phantom_effective_contact_resistance_K_W':15},'validation':{'zero_power_equilibrium':True,'phantom_zero_power_equilibrium':True,'minimum_temperature_principle_all_cases':True,'monotonic_power_response':True,'electrical_energy_balance_all_cases':True,'max_steady_energy_residual_W':max_residual},'limitations':['The parameter-corner range is a sensitivity envelope, not a probability interval or guaranteed temperature bound. Independent extrema for electronics and pack heat conservatively remove electrical correlations.','Nodes are average temperatures; localized cell, IC, sleeve and contact hotspots are unresolved.','No thermal-via/trace/airflow mesh, measured material properties or human perfusion model is present. Nylon ribs, fasteners and wire conduction are omitted; no intentional low-resistance heat path is specified. Omitted conduction may cool electronics and warm the base; the ranges do not bound localized temperatures.','The 34C/R15 phantom is a defined comparison fixture, not a validated model of human skin.','Charging steady-state values describe requested charging before cutoff; physical CE inhibition changes heat generation and may cycle.','Pack internal resistance, entropic heat, standby draw, charger efficiency, optical/RF heat escape and static-air boundary are unmeasured.','Insulated clothing, direct sun, motion, sweat and hand contact change boundary conditions; these are not inferred from the sampled natural-convection range.','No transient warmup/cutoff time is claimed; measured thermal capacitance/NTC lag is needed.']}
    (HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    write_report(result)
    print(json.dumps({'thermal_solutions':result['thermal_solution_count'],'electrical_scenarios':result['electrical_power_scenario_count'],'max_energy_residual_W':max_residual,'worn_sustained':[c for c in cases if c['mode']=='recording_sustained' and c['boundary']=='worn_no_body_sink']},indent=2))
if __name__=='__main__':main()
