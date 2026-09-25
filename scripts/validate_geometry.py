#!/usr/bin/env python3
"""Deployment gate. Run only on the real, prepared BKG geometry, not placeholders."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'docs/data/geometry.json'
if not p.is_file(): raise SystemExit('STOP: No geometry.json. Run scripts/prepare_geometry.py first; no map will be deployed.')
g=json.loads(p.read_text(encoding='utf-8'))
a=json.loads((ROOT/'docs/data/atlas.json').read_text(encoding='utf-8'))
checks={
 'official_archive_url':g.get('source_url')=='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2024/vg250_01-01.utm32s.shape.ebenen.zip',
 'archived_reference_2024':g.get('geometry_reference')=='2024-01-01',
 'sha256_recorded':len(g.get('archive_sha256',''))==64,
 'district_keyset':{f['properties']['id'] for f in g['districts']}=={d['id'] for d in a['districts']},
 'district_count_44':len(g['districts'])==44,
 'municipal_match_minimum_1050':g.get('municipality_match_count',0)>=1050,
 'all_statistical_rows_accounted_for':g.get('municipality_match_count',0)+len(g.get('municipalities_unmatched',[]))==1101,
 'unique_municipal_matches':len({r['geo_id'] for r in g['crosswalk']})==len(g['crosswalk']),
 'valid_polygonal_types':all(f['geometry']['type'] in ('Polygon','MultiPolygon') for f in g['districts']+g['municipalities']),
 'no_synthetic_test_flag':not g.get('synthetic_test_fixture',False),
}
report={'checks':checks,'passed':all(checks.values()),'matched_municipalities':g['municipality_match_count'],'unmatched':g['municipalities_unmatched'],'note':'Checks concern structural integrity and joins, not validation of population estimates. Archive URL and SHA are provenance records, not a digital signature.'}
(ROOT/'docs/data/geography-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for name,passed in checks.items(): print(('PASS ' if passed else 'FAIL ')+name)
if not report['passed']: sys.exit(1)
print('Map deployment gate passed. Unmatched municipalities:',len(g['municipalities_unmatched']))
