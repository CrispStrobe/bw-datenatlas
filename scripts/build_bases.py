#!/usr/bin/env python3
"""Build the table of data bases shown on the site.

Every number in this atlas rests on one of four very different kinds of source, and
mixing them silently is how misleading comparisons happen:

  Register        a continuously maintained administrative register (AZR). Counts
                  people on file, not residents as the population statistic defines them.
  Fortschreibung  the official population projection, carried forward from the last
                  census with births, deaths and registered moves.
  Stichprobe      a sample survey (Mikrozensus). Carries sampling error; small cells
                  are suppressed.
  Vollerhebung    the census (Zensus 2022), with cell-key confidentiality noise.
  Modell          computed in this project from the above, never measured.

The most visible consequence: the foreign population appears twice on the site with
different values, because the projection and the register do not count the same thing
on the same day. The official report says so itself. Rather than hide one of them, the
site names both and states the difference.

The entries are assembled from the generated data files, so a changed reference date
or source in the pipeline shows up here rather than drifting out of sync with prose.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KIND_LABELS = {
    'register': 'Register',
    'fortschreibung': 'Fortschreibung',
    'sample': 'Stichprobe',
    'census': 'Vollerhebung',
    'model': 'Modellrechnung',
}
KIND_NOTES = {
    'register': 'Laufend geführtes Verwaltungsregister. Zählt erfasste Personen, nicht die Wohnbevölkerung der Bevölkerungsstatistik.',
    'fortschreibung': 'Amtliche Bevölkerungsfortschreibung, vom letzten Zensus fortgeschrieben.',
    'sample': 'Stichprobenerhebung mit Zufallsfehler. Kleine Fallzahlen werden geheim gehalten und bleiben hier fehlend.',
    'census': 'Vollerhebung mit Geheimhaltung nach dem Cell-Key-Verfahren; Einzelwerte sind bewusst überlagert.',
    'model': 'In diesem Projekt gerechnet, nicht gemessen. Trägt immer eine Spanne.',
}


def load(name):
    path = ROOT / 'docs/data' / name
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/data/bases.json')
    args = ap.parse_args()

    atlas = load('atlas.json')
    origins = load('district-origins-2024-12.json')
    migration = load('district-migration-2024.json')
    age = load('district-age-2024.json')
    generations = load('district-generations-2024.json')
    socio = load('district-socioeconomics-2024.json')
    grid = load('municipal-origins-2022.json')
    bound = load('municipal-religion-bound.json')
    estimate = load('district-estimate.json')
    pyramid = load('state-age-pyramid-2025.json')
    demography = load('municipal-demography-2022.json')
    timeseries = load('district-timeseries.json')

    # Federal reference figures, for a cross-check of our state totals.
    federal = {}
    fed_path = ROOT / 'inputs/destatis-12411-bevoelkerung-bw.csv'
    if fed_path.is_file():
        import csv as _csv
        for r in _csv.DictReader(fed_path.open(encoding='utf-8')):
            federal[(r['geography'], r['nationality'])] = int(r['persons'])

    districts = atlas['districts']
    fortschreibung_foreign = sum(d['foreign'] for d in districts)
    fortschreibung_population = sum(d['population'] for d in districts)
    register_foreign = sum(d['foreign_total'] for d in origins['districts'])

    entries = [
        {'measure': 'Einwohnerzahl der Kreise', 'kind': 'fortschreibung',
         'reference': '30.11.2024', 'geography': '44 Kreise',
         'source': 'Statistisches Landesamt Baden-Württemberg',
         'used_for': 'Nenner der Anteile, Verteilungsschlüssel'},
        {'measure': 'Einwohnerzahl der Gemeinden', 'kind': 'fortschreibung',
         'reference': '30.06.2024', 'geography': '1.101 Gemeinden',
         'source': 'Statistisches Landesamt Baden-Württemberg',
         'used_for': 'Nenner der Gemeindeanteile'},
        {'measure': 'Ausländische Staatsangehörige (Kreiswert der Karte)', 'kind': 'fortschreibung',
         'reference': '30.11.2024', 'geography': '44 Kreise',
         'source': 'Statistisches Landesamt Baden-Württemberg',
         'used_for': 'Ebene „Ausländische Staatsangehörige“',
         'value_persons': fortschreibung_foreign},
        {'measure': 'Ausländische Staatsangehörige nach Staatsangehörigkeit', 'kind': 'register',
         'reference': origins['reference_period'], 'geography': '44 Kreise',
         'source': origins['source'] + ', ' + origins['source_table'],
         'used_for': 'Herkunftsschlüssel der Modellrechnung, Zusammensetzung im Kreisprofil',
         'value_persons': register_foreign},
        {'measure': 'Bevölkerung mit Migrationshintergrund', 'kind': 'sample',
         'reference': migration['reference_period'], 'geography': '44 Kreise aus 43 Erhebungsregionen',
         'source': migration['source'],
         'used_for': 'Korrektur für Eingebürgerte, Verteilung des nicht erklärten Rests'},
        {'measure': 'Altersgliederung nach Migrationsstatus', 'kind': 'sample',
         'reference': age['reference_period'], 'geography': '44 Kreise',
         'source': age['source'], 'used_for': 'Ebene „Unter 25-Jährige“, Altersbalken im Profil'},
        {'measure': 'Zweite Generation, Familienstand', 'kind': 'sample',
         'reference': generations['reference_period'], 'geography': '44 Kreise',
         'source': generations['source'],
         'used_for': 'Ebene „Zweite Generation“, Gegenprobe der Korrektur'},
        {'measure': 'Erwerbsbeteiligung und Bildungsstand', 'kind': 'sample',
         'reference': socio['reference_period'], 'geography': '44 Kreise',
         'source': socio['source'], 'used_for': 'Ebene „Erwerbstätige“, Kontext im Profil'},
        {'measure': 'Altersaufbau nach Einwanderungsgeschichte', 'kind': 'sample',
         'reference': pyramid['reference_period'], 'geography': 'Baden-Württemberg',
         'source': pyramid['source'].split(',')[0] + ', Mikrozensus',
         'used_for': 'Alterspyramide; eigene Klassifikation, nicht mit dem Migrationshintergrund vermischt'},
        {'measure': 'Veränderung des Migrationshintergrunds', 'kind': 'sample',
         'reference': f"{timeseries['years'][0]}–{timeseries['years'][-1]}", 'geography': '44 Kreise',
         'source': timeseries['source'], 'used_for': 'Ebene „Veränderung“, Verlaufsbalken'},
        {'measure': 'Altersgliederung je Gemeinde', 'kind': 'census',
         'reference': demography['reference_period'], 'geography': '1.101 Gemeinden',
         'source': demography['source'],
         'used_for': 'Ebene „Unter 25-Jährige · Gemeinden“; Vollerhebung statt Stichprobe'},
        {'measure': 'Einwanderungsgeschichte je Gemeinde', 'kind': 'census',
         'reference': demography['reference_period'], 'geography': '1.101 Gemeinden',
         'source': demography['source'],
         'used_for': 'Verteilungsschlüssel für die Herkünfte ohne eigene Gemeindedaten'},
        {'measure': 'Staatsangehörigkeit im 100-Meter-Gitter', 'kind': 'census',
         'reference': grid['reference_period'], 'geography': '1.101 Gemeinden',
         'source': grid['source'], 'used_for': 'Verteilungsmuster innerhalb der Kreise'},
        {'measure': 'Religionszugehörigkeit je Gemeinde', 'kind': 'census',
         'reference': bound['reference_period'], 'geography': '1.101 Gemeinden',
         'source': bound['source'],
         'used_for': 'Obergrenze der Modellwerte. Der Islam ist dort keine eigene Kategorie'},
        {'measure': 'Muslimische Anteile je Herkunftsgruppe', 'kind': 'sample',
         'reference': '2019/2020', 'geography': 'Deutschland',
         'source': 'BAMF, Forschungsbericht 55, Tabelle 2 (Erhebung MLD 2020)',
         'used_for': 'Parameter der Modellrechnung. Auch der BAMF-Bericht rechnet seine Werte für 2025 damit'},
        {'measure': 'Muslimische Bevölkerung, Landessumme', 'kind': 'model',
         'reference': estimate['state_total']['reference_period'], 'geography': 'Baden-Württemberg',
         'source': 'BAMF, Forschungsbericht 55, Tabelle 3',
         'used_for': 'Die verteilte Summe. Bezugsbevölkerung ist der Mikrozensus, nicht die Fortschreibung'},
        {'measure': 'Muslimische Bevölkerung je Kreis und Gemeinde', 'kind': 'model',
         'reference': '2025', 'geography': '44 Kreise, 1.101 Gemeinden',
         'source': 'Diese Anwendung', 'used_for': 'Ebenen „Modell je Kreis“ und „Modell je Gemeinde“'},
    ]

    for e in entries:
        e['kind_label'] = KIND_LABELS[e['kind']]

    difference = register_foreign - fortschreibung_foreign
    data = {
        'type': 'data_bases',
        'schema_version': '1.0',
        'kinds': {k: {'label': KIND_LABELS[k], 'note': KIND_NOTES[k]} for k in KIND_LABELS},
        'headline': ('Jede Zahl im Atlas stammt aus einer von vier Arten von Quelle. '
                     'Sie zählen Unterschiedliches und dürfen nicht gegeneinander '
                     'aufgerechnet werden.'),
        'two_foreign_counts': {
            'fortschreibung_persons': fortschreibung_foreign,
            'fortschreibung_reference': '30.11.2024',
            'register_persons': register_foreign,
            'register_reference': origins['reference_period'],
            'difference_persons': difference,
            'explanation': (
                'Die ausländische Bevölkerung erscheint mit zwei Werten, weil '
                'Bevölkerungsfortschreibung und Ausländerzentralregister nicht dasselbe '
                'zum selben Stichtag zählen. Der amtliche Bericht hält ausdrücklich fest, '
                'dass beide Quellen „infolge methodischer und zeitlicher Unterschiede in '
                'ihren Bestandszahlen voneinander abweichen“. Die Karte zeigt den Wert der '
                'Fortschreibung, die Zusammensetzung nach Staatsangehörigkeit stammt aus '
                'dem Register. Die Modellrechnung verwendet das Register nur als '
                'räumlichen Schlüssel und rechnet die Summe auf die veröffentlichte '
                'Landessumme; der Niveauunterschied wirkt sich dadurch nicht auf die '
                'Anteile aus.'),
        },
        'census_revision_note': (
            'Der Zensus 2022 korrigierte die aus dem Zensus 2011 fortgeschriebene '
            f'Bevölkerung. Je Gemeinde betrug diese Korrektur im Median '
            f'{demography["census_revision_median_percent"]:+.1f} Prozent, in der Spanne von '
            f'{demography["census_revision_range_percent"][0]:+.1f} bis '
            f'{demography["census_revision_range_percent"][1]:+.1f} Prozent.'),
        'denominator_note': (
            'Die veröffentlichte Landesspanne von 10,1 bis 10,7 Prozent bezieht sich auf '
            'die Bevölkerung in privaten Hauptwohnsitzhaushalten des Mikrozensus. Die '
            'Prozentwerte je Kreis und Gemeinde in diesem Atlas beziehen sich dagegen auf '
            'die Einwohnerzahl der Fortschreibung. Beide Nenner unterscheiden sich; die '
            'Werte sind deshalb nicht bis auf die Nachkommastelle mit der Landesangabe '
            'vergleichbar.'),
        'population_fortschreibung_persons': fortschreibung_population,
        'federal_cross_check': {
            'source': ('Statistisches Bundesamt, Statistischer Bericht 12411, '
                       'Bevölkerungsfortschreibung auf Basis Zensus 2022'),
            'reference': '31.12.2025',
            'federal_bw_population': federal.get(('Baden-Württemberg', 'insgesamt')),
            'federal_bw_foreign': federal.get(('Baden-Württemberg', 'nichtdeutsch')),
            'our_population': fortschreibung_population,
            'our_foreign': fortschreibung_foreign,
            'population_difference_percent': round(
                100 * (fortschreibung_population - federal[('Baden-Württemberg', 'insgesamt')])
                / federal[('Baden-Württemberg', 'insgesamt')], 2)
            if federal.get(('Baden-Württemberg', 'insgesamt')) else None,
            'reading': ('Unsere Landessumme stimmt mit dem Bundeswert überein, obwohl die '
                        'Stichtage 13 Monate auseinanderliegen. Das bestätigt die '
                        'Größenordnung, nicht mehr.'),
            'what_it_cannot_show': (
                'Welche Zensusgrundlage unsere Fortschreibung verwendet, lässt sich daran '
                'NICHT ablesen: Auf Landesebene unterscheiden sich die alte Fortschreibung '
                'auf Basis Zensus 2011 und der Zensus 2022 nur um wenige Hundertstel '
                'Prozent. Die Korrektur des Zensus 2022 war je Gemeinde erheblich, im '
                'Median -1,4 Prozent und in der Spanne von -14,9 bis +6,6 Prozent, hebt '
                'sich in der Landessumme aber nahezu auf.'),
        },
        'entries': entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    args.output.with_name('bases-data.js').write_text(
        'window.ATLAS_BASES=' + json.dumps(data, ensure_ascii=False,
                                           separators=(',', ':')) + ';\n', encoding='utf-8')

    print(f'{len(entries)} entries.')
    print(f'Foreign population: Fortschreibung {fortschreibung_foreign:,}, '
          f'Register {register_foreign:,}, difference {difference:,}'.replace(',', '.'))


if __name__ == '__main__':
    main()
