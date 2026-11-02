#!/usr/bin/env python3
"""Battery-entry topology and explicit loss/protection design allocations.

These checks exercise the canonical circuit and algebra. Thermal/current-pulse
qualification remains a hardware acceptance item, never a simulated pass.
"""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
FUSE_RATING_A = 2.5
CONTINUOUS_DERATING = 0.75
TEMPERATURE_FACTOR_ALLOCATION = 0.85
PATH_RESISTANCE_ALLOCATION_OHM = 0.190
PACK_LOWER_BOUND_V = 3.2
CONVERTER_EFFICIENCY_ALLOCATION = 0.80


def constant_power_current(power_w, voltage_v, resistance_ohm):
    """Stable low-current root of P=(V-I*R)*I; reject collapse/negative inputs."""
    if power_w < 0 or voltage_v <= 0 or resistance_ohm < 0:
        raise ValueError('Invalid load or source')
    discriminant = voltage_v * voltage_v - 4 * resistance_ohm * power_w
    if discriminant <= 0:
        raise ValueError('No stable DC operating point at this allocation')
    return 2 * power_w / (voltage_v + math.sqrt(discriminant))


def main():
    source = ROOT / 'power/power-circuit.json'
    circuit = json.loads(source.read_text())
    parts = {p['ref']: p for p in circuit['parts']}
    checks = []

    def check(name, passed, details):
        checks.append({'name': name, 'status': 'pass' if passed else 'fail', 'details': details})

    entry = sorted((p['ref'], pin) for p in circuit['parts']
                   for pin, net in p.get('pins', {}).items() if net == 'VBAT_ENTRY')
    check('Fuse precedes every board battery branch',
          entry == [('F_BAT', '1'), ('J_BAT', '1')]
          and parts['F_BAT']['pins'] == {'1': 'VBAT_ENTRY', '2': 'VBAT'}, entry)
    check('Exact direct-AWG22 battery header and fuse',
          parts['J_BAT']['mpn'] == '43045-0200'
          and parts['J_BAT']['pins'] == {'1': 'VBAT_ENTRY', '2': 'GND'}
          and parts['F_BAT']['mpn'] == '045102.5MRL',
          {'header': parts['J_BAT']['mpn'], 'fuse': parts['F_BAT']['mpn']})

    # Copper estimate, two 75mm maximum leads, conservatively evaluated at65C.
    # 52.96mohm/m is AWG22 copper at20C; it is not 52.96ohm/m.
    wire = 2 * .075 * .05296 * (1 + .00393 * (65 - 20))
    # Molex PS43045:R contact<=10mohm initial +20mohm environmental delta;
    # termination<=5mohm initial. Two separate conductors.
    contacts = 2 * (.010 + .020 + .005)
    # Fuse datasheet gives nominal cold resistance only. The 2x hot/tolerance
    # allowance below is an engineering allocation, not a manufacturer bound.
    fuse = 2 * .0286
    batfet = .030  # TI BQ25616 RevA,p10,-40..125C maximum.
    copper = .015  # PCB entry/return paths allocation; routed solver must verify.
    subtotal = wire + contacts + fuse + batfet + copper
    check('Loss components fit explicit 190mohm acceptance allocation',
          subtotal < PATH_RESISTANCE_ALLOCATION_OHM,
          {'wire_65C_ohm': wire, 'two_contacts_and_crimps_ohm': contacts,
           'fuse_engineering_allocation_ohm': fuse, 'BATFET_max_ohm': batfet,
           'PCB_copper_allocation_ohm': copper, 'subtotal_ohm': subtotal,
           'assembly_acceptance_ceiling_ohm': PATH_RESISTANCE_ALLOCATION_OHM})

    # Factory fallback only: at most35mm added wire on each lead, including
    # overlap, and <=2mohm per joint. Reserve the entire added conductor length
    # even though the overlapped section is electrically parallel.
    extension_wire = 2 * .035 * .05296 * (1 + .00393 * (65 - 20))
    extension_joints = 2 * .002
    extension_subtotal = subtotal + extension_wire + extension_joints
    check('Factory extension variant fits the same path allocation',
          extension_subtotal < PATH_RESISTANCE_ALLOCATION_OHM,
          {'added_wire_max_per_lead_mm': 35,
           'added_wire_65C_ohm': extension_wire,
           'two_splices_acceptance_ohm': extension_joints,
           'extended_subtotal_ohm': extension_subtotal,
           'assembly_acceptance_ceiling_ohm': PATH_RESISTANCE_ALLOCATION_OHM,
           'direct_leads_preferred': True,
           'splice_resistance_requires_kelvin_measurement': True})

    step = constant_power_current(3.55 / CONVERTER_EFFICIENCY_ALLOCATION,
                                  PACK_LOWER_BOUND_V, PATH_RESISTANCE_ALLOCATION_OHM)
    charge = 1.28 / .999
    continuous = FUSE_RATING_A * CONTINUOUS_DERATING * TEMPERATURE_FACTOR_ALLOCATION
    check('Load step including path losses fits fuse allocation', step < continuous,
          {'1A_system_load_step_battery_current_A': step,
           'charge_corner_A': charge, 'fuse_continuous_allocation_A': continuous,
           'minimum_temperature_rerating_factor_required': step / (FUSE_RATING_A * CONTINUOUS_DERATING),
           'temperature_factor_is_allocation_requiring_current_datasheet_and_measured_ambient': True})
    check('Charge corner within pack rating', charge < circuit['battery']['max_charge_A'],
          {'charge_A': charge, 'pack_rating_A': circuit['battery']['max_charge_A']})
    check('200percent fuse test current below connector reference',
          2 * FUSE_RATING_A < 5.5,
          {'fault_fixture_current_A': 2 * FUSE_RATING_A, 'datasheet_max_opening_s_at25C': 5,
           'conservative_2circuit_AWG22_connector_reference_A': 5.5,
           'reference_not_installed_thermal_rating': True})

    # Independent algebra residual and adverse-input checks prevent a sign/root
    # error from silently overstating endurance/current headroom.
    residual = (PACK_LOWER_BOUND_V - step * PATH_RESISTANCE_ALLOCATION_OHM) * step - 3.55 / .80
    check('Constant-power equation residual', abs(residual) < 1e-12, {'residual_W': residual})
    try:
        constant_power_current(20, 3.2, .19)
        rejected = False
    except ValueError:
        rejected = True
    check('Voltage-collapse input rejected', rejected, {})

    result = {
        'schema': 1, 'circuit_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'checks': checks, 'failed_checks': [c['name'] for c in checks if c['status'] == 'fail'],
        'all_calculated_checks_pass': all(c['status'] == 'pass' for c in checks),
        'physical_validation': False,
        'sources': {
            'connector': 'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/430/43045/PS-43045-001.pdf',
            'fuse': 'https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1',
            'BATFET': 'https://www.ti.com/lit/ds/symlink/bq25616.pdf'},
        'qualification_required': [
            'Measure assembled path loss from protected pack output to converter input at temperature; require <=190mohm equivalent at load.',
            'Verify actual fuse ambient with current manufacturer rerating curve: required factor >=0.85, separate from75percent continuous derating.',
            'Characterize inrush and repeated startup I-squared-t; nominal1.029A2s melting value is not a guaranteed repetitive pulse limit.',
            'Use current-limited laboratory source and sacrificial fixture for5A fault opening; record current/time and connector/wire/PCB temperature. The5s rating applies at datasheet conditions.',
            'Check low voltage at converter input and capture cutoff with real source impedance; repeat native switching-model low-input case if outside its tested range.',
            'Physical six-hour endurance remains required with the production camera, SD and radio workload.'
        ]
    }
    (ROOT / 'power/battery-path-check-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'checks': len(checks), 'failures': result['failed_checks'],
                      'step_battery_A': step, 'fuse_continuous_allocation_A': continuous}, indent=2))
    return bool(result['failed_checks'])


if __name__ == '__main__':
    raise SystemExit(main())
