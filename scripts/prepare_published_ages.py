#!/usr/bin/env python3
"""Veröffentlichte Altersangaben zur muslimischen Bevölkerung — und warum es keine Pyramide ist.

Die naheliegende Frage lautet: wie sieht die Alterspyramide der muslimischen
Bevölkerung aus? Die Antwort der beiden einschlägigen Quellen ist, dass es sie nicht
gibt, und das ist keine Lücke dieses Atlas, sondern eine Eigenschaft der Erhebungen.

  MLD 2020 (Pfündel/Stichs/Tanis, BAMF-Forschungsbericht 38) befragt Personen
  AB 16 JAHREN. Eine Pyramide ohne Kinder ist keine Pyramide, und gerade bei einer
  im Durchschnitt jüngeren Bevölkerung fehlt damit der breiteste Teil. Die Studie
  weist deshalb Durchschnittsalter aus, keine Altersaufbauten.

  Pew (2017) weist für Deutschland ein Medianalter aus und für Europa zwei grobe
  Anteile — unter 15 und ab 75 —, aber keinen Altersaufbau je Land.

Was beide liefern, ist trotzdem aussagekräftig, und es steht hier: die Altersangaben
nebeneinander, mit ihrer Altersuntergrenze, ihrem Gebiet und ihrem Bezugsjahr an
jeder Zahl. Wer die Zahlen vergleichen will, muss sehen, dass 39,0 (ab 16, Deutschland,
2020) und 31 (alle Alter, Deutschland, 2016) nicht dasselbe messen — das eine ist ein
Mittelwert über Erwachsene, das andere ein Median über alle.

Die einzige echte Alterspyramide des Atlas bleibt die nach Einwanderungsgeschichte
aus dem Mikrozensus: erhoben, für Baden-Württemberg, über alle Altersstufen — und
ohne jede Religionsangabe.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUELLEN = {
    'bamf_mld2020_full': {
        'title': ('Pfündel, K., Stichs, A., Tanis, K. (2021): Muslimisches Leben in '
                  'Deutschland 2020. Studie im Auftrag der Deutschen Islam Konferenz. '
                  'BAMF-Forschungsbericht 38'),
        'publisher': 'Bundesamt für Migration und Flüchtlinge',
        'url': ('https://www.bamf.de/SharedDocs/Anlagen/DE/Forschung/Forschungsberichte/'
                'fb38-muslimisches-leben.pdf'),
        'locator': 'Abbildung 3-4 und 3-5, S. 61 f.',
        'limitation': ('Befragte ab 16 Jahren, gewichtet, ungewichtete Fallzahl 5.112. '
                       'Teilgruppen unter 30 Personen weist die Studie nicht aus. '
                       'Migrationshintergrund bezieht sich ausschließlich auf muslimisch '
                       'geprägte Herkunftsländer.'),
    },
    'pew_europe_2017': {
        'title': 'Europe’s Growing Muslim Population',
        'publisher': 'Pew Research Center',
        'url': ('https://www.pewresearch.org/religion/2017/11/29/'
                'europes-growing-muslim-population/'),
        'locator': 'Abschnitt „Muslims are younger than other Europeans“',
        'limitation': ('Eigene Schätzung von Pew, keine Erhebung. Bezugsjahr 2016, '
                       'Fertilität 2015 bis 2020. Der Altersaufbau wird nur für Europa '
                       'insgesamt und nur in zwei Gruppen ausgewiesen.'),
    },
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/altersangaben-veroeffentlicht.csv')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/published-ages.json')
    args = ap.parse_args()

    zeilen = []
    with args.input.open(encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['source_id'] not in QUELLEN:
                raise SystemExit(f'Unbekannte Quelle: {r["source_id"]}')
            zeilen.append({
                'source_id': r['source_id'], 'measure': r['measure'],
                'group': r['group'], 'religion': r['religion'],
                'value': float(r['value']), 'unit': r['unit'],
                'reference_period': r['reference_period'],
                'geography': r['geography'], 'age_base': r['age_base'] or None,
                'note': r['note'] or None,
            })

    doc = {
        'type': 'published_age_measures',
        'schema_version': '1.0',
        'why_there_is_no_pyramid': (
            'Weder MLD 2020 noch Pew veröffentlichen einen Altersaufbau der muslimischen '
            'Bevölkerung. MLD 2020 befragt Personen ab 16 Jahren — eine Pyramide ohne '
            'Kinder ist keine Pyramide, und gerade bei einer im Durchschnitt jüngeren '
            'Bevölkerung fehlt damit der breiteste Teil. Pew weist je Land nur ein '
            'Medianalter aus und einen Altersaufbau nur für Europa insgesamt, in zwei '
            'Gruppen.'),
        'why_the_numbers_are_not_comparable': (
            'Ein Durchschnitt über Erwachsene und ein Median über alle Altersstufen sind '
            'zwei verschiedene Größen. Deshalb steht an jeder Zahl, welche Altersstufen '
            'sie umfasst, für welches Gebiet sie gilt und aus welchem Jahr sie stammt.'),
        'the_real_pyramid': (
            'Die einzige Alterspyramide dieses Atlas steht daneben: nach '
            'Einwanderungsgeschichte, aus dem Mikrozensus, für Baden-Württemberg, über '
            'alle Altersstufen — und ohne jede Religionsangabe.'),
        'sources': QUELLEN,
        'count': len(zeilen),
        'measures': zeilen,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('published-ages-data.js').write_text(
        'window.ATLAS_PUBLISHED_AGES=' +
        json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f'{len(zeilen)} veröffentlichte Altersangaben aus {len(QUELLEN)} Quellen')
    for kuerzel in QUELLEN:
        teil = [z for z in zeilen if z['source_id'] == kuerzel]
        groessen = sorted({z['measure'] for z in teil})
        print(f'  {kuerzel:22s} {len(teil):2d} Zeilen · {", ".join(groessen)}')
    mld = [z for z in zeilen if z['measure'] == 'mean_age']
    print('\nDurchschnittsalter (MLD 2020, ab 16 Jahren, Deutschland):')
    for z in mld:
        print(f"  {z['group'][:28]:28s} {z['religion'][:18]:18s} {z['value']:5.1f}")


if __name__ == '__main__':
    main()
