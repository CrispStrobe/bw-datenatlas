#!/usr/bin/env python3
"""Build the presentation data from the immutable v3 research snapshot. No network."""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'data'

def dump(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')

def main() -> None:
    with zipfile.ZipFile(ROOT / 'inputs/research-v3.zip') as archive:
        raw_bytes = archive.read('muslime_bw_daten.json')
        raw = json.loads(raw_bytes)
    audit = json.loads((ROOT / 'inputs/source-audit.json').read_text(encoding='utf-8'))
    obs = raw['observations']
    def rows(dataset: str, indicator: str | None = None):
        return [r for r in obs if r['dataset_id'] == dataset and (indicator is None or r['indicator'] == indicator)]
    def one(dataset: str, indicator: str, geo: str):
        found = [r for r in rows(dataset, indicator) if r['geo_id'] == geo]
        if len(found) != 1:
            raise ValueError(f'Expected one row: {dataset}, {indicator}, {geo}; found {len(found)}')
        return found[0]
    def compact(r):
        return {k: r.get(k) for k in ['observation_id','dataset_id','reference_period','reference_period_type','geo_id','geo_name','indicator','dimensions','value','value_lower','value_upper','unit','comparator','source_id','source_locator','measurement_type','definition_id','quality_flags','note']}

    # Do not mutate the old research snapshot. Apply documented source metadata overlays only.
    sources = {s['source_id']: dict(s) for s in raw['sources']}
    sources['stala_monat_2020'].update({
        'url': audit['source_access']['brachat_schwarz']['url'],
        'access_status':'original_checked_in_addendum',
        'limitation':'Historische Schätzung. Keine neue Schätzung für 2025.',
        'locator':'Statistisches Monatsheft 4/2020, S. 3–10'})
    sources['bamf_mld2020_full'].update({
        'url':audit['source_access']['fb38_original_mld']['url'],
        'limitation':'Befragungsparameter 2019/2020. Nicht alle Tabellen des Berichts werden hier verwendet.'})

    districts = []
    for r in rows('bw_population_2024','population_total'):
        if r['geo_level'] != 'district':
            continue
        foreign = one('bw_population_2024','foreign_citizens',r['geo_id'])
        german = one('bw_population_2024','german_citizens',r['geo_id'])
        districts.append({
            'id':r['geo_id'][2:], 'geo_id':r['geo_id'], 'name':r['geo_name'],
            'population':r['value'], 'foreign':foreign['value'], 'german':german['value'],
            'foreign_pct':100*foreign['value']/r['value'],
            'reference_period':r['reference_period'], 'source_id':r['source_id'],
            'source_ids':[r['observation_id'],foreign['observation_id'],german['observation_id']],
            'foreign_pct_derivation':'100 * foreign / population',
            'muslim_count':None, 'muslim_pct':None,
            'religion_data_status':'not_available_at_this_geographic_level'})
    districts.sort(key=lambda r:r['id'])
    assert len(districts) == 44

    municipalities = json.loads((ROOT/'inputs/municipalities-2024-06.json').read_text(encoding='utf-8'))
    bw = compact(one('bamf_fb55_states_2025','estimated_muslim_persons','DE08'))
    bw_pct = compact(one('bamf_fb55_state_population_shares_2025','estimated_muslim_share','DE08'))
    origins = [compact(r) for r in rows('bamf_fb55_origin_model_2025','estimated_muslim_persons') if r['dimensions']['row_type']=='origin_group']
    regions = [compact(r) for r in rows('bamf_fb55_origin_model_2025','estimated_muslim_persons') if r['dimensions']['row_type']=='region_subtotal']
    total = next(compact(r) for r in rows('bamf_fb55_origin_model_2025','estimated_muslim_persons') if r['dimensions']['row_type']=='total')
    for r in origins:
        r['share_of_published_de_total'] = r['value']/total['value']*100
        r['share_derivation'] = '100 * published_group_midpoint / published_DE_midpoint; rounded source inputs'
        r['share_provenance'] = 'derived'
        r['share_denominator_observation_id'] = total['observation_id']
    state_ids = {r['geo_id'] for r in rows('bamf_fb55_state_population_shares_2025')}
    states = []
    for r in rows('bamf_fb55_states_2025','estimated_muslim_persons'):
        if r['geo_id'] in state_ids:
            share = one('bamf_fb55_state_population_shares_2025','estimated_muslim_share',r['geo_id'])
            states.append({'name':r['geo_name'],'geo_id':r['geo_id'],'low':r['value_lower'],'high':r['value_upper'],
                           'pct_low':share['value_lower'],'pct_high':share['value_upper'],
                           'source_ids':[r['observation_id'],share['observation_id']]})
    selected_nationalities = [compact(r) for r in rows('bw_azr_nationalities','foreign_citizens_by_nationality') if r['dimensions'].get('sex')=='all']
    flows = [compact(r) for r in rows('bw_asylum_registrations_2014_2026','asylum_registrations_retained_bw')]
    # Carry the original numerical records and scope, but not unchecked parameters, into charts.
    app = {
        'version':'1.0.0', 'built_on':'2026-09-23', 'input_version':raw['package_version'],
        'input_sha256':hashlib.sha256(raw_bytes).hexdigest(),
        'scope':'Published state estimates and national origin statistics; no measured district or municipal religion data.',
        'bw':bw, 'bw_pct':bw_pct, 'de_total':total,
        'districts':districts, 'municipalities':municipalities, 'states':states,
        'origins_de_2025':origins, 'regions_de_2025':regions,
        'origin_composition':[compact(r) for r in rows('bamf_fb55_origin_composition')],
        'nationalities_bw':selected_nationalities,
        'historical_bw':[compact(r) for r in rows('bw_historical_estimates')],
        'flows_bw':flows,
        'visa_purposes':[compact(r) for r in rows('aa_national_visa_purposes_2024_2025')],
        'datasets':raw['datasets'], 'sources':sources,
        'source_issues':raw['source_issues_v3'],
        'source_audit':{
            'checked_on':audit['checked_on'],
            'scope':audit['scope'],
            'online_fb55_identity_verified':False,
            'parameter_comparison':audit['bamf_percentage_comparison'],
            'brachat_schwarz':audit['source_access']['brachat_schwarz']},
        'counts':{'research_observations':len(obs),'districts':len(districts),'municipalities':len(municipalities),'origin_groups_de':len(origins)},
        'model':{
            'id':'illustrative_allocation_v1',
            'type':'user_defined_scenario_not_estimate',
            'formula':'T * ((1-w) * P_k / sum(P) + w * A_k / sum(A))',
            'population_reference':'2024-11-30','calibration_reference':'2025',
            'w_range':[0,1],'T_range':[bw['value_lower'],bw['value_upper']],
            'default_enabled':False,'default_weight':0.5,
            'not_identified_from_data':True,
            'confidence_interval':None,
            'warning':'Nur ein frei gewählter Verteilungsschlüssel. Keine empirische Schätzung muslimischer Bevölkerung eines Kreises; die resultierenden Werte haben keine regionale Gültigkeitsbestätigung.'}
    }
    assert len(origins)==18 and len(states)==14
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT/'atlas.json',app)
    (OUT/'atlas-data.js').write_text('window.ATLAS_DATA='+json.dumps(app,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf-8')
    dump(OUT/'research-observations.json',obs)
    dump(OUT/'districts-2024-11.json',districts)
    dump(OUT/'origins-de-2025.json',origins)
    dump(OUT/'municipalities-2024-06.json',municipalities)
    dump(OUT/'source-audit.json',audit)
    dump(OUT/'sources.json',sources)
    # Source-supported municipal religion values remain null throughout the application.
    for name,data in [('districts-2024-11',districts),('municipalities-2024-06',municipalities)]:
        with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(data[0]))
            wr.writeheader()
            for r in data: wr.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    shutil.copy(ROOT/'inputs/research-v3.zip',ROOT/'docs/downloads/research-v3-with-audit.zip')
    print(f'Built {len(districts)} districts, {len(municipalities)} municipality rows, {len(origins)} national origin groups.')

if __name__ == '__main__':
    main()
