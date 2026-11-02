#!/usr/bin/env python3
from pathlib import Path
import json, math
OUT=Path(__file__).resolve().parent
BATTERY_V=3.6; BATTERY_MAH=6500; CAPACITY_RESERVE=0.80; CONVERTER_EFF=0.80
PATH_RESISTANCE_OHM=0.190; LOSS_EVALUATION_PACK_V=3.2
SYSTEM_V=3.416; DESIGN_WORST_V=3.55; IMU_V=3.416; TARGET_H=6.0
SOURCES={
 'battery':'https://www.jauch.com/downloadfile/61f0fb7230945444b292c0fac704609f8/6700%20mAh,%20LI18650JLS%20HB%201s2p,%20Mat.%20250480.pdf',
 'camera_module':'https://wiki.camthink.ai/docs/hardware-dev-resources/camera-module-ov5640/',
 'camera_sensor':'https://files.waveshare.com/upload/d/da/OV5640_DataSheet.pdf',
 'esp32':'https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf',
 'imu':'https://www.st.com/resource/en/datasheet/ism330dhcx.pdf',
 'sd':'https://www.kingston.com/datasheets/sdcit2_en.pdf',
 'translator_axc':'https://www.ti.com/lit/ds/symlink/sn74axc8t245.pdf'}
# Camera is an external-DVDD design: AVDD40 + DVDD125 + DOVDD12 = 177mA.
# LDO input current is conservatively priced as the sum of output currents.
def case(name, esp_ma, sd_ma, imus_ma, margin_ma, notes, sd_peak=None):
    camera_ma=40+125+12
    eq=esp_ma+camera_ma+sd_ma+imus_ma+64.405+margin_ma
    load_nom=eq*SYSTEM_V/1000
    load_worst=eq*DESIGN_WORST_V/1000
    converter_input_w=load_worst/CONVERTER_EFF
    # Evaluate resistive loss at the lowest pack voltage throughout the run.
    # This is deliberately conservative, with190mohm as a measured-acceptance
    # allocation including lead, connector, fuse, chargerBATFET andPCB copper.
    disc=LOSS_EVALUATION_PACK_V**2-4*PATH_RESISTANCE_OHM*converter_input_w
    if disc<=0: raise ValueError('Battery path voltage collapse')
    path_i=2*converter_input_w/(LOSS_EVALUATION_PACK_V+math.sqrt(disc))
    path_loss_w=path_i**2*PATH_RESISTANCE_OHM
    battery_w=converter_input_w+path_loss_w
    runtime=(BATTERY_V*BATTERY_MAH/1000*CAPACITY_RESERVE)/battery_w
    return {'name':name,'inputs':{'esp32_combined_ma_at_3v3':esp_ma,'camera_external_rail_input_ma':camera_ma,'sd_average_ma_at_3v3':sd_ma,'sd_peak_ma_at_3v3':sd_peak,'dual_imu_ma_at_3v416':imus_ma,'analog_ma_at_3v416':64.405,'board_translator_margin_ma':margin_ma},'result':{'equivalent_system_current_ma':round(eq,6),'system_power_w_at_3v416':round(load_nom,6),'system_power_w_at_3v55':round(load_worst,6),'converter_input_power_w':round(converter_input_w,6),'battery_path_loss_w_at_low_voltage':round(path_loss_w,6),'battery_current_at_low_voltage_ma':round(path_i*1000,6),'battery_input_power_w_at_3v55':round(battery_w,6),'battery_current_at_nominal_voltage_ma':round(battery_w/BATTERY_V*1000,6),'runtime_h_after_reserves':round(runtime,6),'six_hour_margin_h':round(runtime-TARGET_H,6)},'notes':notes}
nominal=BATTERY_V*BATTERY_MAH/1000; usable=nominal*CAPACITY_RESERVE
cases=[
 case('conservative_sustained_design',286,100,3.0,30,'ESP32 published TX operating point held continuously; SD100mA is a design assumption, not a manufacturer maximum. Scenario calculation, not guaranteed runtime.',300),
 case('realistic_duty_budget',150.625,100,3.0,30,'Wi-Fi: 15% TX at 286mA + 85% RX at 95mA = 123.65mA; CPU: 25% at 107.9mA dual-core 240MHz modem-sleep ceiling = 26.975mA. Combined ESP allowance is 150.625mA and must be measured.',300),
 case('peak_converter_sizing',286,300,3.0,30,'Instantaneous sizing only: ESP TX operating point and assumed SD300mA peak; this case is not a sustained runtime prediction.',300),
]
six_hour_pack_w=usable/TARGET_H
six_hour_pack_i=six_hour_pack_w/LOSS_EVALUATION_PACK_V
limit=(six_hour_pack_w-six_hour_pack_i**2*PATH_RESISTANCE_OHM)*CONVERTER_EFF/DESIGN_WORST_V*1000
out={'schema':3,'date':'2026-10-23','purpose':'V4 six-hour continuous camera+tactile+dual-IMU budget','battery':{'part':'Jauch LI18650JLS HB 1S2P / 250480','minimum_capacity_mah':BATTERY_MAH,'nominal_voltage_v':BATTERY_V,'minimum_nominal_energy_wh':round(nominal,6),'usable_energy_wh_after_20pct_capacity_reserve':round(usable,6)},'boundary':{'system_v_nominal':SYSTEM_V,'system_v_design_worst':DESIGN_WORST_V,'imu_supply_v':IMU_V,'converter_efficiency':CONVERTER_EFF,'battery_path_resistance_allocation_ohm':PATH_RESISTANCE_OHM,'path_loss_evaluation_pack_v':LOSS_EVALUATION_PACK_V,'path_allocation_note':'190mohm includes protected-pack leads, connector/crimps, fuse, BQ25616 BATFET and PCB copper, with the documented factory lead-extension variant; requires measured assembly acceptance. Capacity reserve covers pack internal loss/early cutoff separately. Thermal and fuse tolerances are allocations, not manufacturer guarantees.','six_hour_max_equivalent_current_ma_at_design_worst':round(limit,6),'six_hour_max_system_power_w_at_design_worst':round(limit*DESIGN_WORST_V/1000,6),'capacity_reserve':'20% allocation for capacity loss and early cutoff; converter and external path losses separate. This is a design allowance, not a proven discharge-curve equivalence or lifetime guarantee.', 'capture_stop_v':3.2, 'capture_restart_v':3.55, 'capture_voltage_node':'VBAT after connector and fuse, referenced to board GND; not protected pack output', 'path_loss_source_node':'Protected pack output before external leads and board path;3.2V here is a conservative low-source loss/stress assumption' },'camera':{'rails_v':{'avdd':2.8,'dvdd':1.5,'dovdd':1.8},'external_core_max_current_ma':125,'total_conservative_input_current_ma':177,'method':'sum of LDO output currents; external DVDD remains powered in every conservative case'},'firmware_seen':{'pixel_format':'JPEG','frame_size':'VGA','jpeg_quality':12,'explicit_frame_rate_hz':54_000_000/(2060*2622),'frame_rate_status':'OV5640 registers target 9.99756fps with 24MHz XCLK, HTS2060,VTS2622. Actual frame timestamps and skipped frames remain recorded. No sensor power reduction assumed.'},'sd':{'chosen_reference':'Kingston Industrial microSD SDCIT2 family','host_mode':'SPI3 at20MHz','average_current_ma':100,'peak_current_ma':300,'source_note':'Selected SDCIT2 manufacturer sheet publishes no current limits.100mA average/300mA peak are design assumptions, requiring selected-card characterization.'},'esp32':{'wifi_tx_peak_ma':286,'wifi_rx_ma':95,'cpu_240mhz_dual_core_typ_max_table_ma':107.9,'note':'286mA is a Wi-Fi TX peak at 100% duty, not a guaranteed continuous part maximum; CPU allowance is separately duty-weighted in realistic case.'},'cases':cases,'sources':SOURCES,'acceptance':['Measure the external battery path at temperature and require <=190mohm equivalent; retain current/voltage traces.','Measure combined ESP current and TX/RX/CPU duty with actual VGA JPEG traffic.','Measure SD current at SPI20MHz with sustained writes; retain peak trace for converter sizing.','Measure all rails and battery current at thermal steady state for >=30 minutes and record frame rate, cutoff, and efficiency.']}
(OUT/'energy-budget.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({x['name']:x['result'] for x in cases},indent=2))
