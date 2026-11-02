#!/usr/bin/env python3
"""Reproduce cost arithmetic without turning incomplete prices into a full quote."""
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
from collections import Counter
import csv, hashlib, json, re
HERE = Path(__file__).resolve().parent
V4 = HERE.parent
ROOT = V4.parents[1]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def purchased_quantity(required, minimum=1, multiple=1):
    if required <= 0 or minimum <= 0 or multiple <= 0:
        raise ValueError('Positive quantities required')
    # Order multiple applies to the complete quantity, not only the excess over MOQ.
    return int((Decimal(max(required, minimum)) / Decimal(multiple)).to_integral_value(rounding=ROUND_CEILING)) * multiple

def complete_quote_total(quote, required_categories):
    """Use common-currency final quoted cash amounts. Unknown or omitted costs stay unknown."""
    covered = set()
    total = Decimal('0')
    for line in quote['lines']:
        covered.update(line['categories'])
        if line.get('cash_amount') is None or line.get('status') != 'quoted':
            return None
        if line.get('currency') != quote['currency']:
            return None
        amount = Decimal(str(line['cash_amount']))
        if not amount.is_finite() or amount < 0:
            raise ValueError('Finite nonnegative amount required')
        if not line.get('evidence'):
            return None
        total += amount
    if set(required_categories) != covered:
        return None
    return total

def balanced_blocks(s, prefix):
    # KiCad quoted strings may contain parentheses; honour escaping.
    pos = 0
    while True:
        start = s.find(prefix, pos)
        if start < 0:
            return
        depth = 0; quoted = False; escaped = False
        for i in range(start, len(s)):
            ch = s[i]
            if quoted:
                if escaped: escaped = False
                elif ch == '\\': escaped = True
                elif ch == '"': quoted = False
            elif ch == '"': quoted = True
            elif ch == '(': depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    yield s[start:i+1]
                    pos = i + 1
                    break
        else:
            raise ValueError('Unbalanced KiCad expression')

def main():
    lock = json.loads((HERE/'requirements-lock.json').read_text())
    assert sha(V4/'system-contract.json') == lock['baseline_contract_sha256'], 'Review changed contract'
    assert sha(V4/'electrical/components.json') == lock['baseline_components_sha256'], 'Review changed BOM'
    components = json.loads((V4/'electrical/components.json').read_text())['components']
    unique = len({c['mpn'] for c in components})
    rows = list(csv.DictReader((V4/'procurement/bom-source-plan.csv').open()))
    priced = []
    for r in rows:
        p = r['unit_price_snapshot']
        if r['scope'] == 'main-board' and 'JLC' in r['price_basis'] and re.fullmatch(r'[0-9]+\.?[0-9]*', p):
            extension = Decimal(p) * int(r['required_qty'])
            priced.append({'mpn':r['manufacturer_mpn'],'qty':int(r['required_qty']), 'historical_usd_extension':float(extension), 'source':r['source_url']})
    pcb_path = V4/'electrical/glove-v4-routing-candidate.kicad_pcb'
    pcb = pcb_path.read_text()
    footprints = list(balanced_blocks(pcb, '(footprint '))
    assert len(footprints) == len(components)
    sides = Counter()
    pads = Counter()
    for fp in footprints:
        side = re.search(r'\(layer "([FB]\.Cu)"\)', fp)
        assert side
        sides[side.group(1)] += 1
        for pad in balanced_blocks(fp, '(pad '):
            kind = re.match(r'\(pad "[^"]*" (\w+)', pad)
            assert kind
            pads[kind.group(1)] += 1
    fees = json.loads((HERE/'assembly-fees.json').read_text())
    std = fees['standard']
    loading = Decimal(str(std['loading_per_component_type'])) * unique
    # All rates below are published-fee scenarios; eligibility and exact feeders need a quote.
    comparisons = []
    for types in (unique, 80, 60, 40):
        comparisons.append({'unique_types':types,'standard_loading_usd':round(types*std['loading_per_component_type'],2),'delta_vs_current_usd':round((unique-types)*std['loading_per_component_type'],2),'status':'arithmetic_only; no replacement BOM exists for reduced type counts'})
    power = json.loads((V4/'verification/energy-budget.json').read_text())
    pbat = next(c for c in power['cases'] if c['name']=='conservative_sustained_design')['result']['battery_input_power_w_at_3v55']
    cases=[]
    for name,ah,v in [('selected_Jauch_minimum',6.5,3.6),('candidate_nominal_6Ah',6,3.7),('candidate_nominal_4p8Ah',4.8,3.7)]:
        hours=ah*v*.8/pbat
        cases.append({'name':name,'capacity_ah':ah,'nominal_v':v,'battery_input_power_w':pbat,'runtime_h':hours,'meets_arithmetic_six_hours':hours>=6,'status':'calculation_only; nominal candidate capacities are not guaranteed minimum capacity'})
    categories=lock['required_cost_categories']
    quotes={name:{'currency':'USD','lines':[{'categories':[category],'cash_amount':None,'status':'unquoted','currency':'USD','evidence':None} for category in categories]} for name in ['baseline','cost_reduced']}
    template=HERE/'quote-comparison-template.json'
    if not template.exists():template.write_text(json.dumps(quotes,indent=2)+'\n')
    totals={name:complete_quote_total(q,categories) for name,q in json.loads(template.read_text()).items()}
    total_values={name:float(n) if n is not None else None for name,n in totals.items()}
    ratio = (float(totals['cost_reduced']/totals['baseline']) if all(v is not None and v>0 for v in totals.values()) else None)
    qualification = json.loads((HERE/'qualification-status.json').read_text())
    qualified = bool(qualification['gates']) and all(g['status']=='passed' and g['evidence'] and all((ROOT/e).is_file() for e in g['evidence']) for g in qualification['gates'].values())
    price_met = ratio is not None and ratio <= 1/3
    output={
      'schema':1,'date':'2026-10-23','source_hashes':{'components':sha(V4/'electrical/components.json'),'board':sha(pcb_path),'cost_rows':sha(V4/'procurement/bom-source-plan.csv'),'system_contract':sha(V4/'system-contract.json')},
      'current_board':{'placements':len(components),'unique_mpn':unique,'subsystems':dict(Counter(c['subsystem'] for c in components)),'placement_sides':dict(sides),'physical_pad_types':dict(pads),'joint_count_note':'Physical pad count from canonical KiCad; includes separate exposed-pad lands. Vendor billed count may differ.'},
      'historical_component_subset':{'usd':float(sum(Decimal(str(p['historical_usd_extension'])) for p in priced)),'mpn_rows':len(priced),'placements':sum(p['qty'] for p in priced),'costs':sorted(priced,key=lambda p:p['historical_usd_extension'],reverse=True),'excluded':'All unpriced rows, mixed currency Comet rows, minimum order/attrition, PCBs, assembly and external kit. Not a current quote.'},
      'assembly_scenarios':{'standard_loading_current_types_usd':float(loading),'type_count_sensitivity':comparisons,'minimum_assembled_quantity':fees['minimum_order_boards'],'economic_eligible_as_drawn':False,'eligibility_blockers':fees['current_blockers'],'price_source':fees['source']},
      'battery_screen':cases,
      'wire_candidate':{'baseline':'Alpha 5851 BK005 100ft spool','baseline_observed_goods_usd':143.30,'candidate':'2 × Adafruit 3164 50ft spool','candidate_observed_goods_usd':9.90,'goods_difference_usd':133.40,'total_nominal_length_m':30.48,'stock_observation':'Adafruit in stock; Mouser US page111; quantities not reserved','unit_length_note':'Adafruit rounds50ft to15.2m; procure total100ft. Actual conductor cut schedule remains to close.','source':'https://www.adafruit.com/product/3164','decision':'candidate_for_harness_qualification','canonical_substitution_approved':False,'open':['Sofia delivered quote','actual total cut length and markings','GH crimp pull/retention and strand count','insulation bond/strain relief','bundle fit and glove feel','cable capacitance/leakage/motion artifact under PVDF acquisition']},
      'complete_delivered_totals_usd':total_values,'cost_ratio':ratio,'price_target_met':price_met,'candidate_qualified':qualified,'threefold_reduction_achieved':price_met and qualified,'manufacturing_ready':False,
      'scope':'Sourcing/engineering cost screen. Baseline and cheaper complete glove remain unquoted and unreleased.'}
    (HERE/'cost-review.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'historical_priced_subset_usd':output['historical_component_subset']['usd'],'board':output['current_board'],'loading_scenario_usd':float(loading),'complete_totals':total_values,'threefold_reduction_achieved':output['threefold_reduction_achieved']},indent=2))

if __name__=='__main__':main()
