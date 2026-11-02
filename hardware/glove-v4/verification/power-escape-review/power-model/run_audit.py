"""Reproduce plane DC, width, via and battery copper-budget estimates.
Run with the KiCad Python environment. Results are engineering calculations, not thermal qualification.
"""
from pathlib import Path
import sys,subprocess,json,math,hashlib,os
P=Path(__file__).resolve().parent;board=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
import pcbnew as k
b=k.LoadBoard(str(board));assert b.GetCopperLayerCount()==8
vias=[t for t in b.GetTracks() if t.Type()==k.PCB_VIA_T]
required={'VBAT_ENTRY':[(x,y,.3) for x in [9.145,9.945] for y in [74.5,75.5]],'VBAT':[(x,y,.3) for x in [14.055,14.855] for y in [74.5,75.5]]+[(17.3736,64.6083,.3),(17.8,65.025,.3)],'VSYS':[(15.85,65.025,.3),(16.15,64.525,.3),(29.375,63.6,.2),(29.975,63.6,.2)],'GND':[(29,65,.2),(29.65,65,.2),(30.3,65,.2)]}
for net,points in required.items():
 for x,y,d in points:
  assert any(t.GetNetname()==net and math.hypot(k.ToMM(t.GetPosition().x)-x,k.ToMM(t.GetPosition().y)-y)<.001 and abs(k.ToMM(t.GetDrillValue())-d)<.001 for t in vias),('Missing audited power via',net,x,y,d)
j=next(f for f in b.GetFootprints() if f.GetReference()=='J12');assert math.hypot(k.ToMM(j.GetPosition().x)-4.1,k.ToMM(j.GetPosition().y)-66.25)<.001
planes={}
for name in ['entry','battery','battery-return','vsys','main','usb']:
 vals=[]
 for step in [.1,.075]:
  dest=out/(name+'-'+str(step)+'.json')
  subprocess.run([sys.executable,str(P/'plane_dc_audit.py'),str(board),str(dest),str(step),str(P/(name+'-sheet-config.json'))],stdout=subprocess.DEVNULL,check=True)
  vals.append(json.loads(dest.read_text()))
 ratio=abs(vals[0]['resistance_at30um_ohm']/vals[1]['resistance_at30um_ohm']-1)
 if ratio>.05:
  dest=out/(name+'-0.05.json');subprocess.run([sys.executable,str(P/'plane_dc_audit.py'),str(board),str(dest),'.05',str(P/(name+'-sheet-config.json'))],stdout=subprocess.DEVNULL,check=True);vals.append(json.loads(dest.read_text()));ratio=abs(vals[-2]['resistance_at30um_ohm']/vals[-1]['resistance_at30um_ohm']-1)
 planes[name]={'resistance_30um_ohm':max(x['resistance_at30um_ohm'] for x in vals),'last_grid_relative_change':ratio,'converged_5percent':ratio<=.05,'widest_interior_corridor_mm':min(x['widest_interior_corridor_mm'] for x in vals),'terminal_spreading_exclusion_radius_mm':1.5}
 print(name,planes[name],flush=True)
rho=1.724e-8*(1+.00393*(50-20));z_power_a=.7205;z_power_b=.8805;z_ground=.1245;thickness_scale=1.76/1.636;plating_um=15
# All diameters are finished holes. Treat only the traversed barrel segment as a resistor.
def barrel(d_mm,z_mm,parallel):return rho*(z_mm*thickness_scale/1000)/(math.pi*((d_mm+plating_um/1000)/1000)*(plating_um/1e6))/parallel
via_segments=[('J12 positive',1.02,z_power_b,1),('F1 entry array',.3,z_power_b,4),('F1 output array',.3,z_power_b,4),('BQ battery array',.3,z_power_b,2),('BQ system array',.3,z_power_a,2),('TPS63070 input array',.2,z_power_a,2),('J12 return',1.02,z_ground,1),('TPS63070 power ground',.2,z_ground,3)]
via_terms=[{'name':n,'drill_mm':d,'barrel_length_mm':z*thickness_scale,'parallel':c,'resistance_ohm':barrel(d,z,c)} for n,d,z,c in via_segments]
# Deliberately use full center-to-center lengths and minimum conductor width for the short surface escapes.
# Each two-pin supply has two parallel escapes; using the longer branch for both bounds their parallel resistance.
neck_terms=[('BQ battery escape',.75,.25,2),('BQ system escape',math.hypot(.1,.5),.28,2),('TPS63070 pad spreading',.4,.25,2),('two fuse-pad spreading paths',.8,1.8,1)]
neck_results=[{'name':n,'length_upper_mm':l,'width_lower_mm':w,'parallel':c,'resistance_at28um_ohm':rho/(28e-6)*(l/w)/c} for n,l,w,c in neck_terms]
plane_sum=sum(planes[n]['resistance_30um_ohm'] for n in ['entry','battery','vsys','battery-return']);plane_bound=plane_sum*30/24*1.05
R=plane_bound+sum(x['resistance_ohm'] for x in via_terms)+sum(x['resistance_at28um_ohm'] for x in neck_results)
def min_width(current,copper_um,internal):return (current/((.024 if internal else .048)*10**.44))**(1/.725)/(copper_um/25.4)*.0254
currents={'battery':1.525,'USB_input':1.35,'main_output':1.0}
widths={n:{'current_A':i,'minimum_long_inner_width_24um_10C_mm':min_width(i,24,True),'minimum_long_outer_width_28um_10C_mm':min_width(i,28,False)} for n,i in currents.items()}
report={'board_sha256':hashlib.sha256(board.read_bytes()).hexdigest(),'stackup':'JLC081611-3313','nominal_finished_mm':1.6,'template_compressed_mm':1.636,'maximum_finished_mm_assumption':1.76,'outer_copper_nominal_um':35,'inner_copper_nominal_um':30,'engineering_minimum_copper_assumptions_um':{'outer':28,'inner':24,'via_plating':15},'temperature_C':50,'plane_models':planes,'barrels':via_terms,'surface_escape_bounds':neck_results,'battery_plus_return_plane_bound_ohm':plane_bound,'battery_plus_return_total_calculated_ohm':R,'battery_plus_return_allocation_ohm':.015,'battery_plus_return_allocation_calculation_pass':R<=.015 and all(planes[n]['converged_5percent'] for n in ['entry','battery','vsys','battery-return']),'at_1p525A':{'drop_V':1.525*R,'copper_loss_W':1.525**2*R},'long_corridor_width_requirements':widths,'sources':['https://www.ti.com/lit/an/snva766/snva766.pdf','https://jlcpcb.com/help/article/jlcpcb-copper-weight','https://jlcpcb.com/help/article/multi-layer-pcb-standard-laminated-structures','https://jlcpcb.com/capabilities/pcb-capabilities'],'limitations':['Factory must confirm copper and minimum barrel plating assumptions; JLC advertised average plating is not a guaranteed minimum.','The plane model is DC only and ignores parallel copper. A grid convergence check does not establish temperature rise or switching stability.','Short package escapes require first-article thermal validation; the long-trace formula is not applied blindly to package pads.','Power integrity also requires input/output ripple and load-step measurements, actual battery harness resistance, and temperature-rise qualification.','Manufacturing readiness additionally requires zero opens, final DRC, RF clearance, controlled USB routing review and specified filled/capped via treatment.']}
(out/'power-corridor-calculations.json').write_text(json.dumps(report,indent=2)+'\n');print('BATTERY COPPER',R,'ohm; allocation pass',report['battery_plus_return_allocation_calculation_pass'],flush=True)
