#!/usr/bin/env python3
"""Was geprüft und nicht verwendet wurde.

Ein Quellenverzeichnis sagt, worauf sich die Zahlen stützen. Es sagt nicht, was
angesehen und verworfen wurde — und gerade das ist bei einer Sammlung wie dieser
die nützlichere Auskunft. Wer nachbaut, läuft sonst dieselben Sackgassen ab: die
Studie, deren Stichprobe für die Frage zu klein ist; das Item, das eine Websuche
einer Quelle zuschreibt, in der es nicht steht; die Tabelle, die die Datenbank mit
HTTP 400 beantwortet.

Jede Zeile nennt dreierlei: was man sich davon erhofft hat, warum es nicht taugt,
und wann das geprüft wurde. Das dritte ist nicht Zierrat — eine Tabelle, die heute
mit einem Fehler antwortet, kann nächstes Jahr antworten.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path,
                    default=ROOT / 'inputs/geprueft-nicht-verwendet.csv')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/checked-not-used.json')
    args = ap.parse_args()

    with args.input.open(encoding='utf-8') as fh:
        zeilen = [dict(r) for r in csv.DictReader(fh)]
    for z in zeilen:
        for feld in ('quelle', 'warum_nicht', 'geprueft_am'):
            if not z.get(feld):
                raise SystemExit(f'{feld} fehlt bei {z.get("quelle")!r}')

    doc = {
        'type': 'checked_not_used',
        'schema_version': '1.0',
        'what_this_is': (
            'Quellen, die für diesen Atlas geprüft und nicht verwendet wurden, mit '
            'dem Grund. Ein Quellenverzeichnis sagt, worauf sich die Zahlen stützen; '
            'dies hier sagt, was angesehen und verworfen wurde.'),
        'why': (
            'Wer nachbaut, läuft sonst dieselben Sackgassen ab. Und eine Auskunft '
            'darüber, was nicht taugt, ist schwerer zu bekommen als eine über das, '
            'was taugt — sie steht nirgends, weil niemand sie aufschreibt.'),
        'dated_on_purpose': (
            'Das Prüfdatum steht dabei, weil es altert: eine Tabelle, die heute mit '
            'einem Fehler antwortet, kann nächstes Jahr antworten, und eine Studie '
            'kann einen Ergänzungsband bekommen.'),
        'count': len(zeilen),
        'entries': zeilen,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('checked-not-used-data.js').write_text(
        'window.ATLAS_CHECKED_NOT_USED=' + json.dumps(
            doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f'{len(zeilen)} geprüfte und nicht verwendete Quellen:')
    for z in zeilen:
        print(f"  {z['geprueft_am']}  {z['quelle'][:62]}")


if __name__ == '__main__':
    main()
