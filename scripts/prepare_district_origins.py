#!/usr/bin/env python3
"""Extract foreign population by nationality per BW district from the official report.

Source: Statistisches Landesamt Baden-Württemberg, Statistischer Bericht A I 4 - j/24,
"Ausländische Bevölkerung in Baden-Württemberg am 31. Dezember 2024", Table 4.
Terms of the report: "Vervielfältigung und Verbreitung, auch auszugsweise, mit
Quellenangabe gestattet."

Table 4 is printed across two facing pages. The left half starts each row with the
district name followed by seven values; the right half prints seven values and ends
with the district name. Both halves are joined on the district name, never by row
order, and every district must appear in both halves or the run fails.

This reads citizenship (Ausländerzentralregister), which is NOT the same as origin or
migration background: naturalised residents hold German passports and are absent here.
That limitation is carried into the output and must stay visible downstream.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://www.statistik-bw.de/fileadmin/user_upload/Service/Veroeff/Statistische_Berichte/312424001.pdf'
REPORT = 'Statistisches Landesamt Baden-Württemberg, Statistischer Bericht A I 4 - j/24'
REFERENCE_DATE = '2024-12-31'

# Table 4 is printed as four blocks of seven value columns. Blocks 1 and 3 put the
# district name first, blocks 2 and 4 put it last. Order below is the printed order.
BLOCK_NAME_FIRST = [
    ['foreign_total', 'europe', 'eu_states', 'turkey', 'italy', 'romania', 'croatia'],
    ['serbia', 'russia', 'iraq', 'france', 'portugal', 'austria', 'spain'],
]
BLOCK_NAME_LAST = [
    ['poland', 'syria', 'greece', 'kosovo', 'hungary', 'bulgaria', 'bosnia_herzegovina'],
    ['india', 'afghanistan', 'china', 'north_macedonia', 'usa', 'ukraine', 'nigeria'],
]
ALL_COLUMNS = [c for b in BLOCK_NAME_FIRST + BLOCK_NAME_LAST for c in b]

# Aggregate rows printed between the districts; they are totals, not areas.
AGGREGATE = re.compile(r'^(Region\b|Regierungsbezirk\b|Baden-Württemberg)')
# Section headings. "Heilbronn" and "Karlsruhe" each exist as both an urban and a rural
# district, so the heading above a row is what tells them apart.
HEADING = re.compile(r'^(Stadtkreise?|Landkreise?)$')


def norm(s: str) -> str:
    s = s.split(',')[0].casefold().replace('ß', 'ss')
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s)


def number(token: str):
    """German thousands separators; '–' and '.' mark a value the source does not give."""
    token = token.strip()
    if token in {'–', '-', '.', 'x', ''}:
        return None
    return int(token.replace('.', '').replace(' ', ''))


def fetch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={'User-Agent': 'BW-Datenatlas/1.0 (open data retrieval)'})
    with urllib.request.urlopen(req, timeout=120) as r, path.open('wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def text_of(pdf: Path) -> str:
    try:
        out = subprocess.run(['pdftotext', '-layout', str(pdf), '-'],
                             capture_output=True, check=True)
    except FileNotFoundError as e:
        raise SystemExit('pdftotext is required (poppler-utils).') from e
    return out.stdout.decode('utf-8', 'replace')


def parse(text: str):
    """Return {(kind, normalised name): {column: value}} merged from all four blocks.

    Each district is printed exactly twice name-first (blocks 1 and 3) and exactly twice
    name-last (blocks 2 and 4). Rows are assigned to blocks by order of appearance, and
    any district that does not appear exactly twice in each orientation is an error
    rather than something to guess at.
    """
    first, last, names = {}, {}, {}
    kind = None
    num = r'(?:\d{1,3}(?:\.\d{3})*|–)'
    re_first = re.compile(r'^\s{1,6}([A-ZÄÖÜ][^\d]{2,44}?)\s{2,}((?:' + num + r'\s+){6}' + num + r')\s*$')
    re_last = re.compile(r'^\s+((?:' + num + r'\s+){6}' + num + r')\s{2,}([A-ZÄÖÜ][^\d]{2,44}?)\s*$')
    for line in text.splitlines():
        stripped = line.strip()
        if h := HEADING.match(stripped):
            kind = 'SKR' if h.group(1).startswith('Stadtkreis') else 'LKR'
            continue
        if AGGREGATE.match(stripped):
            continue
        if m := re_first.match(line):
            name, values = m.group(1).strip(), m.group(2).split()
            if AGGREGATE.match(name):
                continue
            key = (kind, norm(name))
            first.setdefault(key, []).append([number(v) for v in values])
            names.setdefault(key, name)
        elif m := re_last.match(line):
            values, name = m.group(1).split(), m.group(2).strip()
            if AGGREGATE.match(name):
                continue
            key = (kind, norm(name))
            last.setdefault(key, []).append([number(v) for v in values])
            names.setdefault(key, name)

    if set(first) != set(last):
        raise ValueError(f'Orientations disagree: {sorted(set(first) ^ set(last))}')
    out = {}
    for key in first:
        if len(first[key]) != len(BLOCK_NAME_FIRST) or len(last[key]) != len(BLOCK_NAME_LAST):
            raise ValueError(f'{names[key]}: expected {len(BLOCK_NAME_FIRST)} name-first and '
                             f'{len(BLOCK_NAME_LAST)} name-last rows, got '
                             f'{len(first[key])} and {len(last[key])}')
        row = {'name_in_source': names[key]}
        for cols, values in zip(BLOCK_NAME_FIRST, first[key]):
            row.update(zip(cols, values))
        for cols, values in zip(BLOCK_NAME_LAST, last[key]):
            row.update(zip(cols, values))
        out[key] = row
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdf', type=Path, default=ROOT / '.cache/stala-auslaender-j24.pdf')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/district-origins-2024-12.json')
    args = ap.parse_args()

    if not args.pdf.is_file():
        fetch(args.pdf)
    parsed = parse(text_of(args.pdf))

    atlas = json.loads((ROOT / 'docs/data/atlas.json').read_text(encoding='utf-8'))
    # District names in the atlas carry a "(SKR)"/"(LKR)" suffix the report does not use.
    by_name = {}
    for d in atlas['districts']:
        m = re.search(r'\((SKR|LKR)\)\s*$', d['name'])
        bare = norm(re.sub(r'\s*\((SKR|LKR)\)\s*$', '', d['name']))
        by_name.setdefault((m.group(1) if m else None, bare), []).append(d)

    districts, unmatched = [], []
    for key, row in sorted(parsed.items()):
        candidates = by_name.get(key, [])
        if len(candidates) != 1:
            unmatched.append({'name_in_source': row['name_in_source'], 'candidates': len(candidates)})
            continue
        d = candidates[0]
        rec = {'id': d['id'], 'name': d['name'], 'name_in_source': row['name_in_source'],
               'reference_period': REFERENCE_DATE}
        rec.update({c: row.get(c) for c in ALL_COLUMNS})
        districts.append(rec)

    if unmatched:
        raise ValueError(f'Unmatched districts, no guessing: {unmatched}')
    if len(districts) != 44:
        raise ValueError(f'Expected 44 districts, parsed {len(districts)}')

    named = [c for c in ALL_COLUMNS if c not in ('foreign_total', 'europe', 'eu_states')]
    for r in districts:
        if sum(r[c] or 0 for c in named) > (r['foreign_total'] or 0):
            raise ValueError(f'Named nationalities exceed the total in {r["name"]}')

    data = {
        'type': 'district_foreign_population_by_nationality',
        'schema_version': '1.0',
        'reference_period': REFERENCE_DATE,
        'source': REPORT,
        'source_table': 'Tabelle 4',
        'source_url': URL,
        'terms': 'Vervielfältigung und Verbreitung, auch auszugsweise, mit Quellenangabe gestattet.',
        'attribution': '© Statistisches Landesamt Baden-Württemberg, Fellbach',
        'measurement': 'citizenship_azr',
        'not_migration_background': (
            'Ausländerzentralregister: Staatsangehörigkeit, nicht Herkunft oder '
            'Migrationshintergrund. Eingebürgerte Personen sind hier nicht enthalten.'),
        'rounding': 'Die Quelle rundet auf 5; Summen können von Einzelwerten abweichen.',
        'columns': ALL_COLUMNS,
        'districts': districts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    # Browser view: each named nationality as a share of the district's foreign
    # population, so the map's foreign-share layer can show what it is made of.
    labels = {
        'turkey': 'Türkei', 'italy': 'Italien', 'romania': 'Rumänien', 'croatia': 'Kroatien',
        'poland': 'Polen', 'syria': 'Syrien', 'greece': 'Griechenland', 'kosovo': 'Kosovo',
        'hungary': 'Ungarn', 'bulgaria': 'Bulgarien', 'bosnia_herzegovina': 'Bosnien und Herzegowina',
        'serbia': 'Serbien', 'russia': 'Russische Föderation', 'iraq': 'Irak', 'france': 'Frankreich',
        'portugal': 'Portugal', 'austria': 'Österreich', 'spain': 'Spanien', 'india': 'Indien',
        'afghanistan': 'Afghanistan', 'china': 'China', 'north_macedonia': 'Nordmazedonien',
        'usa': 'Vereinigte Staaten', 'ukraine': 'Ukraine', 'nigeria': 'Nigeria',
    }
    view = {
        'meta': {'reference_period': REFERENCE_DATE, 'source': REPORT,
                 'source_table': 'Tabelle 4', 'source_url': URL,
                 'measurement': data['measurement'],
                 'not_migration_background': data['not_migration_background'],
                 'rounding': data['rounding'],
                 'named_share_note': ('Die aufgeführten Staatsangehörigkeiten sind die im Bericht '
                                      'am häufigsten vertretenen. Sie ergeben zusammen weniger als '
                                      '100 Prozent; der Rest verteilt sich auf alle übrigen Staaten.')},
        'labels': labels,
        'districts': {r['id']: {
            'foreign_total': r['foreign_total'],
            'europe': r['europe'], 'eu_states': r['eu_states'],
            'nationalities': {labels[c]: {'persons': r[c],
                                          'share_of_foreign_percent': round(100 * r[c] / r['foreign_total'], 1)}
                              for c in labels if r.get(c)},
        } for r in districts},
    }
    args.output.with_name('nationality-data.js').write_text(
        'window.ATLAS_NATIONALITIES=' + json.dumps(view, ensure_ascii=False,
                                                   separators=(',', ':')) + ';\n', encoding='utf-8')
    total = sum(r['foreign_total'] for r in districts)
    print(f'Parsed {len(districts)} districts; foreign population total {total:,}'.replace(',', '.'))
    print('Turkey', sum(r['turkey'] or 0 for r in districts),
          '| Syria', sum(r['syria'] or 0 for r in districts),
          '| Kosovo', sum(r['kosovo'] or 0 for r in districts),
          '| Bosnia', sum(r['bosnia_herzegovina'] or 0 for r in districts))


if __name__ == '__main__':
    main()
