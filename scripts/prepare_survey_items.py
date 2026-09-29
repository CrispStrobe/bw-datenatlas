#!/usr/bin/env python3
"""„Was gefragt wurde" — Befragungsergebnisse, streng getrennt von allen Zählungen.

Dieser Atlas zählt und schätzt Menschen. Dies hier ist etwas anderes: Antworten auf
Fragen. Beides in einem Abschnitt zu zeigen wäre der schwerste Fehler, den er machen
könnte, denn eine Prozentzahl sieht wie die andere aus, und niemand sieht einem
Balken an, ob dahinter ein Register steht oder ein Fragebogen.

Deshalb ein eigener Abschnitt, eine eigene Überschrift und an jeder Zeile vier
Angaben, die bei Zählungen weniger wiegen und hier alles entscheiden:

  Grundgesamtheit   wer überhaupt gefragt wurde — 88,6 Prozent WOVON?
  Fallzahl          bei Untergruppen oft klein; 603 Befragte sind nicht 5.000
  Erhebungszeitraum nicht das Erscheinungsjahr; dazwischen liegen oft zwei Jahre
  Fundstelle        Abbildung und Seite, damit jede Zahl nachzuschlagen ist

Wo die Quelle die Fragennummern nennt, stehen auch die. Bei Einstellungsfragen hängt
das Ergebnis am Wortlaut, und wer den Wortlaut nachlesen will, muss die Frage finden
können.

Keine Karte, keine Kartenebene, keine Verrechnung mit Bevölkerungszahlen. Diese
Zahlen gehen in keine Modellrechnung dieses Atlas ein.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=ROOT / 'inputs/befragungsitems.csv')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/survey-items.json')
    args = ap.parse_args()

    bloecke: dict[str, dict] = {}
    with args.input.open(encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            b = bloecke.setdefault(r['block'], {
                'block': r['block'], 'title': r['block_title'], 'items': []})
            b['items'].append({
                'label': r['label'],
                'value': float(r['value']),
                'unit': r['unit'],
                'study': r['study'],
                'population': r['population'],
                'base_n': int(r['base_n']) if r['base_n'] else None,
                'field_period': r['field_period'],
                'question_ref': r['question_ref'] or None,
                'source_title': r['source_title'],
                'source_url': r['source_url'],
                'source_locator': r['source_locator'] or None,
            })

    doc = {
        'type': 'survey_items',
        'schema_version': '1.0',
        'what_this_is': ('Antworten auf Fragen, nicht gezählte Menschen. Ein eigener '
                         'Abschnitt, weil eine Prozentzahl wie die andere aussieht und '
                         'niemand einem Balken ansieht, ob dahinter ein Register steht '
                         'oder ein Fragebogen.'),
        'why_the_metadata_matters': (
            'Bei Befragungen entscheidet über das Ergebnis, wer gefragt wurde, wie viele '
            'es waren und wie die Frage lautete. An jeder Zeile stehen deshalb '
            'Grundgesamtheit, Fallzahl, Erhebungszeitraum und Fundstelle — und wo die '
            'Quelle sie nennt, auch die Fragennummern.'),
        'not_in_any_model': ('Diese Zahlen gehen in keine Modellrechnung dieses Atlas '
                             'ein und werden mit keiner Bevölkerungszahl verrechnet.'),
        'count': sum(len(b['items']) for b in bloecke.values()),
        'blocks': list(bloecke.values()),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('survey-items-data.js').write_text(
        'window.ATLAS_SURVEY_ITEMS=' + json.dumps(doc, ensure_ascii=False,
                                                  separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f"{doc['count']} Befragungswerte in {len(bloecke)} Blöcken:")
    for b in doc['blocks']:
        n = {i['base_n'] for i in b['items'] if i['base_n']}
        print(f"  {b['title'][:52]:52s} {len(b['items']):2d} Zeilen · "
              f"n={', '.join(str(x) for x in sorted(n)) or 'nicht angegeben'}")


if __name__ == '__main__':
    main()
