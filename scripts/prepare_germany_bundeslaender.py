#!/usr/bin/env python3
"""Baut die Deutschlandkarte: wie steht Baden-Württemberg unter den Ländern da?

Der Atlas zeigt Baden-Württemberg von innen — Kreise, Gemeinden, Regierungsbezirke —
und seit kurzem von außen, neben 293 europäischen Regionen. Dazwischen fehlte die
Ebene, nach der zuerst gefragt wird: der Vergleich mit den anderen Bundesländern.

Die Zahlen dafür liegen längst im Projekt. Der BAMF-Forschungsbericht 55 weist seine
Näherungswerte nicht nur für Deutschland und Baden-Württemberg aus, sondern für alle
Länder, und alle vierzehn Zeilen seiner Tabelle 3 stehen in den Beobachtungen. Nur
gezeichnet wurden sie nie.

Vierzehn Zeilen, nicht sechzehn: Bremen und Hamburg sowie Brandenburg und
Mecklenburg-Vorpommern wurden bei der Stichprobenziehung zusammengefasst und können
nach Auskunft des Berichts nur gemeinsam ausgewiesen werden. Die Karte fasst die
Flächen deshalb ebenso zusammen, statt einen Wert zweimal zu zeichnen und damit eine
Genauigkeit vorzutäuschen, die die Quelle ausdrücklich nicht hat.

Geometrie von GISCO, NUTS 1 — das ist für Deutschland die Ebene der Bundesländer.
"""
from __future__ import annotations
import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = 'BW-Datenatlas/1.0 (open data project; +https://github.com/CrispStrobe/bw-datenatlas)'
GISCO = ('https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/'
         'NUTS_RG_20M_2024_4326_LEVL_1.geojson')

# Die Beobachtungen führen die Länder unter dem amtlichen Gemeindeschlüssel mit
# vorangestelltem DE, die Geometrie unter dem NUTS-1-Code. Ohne diese Brücke fände
# keine Zeile ihre Fläche.
NUTS_JE_LAND = {
    'DE08': 'DE1', 'DE09': 'DE2', 'DE11': 'DE3', 'DE12': 'DE4', 'DE04': 'DE5',
    'DE02': 'DE6', 'DE06': 'DE7', 'DE13': 'DE8', 'DE03': 'DE9', 'DE05': 'DEA',
    'DE07': 'DEB', 'DE10': 'DEC', 'DE14': 'DED', 'DE15': 'DEE', 'DE01': 'DEF',
    'DE16': 'DEG',
}
# Was der Bericht nur gemeinsam ausweist, zeichnet die Karte nur gemeinsam.
ZUSAMMEN = {
    'DE04+DE02': ['DE04', 'DE02'],
    'DE12+DE13': ['DE12', 'DE13'],
}
# Aggregate, keine Länder.
KEINE_LAENDER = {'DE', 'DE_WEST_BERLIN', 'DE_EAST_NO_BERLIN'}


def hole(url: str) -> bytes:
    with urllib.request.urlopen(
            urllib.request.Request(url, headers={'User-Agent': UA}), timeout=240) as r:
        return r.read()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/germany-bundeslaender.json')
    args = ap.parse_args()

    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    obs = json.loads((ROOT / 'docs/data/research-observations.json')
                     .read_text(encoding='utf-8'))
    quellen = json.loads((ROOT / 'docs/data/sources.json').read_text(encoding='utf-8'))
    quellen = quellen.get('sources', quellen)

    laender: dict[str, dict] = {}
    for o in obs:
        if o.get('source_id') != 'bamf_fb55':
            continue
        geo = o.get('geo_id')
        if not geo or geo in KEINE_LAENDER or not geo.startswith('DE'):
            continue
        if o['indicator'] not in ('estimated_muslim_persons', 'estimated_muslim_share',
                                  'share_of_national_muslim_population'):
            continue
        e = laender.setdefault(geo, {'geo_id': geo, 'name': o.get('geo_name')})
        if o['indicator'] == 'estimated_muslim_persons':
            e['muslim_low'] = o.get('value_lower')
            e['muslim_high'] = o.get('value_upper')
            e['reference_year'] = o.get('reference_period')
        elif o['indicator'] == 'estimated_muslim_share':
            e['share_low'] = o.get('value_lower')
            e['share_high'] = o.get('value_upper')
            e['reference_year'] = o.get('reference_period')
        elif o['indicator'] == 'share_of_national_muslim_population':
            # Die räumliche Verteilung ist 2019 gemessen und wird auf 2025
            # fortgeschrieben — sie trägt deshalb ihr eigenes, älteres Jahr. Beide
            # in ein Feld zu schreiben hieße, die Schätzung auf 2019 zu datieren,
            # und genau das stand eine Fassung lang im Profil.
            e['share_of_national_pct'] = o.get('value')
            e['distribution_year'] = o.get('reference_period')

    for e in laender.values():
        # Eine Zahl für die Einfärbung. Die Spanne bleibt daneben stehen: gefärbt wird
        # nach der Mitte, gelesen wird die Spanne.
        for mitte, lo, hi in (('muslim_mid', 'muslim_low', 'muslim_high'),
                              ('share_mid', 'share_low', 'share_high')):
            a, b = e.get(lo), e.get(hi)
            e[mitte] = round((a + b) / 2, 2) if a is not None and b is not None else None

    flaechen = {f['properties']['NUTS_ID']: f
                for f in json.loads(hole(GISCO))['features']
                if f['properties']['NUTS_ID'].startswith('DE')}
    print(f'{len(flaechen)} NUTS-1-Flächen für Deutschland, '
          f'{len(laender)} Einträge aus dem Bericht')

    merkmale = []
    for geo, e in sorted(laender.items()):
        teile = ZUSAMMEN.get(geo, [geo])
        stuecke = [flaechen[NUTS_JE_LAND[t]] for t in teile if NUTS_JE_LAND.get(t) in flaechen]
        if len(stuecke) != len(teile):
            print(f'  WARNUNG: keine Fläche für {geo}')
            continue
        g = unary_union([shape(s['geometry']) for s in stuecke]).simplify(
            0.008, preserve_topology=True)
        merkmale.append({
            'type': 'Feature',
            'properties': {**e, 'id': geo,
                           'nuts': '+'.join(NUTS_JE_LAND[t] for t in teile),
                           'combined': len(teile) > 1},
            'geometry': json.loads(json.dumps(mapping(g), default=float)),
        })

    def runden(x):
        if isinstance(x, float):
            return round(x, 3)
        if isinstance(x, list):
            return [runden(v) for v in x]
        if isinstance(x, dict):
            return {k: runden(v) for k, v in x.items()}
        return x

    q = quellen.get('bamf_fb55', {})
    doc = {
        'type': 'germany_bundeslaender',
        'schema_version': '1.0',
        'what_this_is': ('Näherungswerte über die Zahl und den Anteil muslimischer '
                         'Religionsangehöriger je Bundesland, aus Tabelle 3 des '
                         'BAMF-Forschungsberichts 55. Dieselbe Quelle und dieselbe '
                         'Rechnung, aus der auch der Landeswert für Baden-Württemberg '
                         'stammt — hier für alle Länder nebeneinander.'),
        'caveat': ('Näherungswerte, keine Zählung. Sie beruhen auf der Annahme, dass '
                   'die 2019 gemessene räumliche Verteilung auch 2025 gilt. Länder mit '
                   'wenig Einwohnern reagieren darauf viel empfindlicher als große. '
                   'Bremen und Hamburg sowie Brandenburg und Mecklenburg-Vorpommern '
                   'weist der Bericht nur gemeinsam aus.'),
        'reference_year': next((e.get('reference_year') for e in laender.values()), None),
        'source_id': 'bamf_fb55',
        'source_title': q.get('title'),
        'source_url': q.get('url'),
        'source_locator': 'Forschungsbericht 55, Tabelle 3 und Abbildung 4',
        'publisher': q.get('publisher'),
        'geometry_source': 'Eurostat GISCO, NUTS 2024, Ebene 1, 1:20 Mio.',
        'count': len(merkmale),
        'features': runden(merkmale),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    args.out.with_name('germany-bundeslaender-data.js').write_text(
        'window.ATLAS_GERMANY=' + json.dumps(doc, ensure_ascii=False,
                                             separators=(',', ':')) + ';\n',
        encoding='utf-8')

    reihe = sorted((e for e in laender.values() if e.get('share_mid')),
                   key=lambda e: e['share_mid'], reverse=True)
    print(f'\n{len(merkmale)} Flächen, Anteil muslimischer Religionsangehöriger:')
    for i, e in enumerate(reihe, 1):
        markierung = ' <--' if e['geo_id'] == 'DE08' else ''
        print(f"  {i:2d}. {e['name'][:38]:38s} {e['share_low']}–{e['share_high']} % "
              f"· {e['muslim_low']:,}–{e['muslim_high']:,} Personen{markierung}"
              .replace(',', '.'))
    print(f"Datei: {args.out.stat().st_size // 1024} KiB")


if __name__ == '__main__':
    main()
