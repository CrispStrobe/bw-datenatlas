#!/usr/bin/env python3
"""Holt eine europäische Vergleichsgröße auf NUTS-2-Ebene von Eurostat.

Die vier Regierungsbezirke sind NUTS-2-Regionen wie 299 andere in Europa. Damit lässt
sich die Frage stellen, die eine Karte von Baden-Württemberg allein nicht beantwortet:
liegt der Südwesten hoch oder niedrig, und im Vergleich womit?

Gezeigt wird der Anteil der im Ausland Geborenen an der Bevölkerung von 15 bis 64
Jahren in Privathaushalten (Eurostat lfst_r_lfsd2pwc). Das ist **nicht** dieselbe
Größe wie der Ausländeranteil im Atlas: gezählt wird der Geburtsort, nicht der Pass.
Wer eingebürgert ist, zählt hier mit und dort nicht — deshalb liegen die Werte höher
und die beiden Ebenen dürfen nicht nebeneinandergelegt werden, als wären sie dasselbe.

Die Zahlen stammen aus der Arbeitskräfteerhebung, einer Stichprobe. Kleine Regionen
tragen entsprechend Unsicherheit, die Eurostat nicht je Region ausweist.

Geometrie von GISCO, 1:20 Mio., vereinfacht.
"""
from __future__ import annotations
import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = 'BW-Datenatlas/1.0 (open data project; +https://github.com/CrispStrobe/bw-datenatlas)'
DATENSATZ = 'lfst_r_lfsd2pwc'
API = ('https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
       + DATENSATZ + '?format=JSON&sex=T&age=Y15-64&wstatus=POP'
       '&c_birth=FOR&c_birth=TOTAL&time={jahr}')
GISCO = ('https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/'
         'NUTS_RG_20M_2024_4326_LEVL_2.geojson')


def hole(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jahr', default='2024')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/eurostat-nuts2.json')
    args = ap.parse_args()

    from shapely.geometry import shape, mapping

    roh = json.loads(hole(API.format(jahr=args.jahr)))
    geo_index = roh['dimension']['geo']['category']['index']
    geo_label = roh['dimension']['geo']['category']['label']
    cb_index = roh['dimension']['c_birth']['category']['index']
    werte = roh['value']
    groessen = roh['size']
    dims = roh['id']
    # Der Index ist flach; die Lage eines Wertes ergibt sich aus dem Produkt der
    # nachfolgenden Achsenlängen. Nur so lassen sich zwei Achsen gleichzeitig lesen.
    schritt = {}
    faktor = 1
    for name, laenge in reversed(list(zip(dims, groessen))):
        schritt[name] = faktor
        faktor *= laenge

    def wert(code: str, geburt: str):
        i = geo_index[code] * schritt['geo'] + cb_index[geburt] * schritt['c_birth']
        return werte.get(str(i))

    regionen = {}
    for code in geo_index:
        # Vier Zeichen allein genügt nicht: EA21 ist die Eurozone, keine Region, und
        # stünde sonst in der Rangliste zwischen den Regionen.
        if len(code) != 4 or code[:2] in ('EA', 'EU'):
            continue
        gesamt, fremd = wert(code, 'TOTAL'), wert(code, 'FOR')
        if not gesamt or fremd is None:
            continue
        regionen[code] = {
            'nuts': code, 'country': code[:2],
            'name': geo_label.get(code, code),
            'population_ths': gesamt,
            'foreign_born_ths': fremd,
            'foreign_born_pct': round(100 * fremd / gesamt, 1),
        }
    print(f'{len(regionen)} NUTS-2-Regionen mit Werten für {args.jahr}')

    flaechen = json.loads(hole(GISCO))
    merkmale = []
    for f in flaechen['features']:
        code = f['properties']['NUTS_ID']
        if code not in regionen:
            continue
        g = shape(f['geometry']).simplify(0.02, preserve_topology=True)
        if g.is_empty:
            continue
        merkmale.append({
            'type': 'Feature',
            'properties': {**regionen[code],
                           'name_de': f['properties'].get('NAME_GERM') or regionen[code]['name'],
                           'name_en': f['properties'].get('NAME_ENGL') or regionen[code]['name'],
                           'name_fr': f['properties'].get('NAME_FREN') or regionen[code]['name']},
            'geometry': json.loads(json.dumps(mapping(g), default=float)),
        })
    ohne_flaeche = sorted(set(regionen) - {m['properties']['nuts'] for m in merkmale})
    print(f'{len(merkmale)} mit Fläche, {len(ohne_flaeche)} ohne: {ohne_flaeche[:6]}')

    def runden(x):
        if isinstance(x, float):
            return round(x, 3)
        if isinstance(x, list):
            return [runden(v) for v in x]
        if isinstance(x, dict):
            return {k: runden(v) for k, v in x.items()}
        return x

    doc = {
        'type': 'eurostat_nuts2_foreign_born',
        'schema_version': '1.0',
        'what_this_is': ('Anteil der im Ausland Geborenen an der Bevölkerung von 15 bis 64 '
                         'Jahren in Privathaushalten, je NUTS-2-Region. Gezählt wird der '
                         'Geburtsort, nicht die Staatsangehörigkeit: Eingebürgerte zählen '
                         'hier mit. Die Größe ist deshalb nicht dieselbe wie der '
                         'Ausländeranteil der übrigen Ebenen dieses Atlas.'),
        'caveat': ('Arbeitskräfteerhebung, also eine Stichprobe. Für kleine Regionen ist die '
                   'Unsicherheit entsprechend größer; Eurostat weist sie je Region nicht aus.'),
        'dataset': DATENSATZ,
        'dataset_url': f'https://ec.europa.eu/eurostat/databrowser/view/{DATENSATZ}/default/table',
        'reference_year': args.jahr,
        'source': 'Eurostat',
        'geometry_source': 'Eurostat GISCO, NUTS 2024, 1:20 Mio.',
        'licence': ('Eurostat: Weiterverwendung gestattet mit Quellenangabe '
                    '(Beschluss 2011/833/EU). GISCO-Grenzen: © EuroGeographics für die '
                    'Verwaltungsgrenzen.'),
        'count': len(merkmale),
        'features': runden(merkmale),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    args.out.with_name('eurostat-nuts2-data.js').write_text(
        'window.ATLAS_EUROSTAT=' + json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')
    reihe = sorted(regionen.values(), key=lambda r: r['foreign_born_pct'], reverse=True)
    print(f'Höchster Anteil: {reihe[0]["name"]} {reihe[0]["foreign_born_pct"]} %')
    print(f'Niedrigster    : {reihe[-1]["name"]} {reihe[-1]["foreign_born_pct"]} %')
    for code in ('DE11', 'DE12', 'DE13', 'DE14'):
        if code in regionen:
            rang = [r['nuts'] for r in reihe].index(code) + 1
            print(f'  {code} {regionen[code]["name"]:12s} '
                  f'{regionen[code]["foreign_born_pct"]:5.1f} % · Rang {rang} von {len(reihe)}')
    print(f'Datei: {args.out.stat().st_size // 1024} KiB')


if __name__ == '__main__':
    main()
