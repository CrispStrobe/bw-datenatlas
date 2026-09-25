#!/usr/bin/env python3
"""Migration flows for Baden-Württemberg, from the official annual report A III 1-j.

The atlas had no migration data at all. It could say how many people of which origin live
in a district and not one thing about movement — which is the mechanism behind every
number it does show. This report is the missing half, and it is the state's own.

There is no Excel annex; the report exists only as a PDF. The tables in it are embedded
text rather than scans, so `pdftotext -layout` recovers them exactly, and the layout is
regular enough to parse by column position. Four of its six tables are read here:

  1  the state series 1995–2023, which puts any single year in proportion
  2  arrivals, departures and balance for all 44 Stadt- und Landkreise, separately for
     the population as a whole (2a) and for foreign nationals (2b)
  4  cross-border movement by country of origin and destination — the one table that
     names Turkey, Syria, Romania and the rest, with arrivals, departures and balance
  6  cross-border movement by age group

Table 5, the 44×44 matrix of movement between districts, is not read: it is large, and
nothing on the page would use it.

WHAT THESE NUMBERS ARE NOT. A Zuzug is a registration with a Meldebehörde, not a person:
someone who moves twice in a year is counted twice, and the balance is not population
growth. They say nothing about religion, and nothing in this file feeds the religion
model.

Licence: © Statistisches Landesamt Baden-Württemberg; reproduction permitted with
attribution.
"""
from __future__ import annotations
import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/stala-wanderung-a3-1j-2023.pdf'
OUTPUT = ROOT / 'docs/data/bw-migration-flows-2023.json'
SOURCE = ('https://www.statistik-bw.de/fileadmin/user_upload/Service/Veroeff/'
          'Statistische_Berichte/314523001.pdf')
PAGE = ('https://www.statistik-bw.de/leben-und-arbeiten/bevoelkerung-und-gebiet/'
        'migration-und-nationalitaet/')

# "1.302", "+ 1.302", "– 4.488", "12 959", "–" for a true zero.
NUMBER = re.compile(r'[+–-]?\s*\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|^–$')
# Lines that are headings, page furniture or footnotes rather than data.
NOISE = re.compile(r'^\s*(Noch:|Artikel-Nr|Statistisches Landesamt|©|\*\)|\d\)|'
                   r'Herkunfts- und Zielgebiet|Altersgruppe|Kreis|Region$|Land$|'
                   r'Regierungsbezirk|Zuzüge|Fortzüge|Wanderungs|darunter|davon|'
                   r'Personen|insgesamt|männlich|Stadtkreis|Landkreise|Insgesamt)',
                   re.I)


def text() -> str:
    if not (CACHE.is_file() and CACHE.stat().st_size > 100000):
        CACHE.parent.mkdir(exist_ok=True)
        request = urllib.request.Request(
            SOURCE, headers={'User-Agent': 'BW-Datenatlas/0.1 '
                                           '(+https://github.com/CrispStrobe)'})
        with urllib.request.urlopen(request, timeout=120) as response:
            CACHE.write_bytes(response.read())
    out = CACHE.with_suffix('.txt')
    subprocess.run(['pdftotext', '-layout', str(CACHE), str(out)], check=True)
    return out.read_text(encoding='utf-8')


def numbers(line: str) -> list[float]:
    """Every number on the line, with German separators and the report's minus sign."""
    found = []
    for raw in re.findall(r'[+–-]?\s*\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?', line):
        cleaned = raw.replace(' ', '').replace('.', '').replace(',', '.')
        sign = -1.0 if cleaned.startswith(('–', '-')) else 1.0
        cleaned = cleaned.lstrip('+–-')
        if not cleaned:
            continue
        found.append(sign * float(cleaned))
    return found


def section(lines: list[str], start: str, stop: str) -> list[str]:
    a = next(i for i, l in enumerate(lines) if l.strip().startswith(start))
    b = next(i for i, l in enumerate(lines[a + 1:], a + 1) if l.strip().startswith(stop))
    return lines[a:b]


def label(line: str) -> str:
    return re.split(r'\s{2,}', line.strip())[0].strip()


def columns(line: str, count: int) -> list[float] | None:
    """The last `count` numbers on the line — the data columns.

    Counting from the left breaks on every row whose LABEL contains a digit, and this
    report is full of them: "unter 5", "5 – 10", "75 und mehr". Taking the trailing
    columns is both simpler and right, because the number of data columns is fixed by
    the table and the label is whatever precedes them.
    """
    values = numbers(line)
    return values[-count:] if len(values) >= count else None


def parse_state_series(lines: list[str]) -> list[dict]:
    out = []
    for line in section(lines, '1. Wanderungsbewegungen', '2. Wanderungen'):
        stripped = line.strip()
        if not stripped[:4].isdigit():
            continue
        year = int(stripped[:4])
        values = columns(line, 6)
        if values is None or not 1995 <= year <= 2035:
            continue
        out.append({'year': year, 'across_state_border_thousands': values[0],
                    'within_state_thousands': values[2],
                    'total_thousands': values[4],
                    'total_per_1000_inhabitants': values[5]})
    return out


def parse_districts(lines: list[str], start: str, stop: str) -> list[dict]:
    out = []
    for line in section(lines, start, stop):
        if NOISE.match(line) or not line.startswith(('  ', 'Region', 'Regierungs', 'Baden')):
            continue
        name = label(line)
        values = columns(line, 6)
        # "im Jahr 20231)" is the tail of a column heading that wraps onto its own line
        # and carries a year that looks like data. Named rows only.
        if values is None or not name or name[0].isdigit() or name.startswith('im Jahr'):
            continue
        kind = ('state' if name.startswith('Baden-Württemberg')
                else 'region' if name.startswith(('Region', 'Regierungsbezirk'))
                else 'district')
        out.append({'name': name, 'kind': kind, 'arrivals': int(values[0]),
                    'arrivals_per_1000': values[1], 'departures': int(values[2]),
                    'departures_per_1000': values[3], 'balance': int(values[4]),
                    'balance_per_1000': values[5]})
    return out


def parse_countries(lines: list[str]) -> list[dict]:
    out = []
    for line in section(lines, '4. Wanderungen über die Landesgrenze', '5. Wanderungsströme'):
        if NOISE.match(line):
            continue
        name = label(line)
        values = columns(line, 7)
        if values is None or not name or name[0].isdigit():
            continue
        indent = len(line) - len(line.lstrip())
        out.append({'area': name, 'level': min(indent // 2, 3),
                    'arrivals': int(values[0]), 'arrivals_male': int(values[1]),
                    'arrivals_foreign': int(values[2]), 'departures': int(values[3]),
                    'departures_male': int(values[4]), 'departures_foreign': int(values[5]),
                    'balance': int(values[6])})
    return out


def parse_age_groups(lines: list[str]) -> list[dict]:
    out, seen = [], set()
    for line in lines[next(i for i, l in enumerate(lines)
                           if l.strip().startswith('6. Wanderungen')):]:
        if NOISE.match(line):
            continue
        stripped = line.strip()
        if not ('–' in stripped[:24] or stripped.startswith(('unter', '75'))):
            continue
        values = columns(line, 6)
        if values is not None:
            name = re.split(r'\s{2,}', stripped)[0].strip()
            if name in seen:
                continue
            seen.add(name)
            out.append({'age_group': name, 'arrivals': int(values[0]),
                        'arrivals_foreign': int(values[1]), 'departures': int(values[2]),
                        'departures_foreign': int(values[3]), 'balance': int(values[4]),
                        'balance_foreign': int(values[5])})
    return out


def main() -> None:
    lines = text().splitlines()
    doc = {
        'type': 'bw_migration_flows',
        'schema_version': '1.0',
        'reference_period': '2023',
        'source': ('Statistisches Landesamt Baden-Württemberg, Statistischer Bericht '
                   'A III 1 - j/23: Wanderungsbewegung in Baden-Württemberg 2023, '
                   'veröffentlicht 22.11.2024'),
        'source_url': SOURCE,
        'source_page': PAGE,
        'licence': ('© Statistisches Landesamt Baden-Württemberg; Vervielfältigung und '
                    'Verbreitung, auch auszugsweise, mit Quellenangabe gestattet'),
        'what_is_counted': ('Zu- und Fortzüge, wie die Meldebehörden sie übermitteln. '
                            'Gezählt werden Meldevorgänge, nicht Personen: Wer zweimal im '
                            'Jahr umzieht, steht zweimal darin. Der Saldo ist kein '
                            'Bevölkerungswachstum.'),
        'not_a_religion_measure': ('Wanderung sagt nichts über Religion. Diese Zahlen '
                                   'gehen in keine Modellrechnung dieses Atlas ein.'),
        'state_series': parse_state_series(lines),
        'districts_total_population': parse_districts(
            lines, '2. Wanderungen über die Gemeindegrenze', 'b) Ausländer'),
        'districts_foreign_nationals': parse_districts(
            lines, 'b) Ausländer', '3. Wanderungsbewegungen innerhalb'),
        'by_country': parse_countries(lines),
        'by_age_group': parse_age_groups(lines),
    }
    OUTPUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')
    OUTPUT.with_name('bw-flows-data.js').write_text(
        'window.ATLAS_BW_FLOWS=' + json.dumps(doc, ensure_ascii=False,
                                              separators=(',', ':')) + ';\n',
        encoding='utf-8')
    districts = [r for r in doc['districts_total_population'] if r['kind'] == 'district']
    if len(districts) != 44:
        raise SystemExit(f'{len(districts)} Kreise gelesen, erwartet sind 44 — '
                         'der Bericht oder sein Satz hat sich geändert')
    print(f"{len(doc['state_series'])} Jahre, "
          f"{len(districts)} Kreise (+ Regionen und Land), "
          f"{len(doc['districts_foreign_nationals'])} Zeilen Ausländer, "
          f"{len(doc['by_country'])} Herkunfts- und Zielgebiete, "
          f"{len(doc['by_age_group'])} Altersgruppen")


if __name__ == '__main__':
    main()
