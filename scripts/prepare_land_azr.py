#!/usr/bin/env python3
"""Drei Größen aus dem Ausländerzentralregister, je Bundesland — für die Deutschlandkarte.

Die Deutschlandkarte zeigte bisher zwei geschätzte Größen und eine gezählte. Diese
drei sind ebenfalls gezählt, kommen aus demselben Register wie die Alterspyramide
und beantworten Fragen, die eine reine Anteilszahl offenlässt:

  in Deutschland geboren   Anteil der zweiten Generation an der ausländischen
                           Bevölkerung. Der übliche Einwand gegen jede Passzahl,
                           je Land beziffert.
  Durchschnittsalter       der ausländischen Bevölkerung. Aus den Mittelwerten je
                           Geschlecht, gewichtet mit den tatsächlichen Besetzungen —
                           zwei Mittelwerte ungewichtet zu mitteln wäre falsch, weil
                           Männer und Frauen unterschiedlich stark vertreten sind.
  seit 25 Jahren hier      Anteil der ausländischen Bevölkerung mit mindestens 25
                           Jahren Aufenthaltsdauer. Das Gegenstück zur gleichnamigen
                           Kreisebene, eine Ebene höher.

Zwei Länderpaare weist der BAMF-Bericht nur gemeinsam aus, und die Karte zeichnet
sie deshalb gemeinsam. Für diese Register-Größen liegen beide Länder einzeln vor;
zusammengefasst wird trotzdem, sonst zeigte dieselbe Fläche je nach Ebene ein
anderes Gebiet. Zusammengefasst wird dabei über die BESETZUNGEN und nicht über die
Anteile: der Mittelwert zweier Anteile ist nicht der Anteil der Summe.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AGS_JE_LAND = {
    'Schleswig-Holstein': 'DE01', 'Hamburg': 'DE02', 'Niedersachsen': 'DE03',
    'Bremen': 'DE04', 'Nordrhein-Westfalen': 'DE05', 'Hessen': 'DE06',
    'Rheinland-Pfalz': 'DE07', 'Baden-Württemberg': 'DE08', 'Bayern': 'DE09',
    'Saarland': 'DE10', 'Berlin': 'DE11', 'Brandenburg': 'DE12',
    'Mecklenburg-Vorpommern': 'DE13', 'Sachsen': 'DE14', 'Sachsen-Anhalt': 'DE15',
    'Thüringen': 'DE16',
}
# Wie die Deutschlandkarte ihre Flächen führt.
ZUSAMMEN = {'DE04+DE02': ['DE04', 'DE02'], 'DE12+DE13': ['DE12', 'DE13']}
LANG_ANSAESSIG = ('25 bis unter 30', '30 bis unter 35', '35 bis unter 40',
                  '40 Jahre und mehr')


def lies(pfad: Path):
    öffner = gzip.open if pfad.suffix == '.gz' else open
    with öffner(pfad, 'rt', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh, delimiter=';'))


def zahl(t):
    t = (t or '').strip().replace('.', '').replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--alter', type=Path,
                    default=ROOT / 'inputs/genesis-12521-0023-auslaender-alter-generation.csv.gz')
    ap.add_argument('--durchschnitt', type=Path,
                    default=ROOT / 'inputs/genesis-12521-0030-durchschnittsalter-laender.csv.gz')
    ap.add_argument('--dauer', type=Path,
                    default=ROOT / 'inputs/genesis-12521-0025-aufenthaltsdauer-laender.csv.gz')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/land-azr.json')
    args = ap.parse_args()

    # --- Generation und Besetzung je Land und Geschlecht ----------------------
    with gzip.open(args.alter, 'rt', encoding='utf-8-sig') as fh:
        zeilen = list(csv.reader(fh, delimiter=';'))
    kopf = next(i for i, r in enumerate(zeilen)
                if any('unter 1 Jahr' in (x or '') for x in r))
    wertspalten = [i for i, b in enumerate(zeilen[kopf]) if i >= 5 and b and i % 2 == 1]

    je_land: dict[str, dict] = {}
    for r in zeilen:
        if len(r) < 7 or r[2] != 'Insgesamt':
            continue
        code = AGS_JE_LAND.get(r[1])
        if not code:
            continue
        zweite = r[3].startswith('2.')
        sex = 'm' if r[4] == 'männlich' else 'w'
        summe = sum(int(r[i]) for i in wertspalten
                    if i < len(r) and (r[i] or '').strip().isdigit())
        e = je_land.setdefault(code, {'gen2': 0, 'gesamt': 0, 'm': 0, 'w': 0})
        e['gesamt'] += summe
        e[sex] += summe
        if zweite:
            e['gen2'] += summe

    # --- Durchschnittsalter, mit den Besetzungen gewichtet --------------------
    for r in lies(args.durchschnitt):
        if r.get('3_variable_attribute_label') != 'Insgesamt':
            continue
        code = AGS_JE_LAND.get(r.get('1_variable_attribute_label', ''))
        if not code:
            continue
        w = zahl(r.get('value'))
        if w is None:
            continue
        sex = 'm' if r.get('2_variable_attribute_label') == 'männlich' else 'w'
        je_land.setdefault(code, {}).setdefault('alter', {})[sex] = w

    # --- Aufenthaltsdauer ------------------------------------------------------
    for r in lies(args.dauer):
        if r.get('3_variable_attribute_label') != 'Insgesamt':
            continue
        code = AGS_JE_LAND.get(r.get('1_variable_attribute_label', ''))
        if not code:
            continue
        w = zahl(r.get('value'))
        if w is None:
            continue
        e = je_land.setdefault(code, {})
        bez = r.get('2_variable_attribute_label', '')
        e['dauer_gesamt'] = e.get('dauer_gesamt', 0) + w
        if any(s in bez for s in LANG_ANSAESSIG):
            e['dauer_lang'] = e.get('dauer_lang', 0) + w

    # --- Zusammenfassen wie die Karte ------------------------------------------
    def buendeln(codes):
        z = {'gen2': 0, 'gesamt': 0, 'm': 0, 'w': 0,
             'dauer_lang': 0, 'dauer_gesamt': 0, 'alter_summe': 0.0}
        for c in codes:
            e = je_land.get(c, {})
            for k in ('gen2', 'gesamt', 'm', 'w', 'dauer_lang', 'dauer_gesamt'):
                z[k] += e.get(k, 0)
            a = e.get('alter', {})
            # Der Mittelwert wird mit der Besetzung gewichtet, nicht gemittelt.
            z['alter_summe'] += a.get('m', 0) * e.get('m', 0) + a.get('w', 0) * e.get('w', 0)
        return z

    ergebnis = {}
    alle = set(je_land) | set(ZUSAMMEN)
    for code in sorted(alle):
        teile = ZUSAMMEN.get(code)
        if teile is None and any(code in v for v in ZUSAMMEN.values()):
            continue  # geht in seinem Paar auf
        z = buendeln(teile or [code])
        kopfzahl = z['m'] + z['w']
        ergebnis[code] = {
            'foreign_total': z['gesamt'],
            'second_generation_pct': (round(100 * z['gen2'] / z['gesamt'], 1)
                                      if z['gesamt'] else None),
            'mean_age_foreign': (round(z['alter_summe'] / kopfzahl, 1)
                                 if kopfzahl and z['alter_summe'] else None),
            'long_resident_pct': (round(100 * z['dauer_lang'] / z['dauer_gesamt'], 1)
                                  if z['dauer_gesamt'] else None),
        }

    doc = {
        'type': 'land_azr_measures',
        'schema_version': '1.0',
        'reference_date': '2025-12-31',
        'source': ('Statistisches Bundesamt (Destatis), GENESIS-Online, Ausländerstatistik, '
                   'Tabellen 12521-0023, 12521-0025 und 12521-0030'),
        'source_url': 'https://www-genesis.destatis.de/datenbank/online/statistic/12521',
        'licence': 'Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)',
        'measurement': 'Register, keine Stichprobe und kein Modell',
        'how_pairs_are_combined': (
            'Bremen und Hamburg sowie Brandenburg und Mecklenburg-Vorpommern liegen hier '
            'einzeln vor, werden aber zusammengefasst, damit dieselbe Fläche der Karte '
            'auf jeder Ebene dasselbe Gebiet zeigt. Zusammengefasst wird über die '
            'Besetzungen: der Mittelwert zweier Anteile ist nicht der Anteil der Summe.'),
        'count': len(ergebnis),
        'laender': ergebnis,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    print(f'{len(ergebnis)} Flächen:')
    for c, e in sorted(ergebnis.items(),
                       key=lambda x: -(x[1]['second_generation_pct'] or 0)):
        print(f"  {c:10s} 2. Gen. {e['second_generation_pct']:5.1f} % · "
              f"Alter {e['mean_age_foreign']} · seit 25 J. {e['long_resident_pct']} %")


if __name__ == '__main__':
    main()
