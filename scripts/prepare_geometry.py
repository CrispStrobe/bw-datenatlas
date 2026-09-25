#!/usr/bin/env python3
"""Fetch archived official BKG boundaries and build locally hosted BW GeoJSON.

The archive is NOT bundled. On GitHub Actions this script runs before publication.
Requires the optional requirements-geography.txt dependencies. No geocoding service.
Names are matched only within the same official district, never by fuzzy inference.
"""
from __future__ import annotations
import argparse
import collections
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2024/vg250_01-01.utm32s.shape.ebenen.zip'
PRODUCT_URL = 'https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html'
LICENSE_URL = 'https://www.govdata.de/dl-de/by-2-0'


def norm_name(s: str) -> str:
    s = s.split(',')[0].casefold().replace('ß','ss')
    s = ''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]','',s)


def fetch(path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL,headers={'User-Agent':'BW-Datenatlas/1.0 (public BKG archive download)'})
            with urllib.request.urlopen(req, timeout=120) as r, path.with_suffix('.part').open('wb') as f:
                while chunk := r.read(1024*1024): f.write(chunk)
            path.with_suffix('.part').replace(path)
            return
        except (OSError, urllib.error.URLError) as e:
            if attempt == 2:
                raise RuntimeError('BKG-Download fehlgeschlagen. Erneut starten oder das offizielle ZIP mit --archive DATEI übergeben. Keine Ersatzgrenzen wurden erzeugt.') from e
            time.sleep(3*(attempt+1))


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,help='Local official BKG 2024 UTM32s shapefile archive instead of download')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/data/geometry.json')
    args=parser.parse_args()
    try:
        import shapefile
        from pyproj import CRS, Transformer
        from shapely.geometry import shape, mapping
        from shapely.ops import transform, unary_union
    except ImportError as e:
        raise SystemExit('Install: python -m pip install -r requirements-geography.txt') from e
    app=json.loads((ROOT/'docs/data/atlas.json').read_text(encoding='utf-8'))
    path=args.archive or ROOT/'.cache/vg250-2024.zip'
    if not path.is_file():
        if args.archive: raise FileNotFoundError(path)
        fetch(path)
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        def read_level(level: str, width: int):
            matches=[n for n in names if n.lower().endswith(f'vg250_{level}.shp')]
            if len(matches)!=1: raise ValueError(f'Expected one VG250_{level}.shp in archive, found {matches}')
            base=matches[0][:-4]
            lookup={n.lower():n for n in names}
            def member(ext): return z.read(lookup[(base+ext).lower()])
            try: encoding=member('.cpg').decode().strip()
            except KeyError: encoding='utf-8'
            if encoding=='65001': encoding='utf-8'
            reader=shapefile.Reader(shp=io.BytesIO(member('.shp')),shx=io.BytesIO(member('.shx')),dbf=io.BytesIO(member('.dbf')),encoding=encoding)
            crs=CRS.from_wkt(member('.prj').decode('utf-8'))
            to_lonlat=Transformer.from_crs(crs,4326,always_xy=True).transform
            parts=collections.defaultdict(list); props={}
            gf_filter_applied=False
            for sr in reader.iterShapeRecords():
                row={k.upper():v for k,v in sr.record.as_dict().items()}
                ags=str(row.get('AGS','')).zfill(width)
                if not ags.startswith('08'): continue
                # VG250 GF=4 denotes land areas. Water geometries are not used for the thematic map.
                if 'GF' in row and int(row['GF']) != 4: continue
                gf_filter_applied = 'GF' in row
                geom=shape(sr.shape.__geo_interface__)
                if not geom.is_valid:
                    from shapely import make_valid
                    geom=make_valid(geom)
                parts[ags].append(geom)
                props[ags]={'id':ags,'name':row['GEN'],'administrative_type':row.get('BEZ',''),'district_code':ags[:5]}
            features=[]; original_union=[]
            for ags in sorted(parts):
                geom=unary_union(parts[ags])
                # Transform before simplifying; use a common metric CRS for a 40 m cartographic tolerance.
                to_metric=Transformer.from_crs(crs,25832,always_xy=True).transform
                metric=transform(to_metric,geom).simplify(40,preserve_topology=True)
                result=transform(Transformer.from_crs(25832,4326,always_xy=True).transform,metric)
                original_union.append(transform(to_lonlat,geom))
                p=result.representative_point()
                prop=dict(props[ags]); prop['label_point']=[round(p.x,5),round(p.y,5)]
                features.append({'type':'Feature','properties':prop,'geometry':mapping(result)})
            return features,unary_union(original_union),gf_filter_applied
        districts,outline,gf=read_level('krs',5)
        municipalities,_,_=read_level('gem',8)
    expected={r['id'] for r in app['districts']}
    found={f['properties']['id'] for f in districts}
    if found != expected: raise ValueError(f'District key mismatch: missing={expected-found}, extra={found-expected}')
    indices=collections.defaultdict(list)
    for m in app['municipalities']: indices[(m['district_code'],norm_name(m['municipality_name']))].append(m)
    used=set(); crosswalk=[]; no_statistics=[]
    # VG250 'gem' also carries unincorporated areas (gemeindefreie Gebiete). These are not
    # municipalities, carry no municipal population statistics, and may repeat the name of a
    # neighbouring municipality in the same district (e.g. 08317971 Rheinau next to the town
    # 08317153 Rheinau). They are excluded from the statistical join and disclosed instead.
    NON_MUNICIPAL={'Gemeindefreies Gebiet'}
    for f in municipalities:
        p=f['properties']
        candidates=[] if p['administrative_type'] in NON_MUNICIPAL else indices.get((p['district_code'],norm_name(p['name'])),[])
        if len(candidates)==1:
            m=candidates[0]
            if m['geo_id'] in used: raise ValueError('Nonunique municipal name match: '+m['geo_id'])
            used.add(m['geo_id']); p['statistical_geo_id']=m['geo_id']
            crosswalk.append({'geo_id':m['geo_id'],'ags':p['id'],'source_name':m['municipality_name'],'bkg_name':p['name'],
                              'method':'exact_normalized_name_within_official_district','geometry_date':'2024-01-01'})
        else:
            p['statistical_geo_id']=None
            no_statistics.append({'ags':p['id'],'bkg_name':p['name'],'administrative_type':p['administrative_type'],
                                  'reason':'not_a_municipality' if p['administrative_type'] in NON_MUNICIPAL else 'no_unique_name_match_in_district'})
    unmatched=[{'geo_id':m['geo_id'],'name':m['municipality_name'],'district_code':m['district_code']} for m in app['municipalities'] if m['geo_id'] not in used]
    # Fail a badly misconfigured match, but retain and disclose isolated unmatched geometries.
    if len(used)<1050: raise ValueError(f'Only {len(used)}/1101 municipalities matched. No fuzzy matches will be invented.')
    data={
        'type':'atlas_geography','schema_version':'1.0','geometry_reference':'2024-01-01',
        'source_url':URL,'product_url':PRODUCT_URL,'license':'Datenlizenz Deutschland – Namensnennung 2.0','license_url':LICENSE_URL,
        'attribution':'© BKG 2026, dl-de/by-2-0; Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf',
        'modifications':'BW selection, GF=4 land areas, dissolve by AGS, reprojection to WGS84, 40 m simplification, coordinate rounding to five decimals, statistical joins.',
        'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'state':{'type':'Feature','properties':{'id':'08','name':'Baden-Württemberg'},'geometry':mapping(outline.simplify(.0004,preserve_topology=True))},
        'districts':districts,'municipalities':municipalities,
        'municipality_match_count':len(used),'municipalities_unmatched':unmatched,'geometries_without_statistics':no_statistics,
        'crosswalk':crosswalk,'gf_land_filter_applied':gf,
    }
    # Rounding applies to geometry coordinates and label points, not statistical data.
    def round_coords(value):
        if isinstance(value,float): return round(value,5)
        if isinstance(value,(list,tuple)): return [round_coords(x) for x in value]
        if isinstance(value,dict): return {k:round_coords(v) for k,v in value.items()}
        return value
    data=round_coords(data)
    for feature in districts+municipalities:
        lo,la=feature['properties']['label_point']
        if not (7 < lo < 11 and 47 < la < 51): raise ValueError('CRS / coordinate order failed')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    args.output.write_text(text,encoding='utf-8')
    args.output.with_name('geometry-data.js').write_text('window.ATLAS_GEOMETRY='+text+';\n',encoding='utf-8')
    args.output.with_name('geometry-status.json').write_text(json.dumps({'status':'prepared_from_supplied_or_downloaded_archive','built_at':datetime.now(timezone.utc).isoformat(),'geometry_reference':data['geometry_reference'],'archive_sha256':data['archive_sha256'],'district_count':len(districts),'statistical_municipalities_matched':len(used),'unmatched_statistical_municipalities':unmatched,'note':'Archive provenance and data sources remain in geometry.json; synthetic archives are for isolated tests only.'},ensure_ascii=False,indent=2),encoding='utf-8')
    args.output.with_name('municipality-ags-crosswalk.json').write_text(json.dumps(crosswalk,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Geography ready: {len(districts)} districts, {len(municipalities)} municipality/municipality-free areas; {len(used)}/1101 statistical municipalities matched.')
    if unmatched: print('UNMATCHED (not guessed):',unmatched)

if __name__=='__main__': main()
