#!/usr/bin/env python3
"""Leitet die vier Regierungsbezirke — NUTS 2 — aus den Kreisen ab.

Baden-Württemberg hat auf NUTS-2-Ebene vier Regionen, und sie sind exakte
Zusammenfassungen der Kreise: die dritte Stelle des Amtlichen Gemeindeschlüssels
sagt, zu welcher. 081 Stuttgart (DE11), 082 Karlsruhe (DE12), 083 Freiburg (DE13),
084 Tübingen (DE14). Nichts daran ist geschätzt.

Die Flächen entstehen durch Verschmelzen der Kreisflächen. Dabei bleiben mehrere
getrennte Teile stehen, und das ist richtig so: es sind wirkliche Exklaven, keine
Rundungsreste. Ein Puffer von zwei Hundertstel Kilometern schließt sie nicht — hätte
er es getan, wären es Lücken aus der Koordinatenrundung gewesen.

Die Zahlen werden addiert, nicht neu geschätzt. Bei der Modellrechnung werden untere
und obere Grenze getrennt summiert; das ist die vorsichtige Lesart, denn sie
unterstellt, dass alle Kreise gleichzeitig am unteren oder am oberen Rand liegen.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGIONEN = {
    '081': ('DE11', 'Stuttgart'),
    '082': ('DE12', 'Karlsruhe'),
    '083': ('DE13', 'Freiburg'),
    '084': ('DE14', 'Tübingen'),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--geometry', type=Path, default=ROOT / 'docs/data/geometry.json')
    ap.add_argument('--atlas', type=Path, default=ROOT / 'docs/data/atlas.json')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/regions.json')
    args = ap.parse_args()

    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    geo = json.loads(args.geometry.read_text(encoding='utf-8'))
    atlas = json.loads(args.atlas.read_text(encoding='utf-8'))
    kreise = {str(d['id']): d for d in atlas['districts']}

    flaechen: dict[str, list] = {}
    for f in geo['districts']:
        flaechen.setdefault(str(f['properties']['id'])[:3], []).append(shape(f['geometry']))

    fehlend = set(REGIONEN) - set(flaechen)
    if fehlend:
        raise SystemExit(f'Kreise ohne Regierungsbezirk: {sorted(fehlend)}')

    merkmale, tabelle = [], []
    for schluessel, (nuts, name) in sorted(REGIONEN.items()):
        vereinigt = unary_union([t.buffer(0) for t in flaechen[schluessel]])
        teile = list(vereinigt.geoms) if hasattr(vereinigt, 'geoms') else [vereinigt]
        gross = max(teile, key=lambda p: p.area)
        mitglieder = [k for k in kreise.values() if str(k['id']).startswith(schluessel)]

        def summe(feld):
            werte = [m.get(feld) for m in mitglieder]
            return sum(w for w in werte if isinstance(w, (int, float))) if any(
                isinstance(w, (int, float)) for w in werte) else None

        einwohner, auslaendisch = summe('population'), summe('foreign')
        zeile = {
            'id': schluessel, 'nuts': nuts, 'name': name,
            'districts': len(mitglieder),
            'population': einwohner,
            'foreign': auslaendisch,
            'foreign_pct': round(100 * auslaendisch / einwohner, 2)
                           if einwohner and auslaendisch is not None else None,
            # Ein Punkt für die Beschriftung: der Schwerpunkt kann außerhalb liegen,
            # wenn eine Region gebogen ist. representative_point liegt immer drin.
            'label_point': [round(gross.representative_point().x, 5),
                            round(gross.representative_point().y, 5)],
        }
        tabelle.append(zeile)
        merkmale.append({'type': 'Feature',
                         'properties': {k: v for k, v in zeile.items() if k != 'label_point'}
                                       | {'label_point': zeile['label_point']},
                         'geometry': json.loads(json.dumps(mapping(
                             vereinigt.simplify(0.0004, preserve_topology=True)),
                             default=float))})
        print(f'  {nuts} {name:11s} {len(mitglieder):2d} Kreise, '
              f'{einwohner:>9,} Einwohner, {len(teile)} Teilfläche(n)'.replace(',', '.'))

    def runden(wert):
        if isinstance(wert, float):
            return round(wert, 5)
        if isinstance(wert, list):
            return [runden(x) for x in wert]
        if isinstance(wert, dict):
            return {k: runden(v) for k, v in wert.items()}
        return wert

    doc = {
        'type': 'atlas_nuts2_regions',
        'schema_version': '1.0',
        'what_this_is': ('Die vier Regierungsbezirke Baden-Württembergs, die Ebene NUTS 2 '
                         'der europäischen Gebietssystematik. Flächen aus den Kreisflächen '
                         'verschmolzen, Zahlen aus den Kreiszahlen addiert — nichts daran '
                         'ist geschätzt oder modelliert.'),
        'derived_from': 'docs/data/geometry.json und docs/data/atlas.json',
        'geometry_reference': geo.get('geometry_reference'),
        'attribution': geo.get('attribution'),
        'licence': geo.get('license'),
        'regions': tabelle,
        'features': runden(merkmale),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    args.out.with_name('regions-data.js').write_text(
        'window.ATLAS_REGIONS=' + json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    gesamt = sum(r['population'] for r in tabelle if r['population'])
    print(f'{len(tabelle)} Regionen, zusammen {gesamt:,} Einwohner'.replace(',', '.'))


if __name__ == '__main__':
    main()
