#!/usr/bin/env python3
"""Was die beiden Kirchen zwischen 2011 und 2022 verloren haben, Gemeinde für Gemeinde.

Der Zensus 2022 und der Zensus 2011 sind beide Zählungen derselben Sache: der
eingetragenen Zugehörigkeit zu einer Religionsgesellschaft des öffentlichen Rechts.
Die Statistischen Ämter haben sie in einer Veröffentlichung nebeneinandergestellt,
beide Blätter mit denselben 1.101 baden-württembergischen Gemeindeschlüsseln — die
Ergebnisse von 2011 sind also auf den Gebietsstand von 2022 gebracht. Damit ist der
Unterschied zwischen zwei Zählungen lesbar und nicht nur der Unterschied zwischen
zwei Gebietseinteilungen.

Was die Karte zeigt und was nicht:

  Sie zeigt die Veränderung des Anteils in Prozentpunkten. Ein Wert von -8 heißt:
      von hundert Einwohnern gehören acht weniger dieser Kirche an als 2011.
  Sie zeigt nicht, warum. In der Zahl stecken Kirchenaustritte, Sterbefälle einer
      älteren Mitgliedschaft und Zuzug von Menschen, die nie Mitglied waren. Der
      Zensus trennt das nicht, und diese Auswertung tut es auch nicht.
  Sie ist eine eigenständige Berechnung. Die Statistischen Ämter verlangen diese
      Kennzeichnung ausdrücklich für Kennzahlen, die aus ihren geheimgehaltenen
      Ergebnissen weitergerechnet werden — beide Jahre sind nach dem Cell-Key-
      Verfahren überlagert, und eine Differenz zweier überlagerter Werte trägt die
      Unschärfe beider. Für kleine Gemeinden ist sie deshalb gröber, als die
      Nachkommastelle aussehen lässt.
"""
from __future__ import annotations
import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUELLE = ('https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/'
          'Zensus2022/Publikationen/Downloads-Publikationen/Sonderauswertungen/'
          'religionszugehoerigkeit_zenus2022_und_zensus2011_bundesland.xlsx')
UA = {'User-Agent': 'BW-Datenatlas/1.0'}
# Spalten beider Blätter: AGS, Name, Regionalebene, Einwohner, katholisch, Anteil,
# evangelisch, Anteil, Rest, Anteil.
SPALTE = {'population': 3, 'catholic': 4, 'evangelical': 6, 'other_none_unstated': 8}


def zahl(x) -> int | None:
    """Die Zahl einer Zelle. Im Blatt von 2011 stehen einige als Text."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x)
    x = str(x).strip().replace('.', '').replace(' ', '')
    return int(x) if x.isdigit() else None


# Die Länder stehen in dieser Veröffentlichung nicht als eigene Zeilen; nur Bund und
# Gemeinden. Die Landeswerte werden deshalb aus den Gemeinden aufsummiert. Zwei Paare
# sind in der Bundesländerkarte dieses Atlas zusammengefasst, weil die dortige
# Muslimquelle sie zusammenfasst — hier wird über Zahlen gebündelt, nicht über Anteile.
ZUSAMMEN = {'DE04+DE02': ['04', '02'], 'DE12+DE13': ['12', '13']}
LAND_ZU_DE = {'01': 'DE01', '03': 'DE03', '05': 'DE05', '06': 'DE06', '07': 'DE07',
              '08': 'DE08', '09': 'DE09', '10': 'DE10', '11': 'DE11', '14': 'DE14',
              '15': 'DE15', '16': 'DE16'}


def lies(blatt, land: str | None = '08') -> dict[str, dict]:
    out = {}
    for r in blatt.iter_rows(min_row=6, values_only=True):
        if not r[0] or r[2] != 'Gemeinde':
            continue
        if land and not str(r[0]).startswith(land):
            continue
        werte = {k: zahl(r[i]) for k, i in SPALTE.items()}
        if None in werte.values() or not werte['population']:
            continue
        out[str(r[0])] = {'name': r[1], **werte}
    return out


def ags(ars: str) -> str:
    """Der achtstellige Gemeindeschlüssel aus dem zwölfstelligen Regionalschlüssel.

    Die Statistischen Ämter schlüsseln hier mit dem Regionalschlüssel, der den
    Gemeindeverband mitführt (081155003010); die Geometriezuordnung dieses Atlas
    nutzt den amtlichen Gemeindeschlüssel (08115010). Land, Regierungsbezirk und
    Kreis stehen vorn, die Gemeinde hinten, der Verband dazwischen fällt weg.
    """
    if len(ars) != 12:
        raise SystemExit(f'Regionalschlüssel {ars!r} hat nicht zwölf Stellen')
    return ars[:5] + ars[-3:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--xlsx', type=Path,
                    default=ROOT / 'inputs/zensus-religion-2011-2022.xlsx')
    ap.add_argument('--laden', action='store_true')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/religion-change-2011-2022.json')
    args = ap.parse_args()

    if args.laden or not args.xlsx.is_file():
        args.xlsx.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(QUELLE + '?__blob=publicationFile&v=3',
                                     headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            args.xlsx.write_bytes(r.read())

    import openpyxl
    w = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=True)
    a = lies(w['Religion_Zensus2022'])
    b = lies(w['Religion_Zensus2011'])
    gemeinsam = sorted(set(a) & set(b))
    if len(gemeinsam) != 1101:
        raise SystemExit(f'{len(gemeinsam)} Gemeinden in beiden Jahren, erwartet 1101 '
                         f'— der Gebietsstand stimmt nicht mehr überein')

    reihen = []
    for schluessel in gemeinsam:
        n, v = a[schluessel], b[schluessel]
        zeile = {'ags': ags(schluessel), 'regional_key': schluessel,
                 'name': n['name'],
                 'population_2011': v['population'], 'population_2022': n['population']}
        for feld in ('catholic', 'evangelical', 'other_none_unstated'):
            alt = 100 * v[feld] / v['population']
            neu = 100 * n[feld] / n['population']
            zeile[feld + '_pct_2011'] = round(alt, 1)
            zeile[feld + '_pct_2022'] = round(neu, 1)
            zeile[feld + '_change'] = round(neu - alt, 1)
        beide_alt = 100 * (v['catholic'] + v['evangelical']) / v['population']
        beide_neu = 100 * (n['catholic'] + n['evangelical']) / n['population']
        zeile['both_churches_pct_2011'] = round(beide_alt, 1)
        zeile['both_churches_pct_2022'] = round(beide_neu, 1)
        zeile['both_churches_change'] = round(beide_neu - beide_alt, 1)
        reihen.append(zeile)

    def land(jahr, felder):
        quelle = b if jahr == 2011 else a
        summe = sum(quelle[x]['population'] for x in gemeinsam)
        teil = sum(sum(quelle[x][f] for f in felder) for x in gemeinsam)
        return round(100 * teil / summe, 1)

    # Dieselbe Rechnung für die Länder, damit der Landeswert einen Vergleich hat.
    alle22 = lies(w['Religion_Zensus2022'], None)
    alle11 = lies(w['Religion_Zensus2011'], None)
    zusammen = set(alle22) & set(alle11)
    bundeslaender = []
    for kennung, praefixe in list(ZUSAMMEN.items()) + [
            (v, [k]) for k, v in sorted(LAND_ZU_DE.items())]:
        teil = [x for x in zusammen if x[:2] in praefixe]
        if not teil:
            continue
        eintrag = {'id': kennung}
        for jahr, quelle in ((2011, alle11), (2022, alle22)):
            summe = sum(quelle[x]['population'] for x in teil)
            kirchen = sum(quelle[x]['catholic'] + quelle[x]['evangelical']
                          for x in teil)
            eintrag[f'both_churches_pct_{jahr}'] = round(100 * kirchen / summe, 1)
            eintrag[f'population_{jahr}'] = summe
        eintrag['both_churches_change'] = round(
            eintrag['both_churches_pct_2022'] - eintrag['both_churches_pct_2011'], 1)
        bundeslaender.append(eintrag)
    bundeslaender.sort(key=lambda z: z['both_churches_change'])

    doc = {
        'type': 'religion_change_2011_2022',
        'schema_version': '1.0',
        'what_this_is': (
            'Veränderung der Zugehörigkeit zu den beiden großen Kirchen zwischen dem '
            'Zensus 2011 und dem Zensus 2022, in Prozentpunkten je Gemeinde. Beide '
            'Zählungen stehen in derselben Veröffentlichung der Statistischen Ämter '
            'und tragen dieselben 1.101 Gemeindeschlüssel; die Ergebnisse von 2011 '
            'sind also auf den Gebietsstand von 2022 gebracht.'),
        'own_calculation': (
            'Eigenständige Berechnung. Die Statistischen Ämter verlangen diese '
            'Kennzeichnung für Kennzahlen, die aus ihren geheimgehaltenen Ergebnissen '
            'weitergerechnet werden. Beide Jahre sind nach dem Cell-Key-Verfahren '
            'überlagert, und die Differenz zweier überlagerter Werte trägt die '
            'Unschärfe beider — für kleine Gemeinden ist sie gröber, als die '
            'Nachkommastelle aussehen lässt.'),
        'what_it_does_not_say': (
            'Warum der Anteil gefallen ist, sagt die Zahl nicht. Darin stecken '
            'Kirchenaustritte, Sterbefälle einer im Schnitt älteren Mitgliedschaft und '
            'der Zuzug von Menschen, die nie Mitglied waren. Der Zensus trennt das '
            'nicht, und diese Auswertung tut es auch nicht.'),
        'reference_periods': ['2011-05-09', '2022-05-15'],
        'source': ('Statistische Ämter des Bundes und der Länder, Bevölkerung nach '
                   'Religionszugehörigkeit im Zensus 2022 und im Zensus 2011'),
        'source_url': QUELLE,
        'attribution': '© Statistische Ämter des Bundes und der Länder, 2024',
        'state_total': {
            'catholic_pct_2011': land(2011, ['catholic']),
            'catholic_pct_2022': land(2022, ['catholic']),
            'evangelical_pct_2011': land(2011, ['evangelical']),
            'evangelical_pct_2022': land(2022, ['evangelical']),
            'both_churches_pct_2011': land(2011, ['catholic', 'evangelical']),
            'both_churches_pct_2022': land(2022, ['catholic', 'evangelical']),
        },
        'count': len(reihen),
        # Geschlüsselt nach dem amtlichen Gemeindeschlüssel, weil die Karte damit
        # zuordnet; der Regionalschlüssel der Quelle steht an jeder Zeile.
        'municipalities': {z['ags']: z for z in reihen},
        'germany': {z['id']: z for z in bundeslaender},
        'germany_note': ('Die Länderwerte sind Summen ihrer Gemeinden; die Veröffentlichung '
                         'weist keine Länderzeilen aus. Bremen und Hamburg sowie '
                         'Brandenburg und Mecklenburg-Vorpommern sind zusammengefasst, '
                         'weil die Bundesländerkarte dieses Atlas sie zusammenfasst — '
                         'gebündelt wird über Zahlen, nicht über Anteile.'),
    }
    doc['state_total']['both_churches_change'] = round(
        doc['state_total']['both_churches_pct_2022']
        - doc['state_total']['both_churches_pct_2011'], 1)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('religion-change-data.js').write_text(
        'window.ATLAS_RELIGION_CHANGE=' + json.dumps(
            doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')

    st = doc['state_total']
    print(f"{len(reihen)} Gemeinden in beiden Zählungen.")
    print(f"  katholisch  {st['catholic_pct_2011']} % -> {st['catholic_pct_2022']} %")
    print(f"  evangelisch {st['evangelical_pct_2011']} % -> "
          f"{st['evangelical_pct_2022']} %")
    print(f"  beide       {st['both_churches_pct_2011']} % -> "
          f"{st['both_churches_pct_2022']} % ({st['both_churches_change']} Punkte)")
    print('  Länder (beide Kirchen, Punkte): '
          + ', '.join(f"{z['id']} {z['both_churches_change']}"
                      for z in bundeslaender[:4] + bundeslaender[-2:]))
    stark = sorted(reihen, key=lambda z: z['both_churches_change'])[:3]
    schwach = sorted(reihen, key=lambda z: z['both_churches_change'])[-3:]
    print('  stärkster Rückgang: '
          + ', '.join(f"{z['name']} {z['both_churches_change']}" for z in stark))
    print('  geringster:         '
          + ', '.join(f"{z['name']} {z['both_churches_change']}" for z in schwach))


if __name__ == '__main__':
    main()
