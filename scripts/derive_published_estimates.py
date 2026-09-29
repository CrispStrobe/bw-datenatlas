#!/usr/bin/env python3
"""Stellt die veröffentlichten Schätzungen zur muslimischen Bevölkerung Baden-Württembergs nebeneinander.

Der Atlas nennt im Kopf 1.133.000 bis 1.197.000 Personen für 2025. Das ist die
veröffentlichte Spanne des BAMF-Forschungsberichts 55. Daneben gibt es eine zweite
veröffentlichte Zahl, die das Statistische Landesamt selbst gerechnet hat: 819.000
für 2018. Beide lagen längst in den Beobachtungen dieses Projekts, aber nur eine
stand auf der Seite. Wer die andere sehen wollte, musste sie in einer Tabelle mit
über sechstausend Zeilen suchen — also sah sie niemand.

Das ist keine Kleinigkeit der Darstellung. Ein Atlas, der "veröffentlichte
Schätzungen" im Untertitel führt, muss zeigen, dass es mehrere gibt und dass sie
auseinanderliegen. Die Spanne zwischen den Verfahren ist eine Aussage über die
Unsicherheit, und sie ist größer als jede Spanne innerhalb eines Verfahrens.

Abgeleitet, nicht abgetippt: jede Zahl kommt aus research-observations.json, jede
Zeile trägt ihre Quelle, ihr Bezugsjahr und ihr Verfahren mit. Ändert sich dort
etwas, ändert sich hier alles Nötige mit.

Ausdrücklich KEINE Zeitreihe. Die Werte von 1987 bis 2025 stehen nebeneinander, weil
sie veröffentlicht wurden, nicht weil sie dasselbe messen: verschiedene Stellen,
verschiedene Verfahren, verschiedene Abgrenzungen dessen, wer als muslimisch zählt.
Eine Linie durch diese Punkte zu legen wäre eine Behauptung, die keine der Quellen
deckt.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Die Gebietskennungen, unter denen Baden-Württemberg in den Beobachtungen steht.
# Die Quellen schreiben es unterschiedlich; eine einzige Schreibweise anzunehmen
# hätte die Hälfte der Zeilen übersehen.
BW = {'08', 'DE08', 'DE1'}
KENNZAHLEN = {'muslim_persons_historical', 'estimated_muslim_persons',
              'estimated_muslim_share'}

# Wie die Quelle zu ihrer Zahl kommt — in einem Satz, aus dem hervorgeht, was die
# Zahl NICHT ist. Ohne das stünden hier fünf Zahlen, die sich zu widersprechen
# scheinen, ohne dass der Leser den Grund sehen kann.
VERFAHREN = {
    ('stala_monat_2020', 'census_republished'):
        'Volkszählung 1987: erhobene Religionszugehörigkeit, vom Landesamt zitiert.',
    ('stala_monat_2020', 'ministerial_report_republished'):
        'Zahl aus einem Bericht des Innenministeriums, vom Landesamt zitiert.',
    ('stala_monat_2020', 'main'):
        'Schätzung des Landesamts: Herkunft mal angenommener Anteil je Herkunftsland, '
        'Hauptvariante.',
    ('stala_monat_2020', 'alternative'):
        'Dieselbe Rechnung des Landesamts mit der zweiten, vorsichtigeren Annahme je '
        'Herkunftsland.',
    ('bamf_fb55', None):
        'Hochrechnung des BAMF aus der Erhebung „Muslimisches Leben in Deutschland“, '
        'auf die Länder verteilt; veröffentlicht als Spanne.',
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/published-estimates.json')
    args = ap.parse_args()

    obs = json.loads((ROOT / 'docs/data/research-observations.json')
                     .read_text(encoding='utf-8'))
    quellen = json.loads((ROOT / 'docs/data/sources.json').read_text(encoding='utf-8'))
    quellen = quellen.get('sources', quellen)

    passend = [o for o in obs
               if o.get('indicator') in KENNZAHLEN
               and (o.get('geo_id') in BW
                    or (o.get('geo_name') or '').startswith('Baden-W'))]

    # Personen und Anteil derselben Schätzung stehen als zwei Zeilen in den
    # Beobachtungen. Hier gehören sie in einen Eintrag, sonst erschiene jede
    # Schätzung zweimal.
    eintraege: dict[tuple, dict] = {}
    for o in passend:
        szenario = (o.get('dimensions') or {}).get('scenario')
        schluessel = (o['source_id'], o.get('reference_period'), szenario)
        e = eintraege.setdefault(schluessel, {
            'source_id': o['source_id'],
            'reference_year': o.get('reference_period'),
            'scenario': szenario,
            'publisher': quellen.get(o['source_id'], {}).get('publisher'),
            'source_title': quellen.get(o['source_id'], {}).get('title'),
            'source_url': quellen.get(o['source_id'], {}).get('url'),
            'published_in': quellen.get(o['source_id'], {}).get('publication_period'),
            'method': VERFAHREN.get((o['source_id'], szenario)),
            'persons': None, 'persons_low': None, 'persons_high': None,
            'share_pct': None, 'share_low': None, 'share_high': None,
        })
        if o.get('unit') == 'persons':
            e['persons'] = o.get('value')
            e['persons_low'] = o.get('value_lower')
            e['persons_high'] = o.get('value_upper')
        elif o.get('unit') == 'percent':
            e['share_pct'] = o.get('value')
            e['share_low'] = o.get('value_lower')
            e['share_high'] = o.get('value_upper')

    # Innerhalb eines Jahres zuerst die Hauptvariante: alphabetisch stünde
    # "alternative" davor, und dann läse sich die vorsichtigere Nebenrechnung wie
    # das Hauptergebnis.
    reihe = sorted(eintraege.values(),
                   key=lambda e: (str(e['reference_year']),
                                  0 if e['scenario'] in (None, 'main') else 1,
                                  e['scenario'] or ''))
    for e in reihe:
        # Eine einzige Zahl für die Balkenlänge, damit die Anzeige nicht selbst
        # entscheiden muss, was sie bei einer Spanne zeichnet.
        werte = [x for x in (e['persons'], e['persons_low'], e['persons_high'])
                 if x is not None]
        e['persons_mid'] = (sum([min(werte), max(werte)]) / 2) if werte else None

    doc = {
        'type': 'published_estimates_bw',
        'schema_version': '1.0',
        'what_this_is': ('Alle veröffentlichten Schätzungen zur Zahl der Musliminnen '
                         'und Muslime in Baden-Württemberg, die dieser Atlas belegt '
                         'führt — nebeneinander, mit Bezugsjahr, Stelle und Verfahren.'),
        'not_a_time_series': ('Die Werte stehen nebeneinander, weil sie veröffentlicht '
                              'wurden, nicht weil sie dasselbe messen. Verschiedene '
                              'Stellen, verschiedene Verfahren, verschiedene '
                              'Abgrenzungen dessen, wer als muslimisch zählt. Eine '
                              'Linie durch diese Punkte deckt keine der Quellen.'),
        'why_they_differ': ('Zwischen der jüngsten Landesschätzung und der BAMF-Spanne '
                            'liegen sieben Jahre, in denen die Zuwanderung nach '
                            'Baden-Württemberg stark war, und zwei verschiedene '
                            'Verfahren. Der Abstand ist damit keine Korrektur der '
                            'einen durch die andere.'),
        'count': len(reihe),
        'estimates': reihe,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('published-estimates-data.js').write_text(
        'window.ATLAS_PUBLISHED_ESTIMATES=' +
        json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f'{len(reihe)} veröffentlichte Schätzungen für Baden-Württemberg:')
    for e in reihe:
        p = (f"{e['persons']:,}".replace(',', '.') if e['persons']
             else f"{e['persons_low']:,}–{e['persons_high']:,}".replace(',', '.')
             if e['persons_low'] else '—')
        a = (f"{e['share_pct']} %" if e['share_pct']
             else f"{e['share_low']}–{e['share_high']} %" if e['share_low'] else '')
        print(f"  {e['reference_year']}  {(e['scenario'] or '-'):28s} "
              f"{p:>19s}  {a:>12s}  {e['source_id']}")
        if not e['method']:
            print(f"      WARNUNG: kein Verfahrenstext für "
                  f"({e['source_id']}, {e['scenario']})")


if __name__ == '__main__':
    main()
