#!/usr/bin/env python3
"""Kirchenmitgliedschaft je Gemeinde aus dem Zensus 2022 — gezählt, nicht geschätzt.

Der Atlas trägt seit v0.11 den Namen "Religion und Migration". Damit gehört auf die
Karte, was für die Kirchen erhoben ist und für den Islam nicht: eine Vollerhebung
je Gemeinde. Der Zensus 2022 hat die Zugehörigkeit zu einer Religionsgesellschaft
des öffentlichen Rechts erfasst, und das sind in Baden-Württemberg die römisch-
katholische und die evangelische Kirche. Mehr nicht — der Islam ist keine eigene
Kategorie, und wer ihm angehört, steht in der Restkategorie.

Genau deshalb steht diese Ebene neben der Modellrechnung und nicht anstelle von ihr.
Sie zeigt drei Dinge, die der Atlas bisher nicht zeigte:

  katholisch      die konfessionelle Geografie des Landes, die ausgeprägteste
                  religiöse Struktur, die Baden-Württemberg überhaupt hat
  evangelisch     ihr Gegenstück
  keine der beiden  die Restkategorie — und damit sichtbar die Obergrenze, gegen
                  die das Muslim-Modell bisher nur rechnerisch geprüft wurde

Die dritte Ebene ist die heikelste und trägt deshalb den längsten Hinweis. Sie ist
KEIN Anteil von Konfessionslosen und erst recht kein Muslimanteil: sie enthält
Konfessionslose, alle anderen Religionen und alle fehlenden Angaben in einer Zahl.
Ihr Wert für diesen Atlas liegt darin, dass der modellierte Muslimanteil nicht über
ihr liegen kann.

Gezählt, nicht geschätzt — mit einer Einschränkung, die zum Zensus gehört: die
Einzelwerte sind nach dem Cell-Key-Verfahren geheimgehalten, also bewusst leicht
überlagert. Für eine Gemeindekarte ist das unerheblich, für den Einzelwert einer
kleinen Gemeinde nicht.
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
                    default=ROOT / 'inputs/zensus2022-religion-gemeinden-bw.csv')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/municipal-religion-2022.json')
    args = ap.parse_args()

    bound = json.loads((ROOT / 'docs/data/municipal-religion-bound.json')
                       .read_text(encoding='utf-8'))
    crosswalk = {c['geo_id']: c['ags'] for c in json.loads(
        (ROOT / 'docs/data/municipality-ags-crosswalk.json').read_text(encoding='utf-8'))}

    zensus = {}
    with args.input.open(encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            zahl = lambda k: int(r[k]) if r[k] not in ('', '-', '.') else None
            zensus[r['ags']] = {
                'ags': r['ags'], 'name': r['name'],
                'population': zahl('population'),
                'catholic': zahl('catholic'),
                'evangelical': zahl('evangelical'),
                'other_none_unstated': zahl('other_none_unstated'),
            }

    def anteil(teil, ganz):
        if teil is None or not ganz:
            return None
        return round(100 * teil / ganz, 2)

    gemeinden, ohne = {}, []
    for geo_id, ags in crosswalk.items():
        z = zensus.get(ags)
        if not z:
            ohne.append(geo_id)
            continue
        beide = None
        if z['catholic'] is not None and z['evangelical'] is not None:
            beide = z['catholic'] + z['evangelical']
        gemeinden[geo_id] = {
            'ags': ags, 'name': z['name'], 'population': z['population'],
            'catholic': z['catholic'], 'evangelical': z['evangelical'],
            'other_none_unstated': z['other_none_unstated'],
            'catholic_pct': anteil(z['catholic'], z['population']),
            'evangelical_pct': anteil(z['evangelical'], z['population']),
            'both_churches_pct': anteil(beide, z['population']),
            'other_none_unstated_pct': anteil(z['other_none_unstated'], z['population']),
        }
    print(f'{len(gemeinden)} Gemeinden verknüpft, {len(ohne)} ohne Zensuszeile')

    summe = lambda k: sum(g[k] for g in gemeinden.values() if g[k] is not None)
    land = {
        'population': summe('population'),
        'catholic': summe('catholic'),
        'evangelical': summe('evangelical'),
        'other_none_unstated': summe('other_none_unstated'),
    }
    for name, feld in (('catholic_pct', 'catholic'), ('evangelical_pct', 'evangelical'),
                       ('other_none_unstated_pct', 'other_none_unstated')):
        land[name] = anteil(land[feld], land['population'])
    land['both_churches_pct'] = anteil(land['catholic'] + land['evangelical'],
                                       land['population'])

    doc = {
        'type': 'municipal_religion_census_2022',
        'schema_version': '1.0',
        'what_this_is': ('Zugehörigkeit zu einer Religionsgesellschaft des öffentlichen '
                         'Rechts je Gemeinde, Zensus 2022. Erfasst sind nur die '
                         'römisch-katholische und die evangelische Kirche; alles andere '
                         'steht in einer einzigen Restkategorie.'),
        'counted_not_estimated': ('Eine Vollerhebung, keine Modellrechnung — anders als '
                                  'die muslimische Bevölkerung, für die es auf '
                                  'Gemeindeebene keine Erhebung gibt.'),
        'the_residual_is_not_a_muslim_share': (
            'Die Restkategorie "Sonstige, keine, ohne Angabe" umfasst Konfessionslose, '
            'alle anderen Religionen und alle fehlenden Angaben in einer Zahl. Sie ist '
            'weder ein Anteil Konfessionsloser noch ein Muslimanteil. Ihr Wert für '
            'diesen Atlas: der modellierte Muslimanteil einer Gemeinde kann nicht über '
            'ihr liegen.'),
        'secrecy': ('Einzelwerte sind nach dem Cell-Key-Verfahren geheimgehalten, also '
                    'bewusst leicht überlagert. Für die Karte unerheblich, für den '
                    'Einzelwert einer kleinen Gemeinde nicht.'),
        'reference_period': bound.get('reference_period'),
        'source': bound.get('source'),
        'source_url': bound.get('source_url'),
        'attribution': bound.get('attribution'),
        'state_total': land,
        'count': len(gemeinden),
        'municipalities': gemeinden,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    args.out.with_name('municipal-religion-data.js').write_text(
        'window.ATLAS_MUNI_RELIGION=' +
        json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f"Land: katholisch {land['catholic_pct']} %, evangelisch "
          f"{land['evangelical_pct']} %, beide zusammen {land['both_churches_pct']} %, "
          f"Restkategorie {land['other_none_unstated_pct']} %")
    for feld, titel in (('catholic_pct', 'katholisch'), ('evangelical_pct', 'evangelisch'),
                        ('other_none_unstated_pct', 'Restkategorie')):
        reihe = sorted((g for g in gemeinden.values() if g[feld] is not None),
                       key=lambda g: g[feld], reverse=True)
        print(f'  {titel:14s} höchster {reihe[0]["name"][:24]:24s} {reihe[0][feld]:5.1f} % '
              f'· niedrigster {reihe[-1]["name"][:22]:22s} {reihe[-1][feld]:5.1f} %')
    print(f'Datei: {args.out.stat().st_size // 1024} KiB')


if __name__ == '__main__':
    main()
