#!/usr/bin/env python3
"""Foreign population by district from the Ausländerzentralregister, via Destatis.

This is the data behind the Federal Statistical Office's interactive map "Migration,
Integration, Regionen". It is published as one CSV for all 401 German districts, and it
carries three things the atlas could not get anywhere else:

  Origin groups per district, not just per state — EU-27, the states that joined from
  2004, non-EU, and the former Gastarbeiter recruitment countries, plus Türkei, Ukraine,
  Syrien, Rumänien and Polen named individually.

  Residence status per district — Aufenthaltsgestattung and Duldung. A survey of the
  state's own publications concluded that asylum figures below state level were not
  available; they are, from the federal register, and they were in a file linked from a
  map.

  Length of residence per district, which the atlas otherwise has only as a state
  average.

Reference date 31 December 2025, which is a year newer than the state report the atlas
uses for nationality by district.

BADEN-WÜRTTEMBERG AND THE REST. All 401 districts are read, but only the 44 of
Baden-Württemberg are published. The others are kept as distribution only — the national
minimum, median and maximum per indicator — so that a district's value can be placed
against Germany without this atlas turning into a national one.

WHAT A SHARE HERE MEANS. Every ANT_ column is a share of the foreign population of that
district, not of its inhabitants. A district where 60 % of foreigners are non-EU citizens
is not a district that is 60 % non-EU. Confusing the two would be the easiest possible
misreading of this file, so the denominator travels with every value.

Licence: © Statistisches Bundesamt (Destatis); reproduction and distribution, including
in part, permitted with source attribution.
"""
from __future__ import annotations
import csv
import io
import json
import statistics
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'inputs/destatis-migration-integration-regionen.zip'
OUTPUT = ROOT / 'docs/data/district-azr-2025.json'
SOURCE_PAGE = 'https://service.destatis.de/DE/karten/migration_integration_regionen.html'
SOURCE_DATA = 'https://service.destatis.de/DE/karten/data/migration_integration_regionen.zip'

# Column -> (published name, what it is). Only what this atlas can explain is taken;
# the file has about 150 columns and most of them belong to a different question.
COUNTS = {
    'AZR_INSG': ('foreign_total', 'Ausländer insgesamt'),
    'AZR_GASTARB': ('recruitment_states', 'aus den Gastarbeiter-Anwerbestaaten'),
    'AZR_EU27_AUSL': ('eu27', 'EU-Staaten'),
    'AZR_OST2004': ('eu_since_2004', 'EU-Staaten, die seit 2004 beigetreten sind'),
    'AZR_NICHTEU_AUSL': ('non_eu', 'Nicht-EU-Staaten'),
    'AZR_TUERKEI': ('turkey', 'Türkei'),
    'AZR_UKRAINE': ('ukraine', 'Ukraine'),
    'AZR_SYRIEN': ('syria', 'Syrien'),
    'AZR_RUMAENIEN': ('romania', 'Rumänien'),
    'AZR_POLEN': ('poland', 'Polen'),
    'AZR_GESTATT': ('permission_pending', 'mit Aufenthaltsgestattung'),
    'AZR_DULD': ('tolerated', 'mit Duldung'),
    'AZR_AD25UM': ('resident_25_years_or_more', 'seit 25 Jahren oder länger hier'),
}
SHARES = {'AZR_ANT_' + key.removeprefix('AZR_'): name
          for key, (name, _) in COUNTS.items() if key != 'AZR_INSG'}


def number(value: str) -> float | None:
    """This file is English-formatted: comma-separated, period decimals.

    German statistical files usually write 18,2 and use the period for thousands, and
    treating this one the same way turned every share into ten or a hundred times
    itself — a Turkish share of "182 %" for Heilbronn. The period here is a decimal
    point and nothing else.
    """
    value = (value or '').strip()
    try:
        return float(value)
    except ValueError:
        return None


def main() -> None:
    with zipfile.ZipFile(ARCHIVE) as archive:
        name = next(n for n in archive.namelist() if n.endswith('_daten.csv'))
        text = archive.read(name).decode('utf-8-sig')
    rows = list(csv.DictReader(io.StringIO(text)))
    # A share of a population cannot exceed 100. This is the check that would have
    # caught the decimal-separator error immediately instead of after it was published.
    if len(rows) < 390:
        raise SystemExit(f'{len(rows)} Kreise gelesen, erwartet sind rund 400')

    def record(row: dict) -> dict:
        out = {'id': row['RS'], 'name': row['NAME'].strip('"')}
        for column, (field, _) in COUNTS.items():
            out[field] = number(row.get(column, ''))
        for column, field in SHARES.items():
            out[field + '_share_of_foreign'] = number(row.get(column, ''))
        return out

    everyone = [record(r) for r in rows]
    bw = [r for r in everyone if r['id'].startswith('08')]
    if len(bw) != 44:
        raise SystemExit(f'{len(bw)} Kreise in Baden-Württemberg gelesen, erwartet sind 44')

    # The rest of Germany is kept only as a distribution, so a BW value can be placed
    # against the country without publishing a national dataset here.
    for row in bw:
        for field, value in row.items():
            if field.endswith('_share_of_foreign') and value is not None and not 0 <= value <= 100:
                raise SystemExit(f'{row["name"]}: {field} = {value}, '
                                 'ein Anteil kann nicht außerhalb von 0 bis 100 liegen')

    national = {}
    for field in [f + '_share_of_foreign' for f in SHARES.values()]:
        values = sorted(v for v in (r[field] for r in everyone) if v is not None)
        if values:
            national[field] = {'min': values[0], 'median': statistics.median(values),
                               'max': values[-1], 'districts': len(values)}

    doc = {
        'type': 'district_foreign_population_azr',
        'schema_version': '1.0',
        'reference_date': '2025-12-31',
        'source': ('Statistisches Bundesamt (Destatis), interaktive Karte „Migration, '
                   'Integration, Regionen“; Daten aus dem Ausländerzentralregister (AZR)'),
        'source_page': SOURCE_PAGE,
        'source_data': SOURCE_DATA,
        'licence': ('© Statistisches Bundesamt (Destatis); Vervielfältigung und '
                    'Verbreitung, auch auszugsweise, mit Quellenangabe gestattet'),
        'what_a_share_means': (
            'Jeder Anteil bezieht sich auf die ausländische Bevölkerung des Kreises, '
            'nicht auf seine Einwohner. Ein Kreis, in dem 60 Prozent der Ausländer aus '
            'Nicht-EU-Staaten kommen, ist kein Kreis, der zu 60 Prozent aus Nicht-EU-'
            'Ausländern besteht.'),
        'not_a_religion_measure': (
            'Staatsangehörigkeit ist keine Religionszugehörigkeit. Eingebürgerte und '
            'hier geborene Nachkommen haben einen deutschen Pass und stehen in keiner '
            'dieser Zahlen. Diese Datei geht in keine Modellrechnung dieses Atlas ein.'),
        'labels': {name: text for _, (name, text) in COUNTS.items()},
        'districts': sorted(bw, key=lambda r: r['name']),
        'germany_distribution': national,
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    OUTPUT.with_name('district-azr-data.js').write_text(
        'window.ATLAS_DISTRICT_AZR=' + json.dumps(doc, ensure_ascii=False,
                                                  separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f'{len(bw)} Kreise in Baden-Württemberg von {len(everyone)} deutschen Kreisen, '
          f'{len(SHARES)} Anteilskennzahlen je Kreis')


if __name__ == '__main__':
    main()
