#!/usr/bin/env python3
"""Islamischer Religionsunterricht in Baden-Württemberg: die Reihe seit 2019.

Die Stiftung Sunnitischer Schulrat, die den Unterricht in Baden-Württemberg
inhaltlich verantwortet, veröffentlicht die Teilnehmerzahlen und nennt als Quelle
die amtliche Schulstatistik des Statistischen Landesamts. Das ist die Primärquelle
für die Zahl, die sonst nur über Presseabfragen zu bekommen ist.

Und sie lässt sich prüfen. Die Kultusministerkonferenz veröffentlicht zweijährlich
dieselbe Größe, getrennt nach Primar- und Sekundarbereich I einerseits und
Sekundarbereich II andererseits. Zählt man beide zusammen, ergibt sich für die
überlappenden Jahre genau die Zahl der Stiftung:

    2021/22   KMK 6.459 + 35 = 6.494     Stiftung 6.494
    2023/24   KMK 9.750 + 310 = 10.060   Stiftung 10.060

Damit ist zweierlei belegt. Erstens stimmen die beiden unabhängigen
Veröffentlichungen überein. Zweitens — und das ist der praktische Gewinn — ist
klar, was die verbreitete KMK-Zahl NICHT enthält: die Sekundarstufe II. Wer 9.750
und 11.827 nebeneinanderlegt, vergleicht zwei verschiedene Abgrenzungen und zwei
verschiedene Schuljahre.

Der Punkt 2019 stimmt nicht überein: die Stiftung nennt 5.500 ohne
Schuljahresbezeichnung, die KMK für 2019/20 zusammen 5.905. Das steht so in der
Datei, statt geglättet zu werden.

Der Aufbau prüft die beiden Übereinstimmungen und bricht ab, wenn sie nicht mehr
stimmen — dann hat eine der beiden Quellen ihre Zahlen geändert.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=ROOT / 'inputs/iru-bw-zeitreihe.csv')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/iru-bw-timeseries.json')
    args = ap.parse_args()

    punkte, geprueft = [], 0
    with args.input.open(encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            zahl = lambda k: int(r[k]) if r[k] else None
            p = {'school_year': r['school_year'], 'pupils': zahl('pupils'),
                 'kmk_primar_sek1': zahl('kmk_primar_sek1'),
                 'kmk_sek2': zahl('kmk_sek2'), 'note': r['note'] or None}
            if p['kmk_primar_sek1'] is not None:
                summe = p['kmk_primar_sek1'] + (p['kmk_sek2'] or 0)
                p['kmk_total'] = summe
                p['matches_kmk'] = summe == p['pupils']
                if not p['matches_kmk']:
                    raise SystemExit(
                        f"{p['school_year']}: KMK-Summe {summe} weicht von der Angabe "
                        f"der Stiftung ({p['pupils']}) ab — eine Quelle hat sich geändert")
                geprueft += 1
            punkte.append(p)

    erst, letzt = punkte[0], punkte[-1]
    doc = {
        'type': 'iru_bw_timeseries',
        'schema_version': '1.0',
        'what_this_is': ('Teilnehmerinnen und Teilnehmer am islamischen '
                         'Religionsunterricht in Baden-Württemberg, alle Schularten '
                         'einschließlich Sekundarstufe II.'),
        'source': ('Stiftung Sunnitischer Schulrat nach der amtlichen Schulstatistik '
                   'des Statistischen Landesamts Baden-Württemberg'),
        'source_url': 'https://sunnitischer-schulrat.de/',
        'cross_check': ('Für 2021/22 und 2023/24 unabhängig bestätigt: die Summe aus '
                        'Primar- und Sekundarbereich I und dem nachrichtlich '
                        'ausgewiesenen Sekundarbereich II der '
                        'KMK-Auswertung Religionsunterricht ergibt genau dieselbe Zahl.'),
        'what_the_kmk_headline_omits': ('Die verbreitete KMK-Zahl — für 2023/24 9.750 — '
                                        'enthält den Sekundarbereich II nicht. Der '
                                        'Unterschied zu 10.060 ist genau dieser Bereich.'),
        'caveat': ('Der Punkt 2019 stimmt zwischen den beiden Quellen nicht überein: '
                   '5.500 bei der Stiftung ohne Schuljahresbezeichnung, 5.905 bei der '
                   'KMK für 2019/20.'),
        'schools_with_offer': 157,
        'religion_groups': 720,
        'growth_since_2019_percent': round(100 * (letzt['pupils'] / erst['pupils'] - 1)),
        'count': len(punkte),
        'points': punkte,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('iru-bw-timeseries-data.js').write_text(
        'window.ATLAS_IRU_BW=' + json.dumps(doc, ensure_ascii=False,
                                            separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(punkte)} Punkte, {geprueft} davon gegen die KMK geprüft und bestätigt')
    for p in punkte:
        marke = f"  == KMK {p['kmk_total']}" if p.get('kmk_total') else ''
        print(f"  {p['school_year']:8s} {p['pupils']:6d}{marke}")
    print(f"Wachstum seit 2019: +{doc['growth_since_2019_percent']} %")


if __name__ == '__main__':
    main()
