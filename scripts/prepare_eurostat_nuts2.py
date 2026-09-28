#!/usr/bin/env python3
"""Holt europäische Vergleichsgrößen auf NUTS-2-Ebene von Eurostat.

Die vier Regierungsbezirke sind NUTS-2-Regionen wie rund 270 andere in Europa. Damit
lässt sich die Frage stellen, die eine Karte von Baden-Württemberg allein nicht
beantwortet: liegt der Südwesten hoch oder niedrig, und im Vergleich womit?

Sechs Größen, aus fünf Datensätzen, alle auf derselben Gebietsebene:

  im Ausland geboren        Geburtsort, nicht Pass — Eingebürgerte zählen mit
  außerhalb der EU geboren  dieselbe Quelle, engere Abgrenzung
  ausländische Staatsang.   Pass, nicht Geburtsort — die Größe des übrigen Atlas
  Erwerbstätigenquote       Einheimische und im Ausland Geborene, und die Lücke
  Erwerbslosenquote         dieselbe Gegenüberstellung
  Wanderungssaldo           je 1.000 Einwohner, aus der Bevölkerungsfortschreibung

Warum beides, Geburtsort UND Pass: der Atlas misst sonst überall den Pass. Nur mit
lfst_r_lfsd2pwn steht daneben eine europäische Zahl, die dasselbe meint. Der
Geburtsort bleibt trotzdem dabei, weil er die andere Hälfte der Frage beantwortet —
wer eingebürgert ist, verschwindet aus der Passzahl und nicht aus der Gesellschaft.
Die beiden Werte sind nicht ineinander umrechenbar und stehen deshalb nebeneinander.

Fünf der sechs Größen stammen aus der Arbeitskräfteerhebung, also aus einer
Stichprobe. Für kleine Regionen ist die Unsicherheit entsprechend groß, und Eurostat
weist sie je Region nicht aus. Der Wanderungssaldo kommt aus der
Bevölkerungsfortschreibung und ist keine Stichprobe.

Jede Größe trägt ihr eigenes Bezugsjahr: die Datensätze werden unterschiedlich oft
und unterschiedlich schnell fortgeschrieben, und ein gemeinsames Jahr zu behaupten
hieße, für manche Größen ein falsches zu behaupten. Abgefragt wird jeweils der
zuletzt veröffentlichte Stand.

Geometrie von GISCO, 1:20 Mio., vereinfacht.
"""
from __future__ import annotations
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = 'BW-Datenatlas/1.0 (open data project; +https://github.com/CrispStrobe/bw-datenatlas)'
API = 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
GISCO = ('https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/'
         'NUTS_RG_20M_2024_4326_LEVL_2.geojson')

# Jede Abfrage legt jede Achse außer geo und time fest. Bliebe eine offen, käme ein
# Würfel zurück, aus dem sich eine Zahl nur mit einer zweiten stillen Annahme
# herausrechnen ließe — und genau solche Annahmen sind es, die später niemand mehr
# findet. Was hier steht, steht auch in der veröffentlichten Datei.
ABFRAGEN = {
    'pwc': ('lfst_r_lfsd2pwc', {'sex': 'T', 'age': 'Y15-64', 'wstatus': 'POP',
                                'unit': 'THS_PER',
                                'c_birth': ['TOTAL', 'FOR', 'NEU27_2020_FOR']}),
    'pwn': ('lfst_r_lfsd2pwn', {'sex': 'T', 'age': 'Y15-64', 'wstatus': 'POP',
                                'unit': 'THS_PER', 'citizen': ['TOTAL', 'FOR']}),
    'emp': ('lfst_r_lfe2emprc', {'sex': 'T', 'age': 'Y20-64', 'isced11': 'TOTAL',
                                 'unit': 'PC', 'c_birth': ['NAT', 'FOR']}),
    'une': ('lfst_r_lfur2gac', {'sex': 'T', 'age': 'Y15-74', 'unit': 'PC',
                                'c_birth': ['NAT', 'FOR']}),
    'mig': ('tgs00099', {'indic_de': 'CNMIGRATRT'}),
}

# Was am Ende je Region in der Datei steht. Die Reihenfolge ist die der Anzeige.
KENNZAHLEN = [
    ('foreign_born_pct', 'pwc', 'Im Ausland geboren',
     'Anteil der im Ausland Geborenen an der Bevölkerung von 15 bis 64 Jahren in '
     'Privathaushalten. Gezählt wird der Geburtsort, nicht der Pass.'),
    ('non_eu_born_pct', 'pwc', 'Außerhalb der EU geboren',
     'Anteil der außerhalb der EU-27 Geborenen an derselben Bevölkerung.'),
    ('foreign_citizen_pct', 'pwn', 'Ausländische Staatsangehörige',
     'Anteil der Personen ohne Pass des Wohnsitzlandes an der Bevölkerung von 15 bis '
     '64 Jahren in Privathaushalten. Dieselbe Abgrenzung wie im übrigen Atlas.'),
    ('employment_gap_pp', 'emp', 'Abstand der Erwerbstätigenquoten',
     'Erwerbstätigenquote der im Inland Geborenen minus die der im Ausland Geborenen, '
     'in Prozentpunkten, 20 bis 64 Jahre. Ein positiver Wert heißt: die im Ausland '
     'Geborenen sind seltener erwerbstätig.'),
    ('unemployment_foreign_born_pct', 'une', 'Erwerbslosenquote der im Ausland Geborenen',
     'Erwerbslosenquote der im Ausland Geborenen, 15 bis 74 Jahre.'),
    ('net_migration_per_1000', 'mig', 'Wanderungssaldo je 1.000 Einwohner',
     'Zuzüge minus Fortzüge einschließlich statistischer Anpassung, je 1.000 '
     'Einwohner. Aus der Bevölkerungsfortschreibung, keine Stichprobe.'),
]


def hole(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read()


def frage(code: str, filter: dict, jahr: str | None) -> dict:
    p = [('format', 'JSON')]
    for k, v in filter.items():
        for einzeln in (v if isinstance(v, list) else [v]):
            p.append((k, einzeln))
    p.append(('time', jahr) if jahr else ('lastTimePeriod', '1'))
    return json.loads(hole(API + code + '?' + urllib.parse.urlencode(p)))


def nach_geo(antwort: dict, auswahl: dict) -> tuple[str, dict]:
    """Eine Zahl je Region aus dem flachen JSON-stat-Würfel.

    Der Index ist eine einzige Zahl; die Lage eines Wertes ergibt sich aus dem
    Produkt der nachfolgenden Achsenlängen. Jede Achse außer geo muss festgelegt
    sein — hat eine Achse nur einen einzigen Wert, ist sie damit festgelegt.
    """
    dims, groessen = antwort['id'], antwort['size']
    index = {d: antwort['dimension'][d]['category']['index'] for d in dims}
    schritt, faktor = {}, 1
    for d, n in reversed(list(zip(dims, groessen))):
        schritt[d] = faktor
        faktor *= n
    basis = 0
    for d in dims:
        if d == 'geo':
            continue
        code = auswahl.get(d)
        if code is None:
            if len(index[d]) != 1:
                raise SystemExit(f'Achse {d} hat {len(index[d])} Werte und keine Auswahl')
            code = next(iter(index[d]))
        if code not in index[d]:
            raise SystemExit(f'Achse {d} kennt {code} nicht')
        basis += index[d][code] * schritt[d]
    roh = antwort['value']
    lies = ((lambda i: roh[i] if i < len(roh) else None) if isinstance(roh, list)
            else (lambda i: roh.get(str(i))))
    jahr = next(iter(antwort['dimension']['time']['category']['index']))
    return jahr, {g: lies(basis + i * schritt['geo']) for g, i in index['geo'].items()}


def echte_region(code: str) -> bool:
    """EA21 ist die Eurozone und EU27_2020 die Union — Aggregate, keine Regionen.

    Vier Zeichen allein genügt als Prüfung nicht: EA21 hat auch vier. Stünde das
    Aggregat in der Rangliste, hätte es einen Rang zwischen Regionen, und die Aussage
    "Rang 23 von 274" wäre um eine Zeile falsch.
    """
    return len(code) == 4 and code[:2] not in ('EA', 'EU')


def teile(zaehler, nenner):
    if zaehler is None or not nenner:
        return None
    return round(100 * zaehler / nenner, 1)


def differenz(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jahr', help='festes Bezugsjahr statt des zuletzt veröffentlichten')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/eurostat-nuts2.json')
    args = ap.parse_args()

    from shapely.geometry import shape, mapping

    roh, jahre = {}, {}
    for kuerzel, (code, filter) in ABFRAGEN.items():
        antwort = frage(code, filter, args.jahr)
        roh[kuerzel] = antwort
        print(f'  {code:18s} {len(antwort.get("value", {})):6d} Werte · '
              f'{(antwort.get("label") or "")[:56]}')

    def schicht(kuerzel, **auswahl):
        jahr, werte = nach_geo(roh[kuerzel], auswahl)
        jahre[kuerzel] = jahr
        return werte

    gesamt = schicht('pwc', c_birth='TOTAL')
    fremd = schicht('pwc', c_birth='FOR')
    ausser_eu = schicht('pwc', c_birth='NEU27_2020_FOR')
    gesamt_pass = schicht('pwn', citizen='TOTAL')
    fremd_pass = schicht('pwn', citizen='FOR')
    quote_nat = schicht('emp', c_birth='NAT')
    quote_for = schicht('emp', c_birth='FOR')
    erwerbslos_nat = schicht('une', c_birth='NAT')
    erwerbslos_for = schicht('une', c_birth='FOR')
    wanderung = schicht('mig')

    regionen = {}
    for code in roh['pwc']['dimension']['geo']['category']['index']:
        if not echte_region(code):
            continue
        werte = {
            'foreign_born_pct': teile(fremd.get(code), gesamt.get(code)),
            'non_eu_born_pct': teile(ausser_eu.get(code), gesamt.get(code)),
            'foreign_citizen_pct': teile(fremd_pass.get(code), gesamt_pass.get(code)),
            'employment_native_pct': quote_nat.get(code),
            'employment_foreign_born_pct': quote_for.get(code),
            'employment_gap_pp': differenz(quote_nat.get(code), quote_for.get(code)),
            'unemployment_native_pct': erwerbslos_nat.get(code),
            'unemployment_foreign_born_pct': erwerbslos_for.get(code),
            'net_migration_per_1000': wanderung.get(code),
        }
        # Eine Region ohne jede der sechs Größen ist kein Eintrag, sondern ein Loch.
        if all(werte[name] is None for name, *_ in KENNZAHLEN):
            continue
        regionen[code] = {
            'nuts': code, 'country': code[:2],
            'name': roh['pwc']['dimension']['geo']['category']['label'].get(code, code),
            'population_ths': gesamt.get(code),
            'foreign_born_ths': fremd.get(code),
            **werte,
        }
    print(f'{len(regionen)} NUTS-2-Regionen mit mindestens einer der sechs Größen')
    for name, quelle, titel, _ in KENNZAHLEN:
        da = sum(1 for r in regionen.values() if r[name] is not None)
        print(f'  {name:32s} {da:4d} Regionen · {jahre[quelle]}')

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
            # NAME_GERM, NAME_ENGL und NAME_FREN sind auf dieser Ebene die Namen des
            # STAATES, nicht der Region: DE11 trägt dort "Deutschland". Als
            # Regionsnamen eingesetzt machten sie aus Stuttgart, Karlsruhe, Freiburg
            # und Tübingen viermal "Deutschland". Der Name der Region steht in
            # NAME_LATN; die Staatennamen sind als solche brauchbar und stehen
            # deshalb daneben, damit ein Leser weiß, wo "Warszawski stołeczny" liegt.
            'properties': {**regionen[code],
                           'name_latin': f['properties'].get('NAME_LATN')
                                         or regionen[code]['name'],
                           'country_de': f['properties'].get('NAME_GERM') or code[:2],
                           'country_en': f['properties'].get('NAME_ENGL') or code[:2],
                           'country_fr': f['properties'].get('NAME_FREN') or code[:2]},
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
        'type': 'eurostat_nuts2',
        'schema_version': '2.0',
        'what_this_is': ('Sechs Vergleichsgrößen je NUTS-2-Region. Geburtsort und '
                         'Staatsangehörigkeit stehen nebeneinander und sind nicht '
                         'dasselbe: wer eingebürgert ist, zählt beim Geburtsort mit '
                         'und beim Pass nicht.'),
        'caveat': ('Fünf der sechs Größen stammen aus der Arbeitskräfteerhebung, also '
                   'aus einer Stichprobe. Für kleine Regionen ist die Unsicherheit '
                   'entsprechend größer; Eurostat weist sie je Region nicht aus. Der '
                   'Wanderungssaldo kommt aus der Bevölkerungsfortschreibung.'),
        'measures': [{'key': name, 'title': titel, 'definition': erklaerung,
                      'dataset': ABFRAGEN[quelle][0],
                      # Der amtliche Titel des Datensatzes, wie Eurostat ihn führt —
                      # nicht unsere Bezeichnung. Die Quellenangabe muss auffindbar
                      # machen, was abgerufen wurde, und dafür zählt der fremde Titel.
                      'dataset_label': roh[quelle].get('label'),
                      'dataset_url': ('https://ec.europa.eu/eurostat/databrowser/view/'
                                      + ABFRAGEN[quelle][0] + '/default/table'),
                      'reference_year': jahre[quelle],
                      'selection': ABFRAGEN[quelle][1],
                      'available_regions': sum(1 for r in regionen.values()
                                               if r[name] is not None)}
                     for name, quelle, titel, erklaerung in KENNZAHLEN],
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

    for name, quelle, titel, _ in KENNZAHLEN:
        da = [r for r in regionen.values() if r[name] is not None]
        if not da:
            continue
        reihe = sorted(da, key=lambda r: r[name], reverse=True)
        print(f'\n{titel} ({jahre[quelle]})')
        print(f'  höchster  {reihe[0]["name"][:28]:28s} {reihe[0][name]:6.1f}')
        print(f'  niedrigster {reihe[-1]["name"][:26]:26s} {reihe[-1][name]:6.1f}')
        for code in ('DE11', 'DE12', 'DE13', 'DE14'):
            if code in regionen and regionen[code][name] is not None:
                wert = regionen[code][name]
                rang = sum(1 for r in da if r[name] > wert) + 1
                print(f'  {code} {regionen[code]["name"][:12]:12s} '
                      f'{regionen[code][name]:6.1f} · Rang {rang} von {len(reihe)}')
    print(f'\nDatei: {args.out.stat().st_size // 1024} KiB')


if __name__ == '__main__':
    main()
