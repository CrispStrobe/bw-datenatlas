#!/usr/bin/env python3
"""Das 1-Kilometer-Gitter des Zensus 2022, auf Baden-Württemberg zugeschnitten.

Bis hierher endet der Atlas bei der Gemeinde. Das ist für große Städte die gröbste
denkbare Auflösung: Stuttgart hat 610.000 Einwohner und einen einzigen Wert. Wo
innerhalb einer Stadt wer wohnt, war damit nicht zu sehen — und gerade das ist die
Frage, auf die sonst Vermutungen antworten.

Der Zensus veröffentlicht seine Ergebnisse auch in Gitterzellen. Diese Ebene ist
amtlich, eine Vollerhebung, und sie ist die einzige unterhalb der Gemeinde, die es
je geben wird: eine Erhebung feiner als der Zensus ist nicht in Sicht.

Zugeschnitten wird gegen die Landesfläche selbst und nicht gegen ein Rechteck. Ein
Rechteck um Baden-Württemberg enthält Teile von Bayern, Hessen, Rheinland-Pfalz und
der Schweiz, und die gehören nicht auf diese Karte.

Geheimhaltung: der Zensus überlagert Zellenwerte nach dem Cell-Key-Verfahren und
sperrt kleine Fälle. Die Datei führt die erläuternden Zeichen mit; eine gesperrte
Zelle bleibt leer, statt als Null gezeichnet zu werden. Bei einer Auflösung von
einem Kilometer ist das der Unterschied zwischen "hier wohnt niemand" und "hier
durfte nichts gesagt werden".

Die Quelldateien sind je 11 bis 15 MB groß und liegen nicht im Repository. Das
Skript liest sie aus einem Verzeichnis, das beim Aufruf angegeben wird, und legt
nur den zugeschnittenen Auszug ab.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Unter so vielen Einwohnern wird kein Anteil gebildet: die Geheimhaltung
# verschiebt kleine Zahlen um genau die Größenordnung, um die es dann ginge.
MINDESTGROESSE = 30

# Welche Größen übernommen werden, mit dem Dateinamensmuster und der Wertspalte.
GROESSEN = {
    'foreign_pct': ('*Anteil_Auslaender_1km*.csv', 'AnteilAuslaender',
                    'Ausländeranteil', 'percent'),
    'mean_age': ('*Durchschnittsalter_1km*.csv', 'Durchschnittsalter',
                 'Durchschnittsalter', 'years'),
    'under_18_pct': ('*Anteil_unter_18_1km*.csv', 'AnteilUnter18',
                     'Unter 18-Jährige', 'percent'),
    'age_65_plus_pct': ('*Anteil_ueber_65_1km*.csv', 'AnteilUeber65',
                        'Ab 65-Jährige', 'percent'),
}

# Größen, die als Zahl geliefert werden und erst durch die Einwohnerzahl derselben
# Zelle zu einem Anteil werden. Die Nennerspalte steht in derselben Datei.
ANTEILE = {
    'turkish_pct': ('*Staatsangehoerigkeit_nach_Laendern_1km*.csv', 'Tuerkei',
                    'Türkische Staatsangehörige', 'percent'),
    # Bosnien und Herzegowina liefert die Datei ebenfalls, aber nur für 3.796 der
    # 21.585 Zellen — jede fünfte. Eine Karte, die zu vier Fünfteln leer ist und bei
    # der leer zweierlei heißt, sagt mehr über die Geheimhaltung als über das Land.
    # Deshalb nicht übernommen.
    'age_18_29_pct': ('*Alter_in_5_Altersklassen_1km*.csv', 'a18bis29',
                      '18- bis 29-Jährige', 'percent'),
    'age_30_49_pct': ('*Alter_in_5_Altersklassen_1km*.csv', 'a30bis49',
                      '30- bis 49-Jährige', 'percent'),
    'age_50_64_pct': ('*Alter_in_5_Altersklassen_1km*.csv', 'a50bis64',
                      '50- bis 64-Jährige', 'percent'),
}


def zahl(text: str):
    text = (text or '').strip()
    if not text or text in ('–', '-', '.', 'x'):
        return None
    try:
        return float(text.replace('.', '').replace(',', '.'))
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--quelle', type=Path, required=True,
                    help='Verzeichnis mit den entpackten Gitterzellen-Ordnern')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/grid-bw-1km.json')
    args = ap.parse_args()

    from pyproj import Transformer
    from shapely.geometry import shape, Point
    from shapely.prepared import prep

    geo = json.loads((ROOT / 'docs/data/geometry.json').read_text(encoding='utf-8'))
    land = prep(shape(geo['state']['geometry']).buffer(0.004))
    nach_wgs = Transformer.from_crs(3035, 4326, always_xy=True)

    zellen: dict[str, dict] = {}
    gefunden = {}
    for schluessel, (muster, spalte, titel, einheit) in GROESSEN.items():
        treffer = sorted(args.quelle.glob('*/' + muster)) or sorted(args.quelle.glob(muster))
        if not treffer:
            print(f'  {schluessel:16s} keine Datei für {muster} — übersprungen')
            continue
        pfad = treffer[0]
        n = 0
        with pfad.open(encoding='utf-8-sig') as fh:
            leser = csv.DictReader(fh, delimiter=';')
            if spalte not in (leser.fieldnames or []):
                kandidat = [f for f in leser.fieldnames
                            if f not in ('GITTER_ID_1km', 'x_mp_1km', 'y_mp_1km')
                            and 'zeichen' not in f.lower()]
                if not kandidat:
                    print(f'  {schluessel}: Wertspalte nicht gefunden in {leser.fieldnames}')
                    continue
                spalte = kandidat[0]
            for r in leser:
                x, y = float(r['x_mp_1km']), float(r['y_mp_1km'])
                # Erst das billige Rechteck, dann die teure Fläche.
                if not (4150000 <= x <= 4400000 and 2680000 <= y <= 2980000):
                    continue
                lon, lat = nach_wgs.transform(x, y)
                if not land.contains(Point(lon, lat)):
                    continue
                w = zahl(r[spalte])
                if w is None:
                    continue
                z = zellen.setdefault(r['GITTER_ID_1km'],
                                      {'lon': round(lon, 4), 'lat': round(lat, 4)})
                z[schluessel] = round(w, 1)
                n += 1
        gefunden[schluessel] = {'title': titel, 'unit': einheit,
                                'source_file': pfad.name, 'cells': n}
        print(f'  {schluessel:16s} {n:6d} Zellen aus {pfad.name}')

    # Spaltenweise statt zeilenweise: bei 21.000 Zellen wiegen die wiederholten
    # Feldnamen mehr als die Zahlen selbst. So wird aus 2,2 MB ein Drittel davon.
    # Die Anteilsgrößen: Zähler und Nenner stehen in derselben Zeile, also wird hier
    # gerechnet und nicht im Browser. Eine gesperrte Zahl bleibt gesperrt — sie als
    # Null zu lesen hieße, aus einer Geheimhaltung eine Aussage zu machen.
    for schluessel, (muster, spalte, titel, einheit) in ANTEILE.items():
        treffer = sorted(args.quelle.glob('*/' + muster)) or sorted(args.quelle.glob(muster))
        if not treffer:
            print(f'  {schluessel:16s} keine Datei für {muster} — übersprungen')
            continue
        pfad = treffer[0]
        n = zu_klein = unmoeglich = 0
        with pfad.open(encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh, delimiter=';'):
                kennung = r['GITTER_ID_1km']
                z = zellen.get(kennung)
                if z is None:
                    continue
                zaehler = zahl(r.get(spalte))
                nenner = zahl(r.get('Insgesamt_Bevoelkerung'))
                if zaehler is None or not nenner:
                    continue
                # Zwei Regeln gegen die Überlagerung, beide gezählt statt still
                # angewandt. Erstens eine Mindestgröße: ein Anteil aus fünf
                # Einwohnern ist kein Anteil, sondern Rauschen — die Cell-Key-
                # Überlagerung verschiebt kleine Zahlen um genau die Größenordnung,
                # um die es dabei geht. Bundesweit kostet die Grenze 338 von 36.169
                # Zellen. Zweitens das Unmögliche: in genau einer Zelle in ganz
                # Deutschland ist der Zähler größer als der Nenner (3 Einwohner,
                # 9 türkische Staatsangehörige). Das ist kein Wert, den man kappt,
                # sondern einer, den man wegläßt und nennt.
                if nenner < MINDESTGROESSE:
                    zu_klein += 1
                    continue
                if zaehler > nenner:
                    unmoeglich += 1
                    continue
                z[schluessel] = round(100 * zaehler / nenner, 1)
                n += 1
        gefunden[schluessel] = {'title': titel, 'unit': einheit,
                                'source_file': pfad.name, 'cells': n,
                                'derived': f'{spalte} / Insgesamt_Bevoelkerung',
                                'dropped_too_small': zu_klein,
                                'dropped_impossible': unmoeglich,
                                'minimum_denominator': MINDESTGROESSE}
        print(f'  {schluessel:16s} {n:6d} Zellen aus {pfad.name}'
              + (f' · {zu_klein} zu klein' if zu_klein else '')
              + (f' · {unmoeglich} unmöglich' if unmoeglich else ''))

    reihe = sorted(zellen.values(), key=lambda z: (z['lat'], z['lon']))
    spalten = {'lon': [z['lon'] for z in reihe], 'lat': [z['lat'] for z in reihe]}
    for k in gefunden:
        spalten[k] = [z.get(k) for z in reihe]

    doc = {
        'type': 'zensus2022_grid_bw_1km',
        'schema_version': '1.0',
        'what_this_is': ('Ergebnisse des Zensus 2022 in Gitterzellen von einem Kilometer '
                         'Kantenlänge, zugeschnitten auf die Landesfläche '
                         'Baden-Württembergs. Die einzige Ebene unterhalb der Gemeinde, '
                         'die es amtlich gibt.'),
        'why_it_matters': ('Eine Gemeinde wie Stuttgart hat 610.000 Einwohner und auf den '
                           'übrigen Ebenen einen einzigen Wert. Wo innerhalb einer Stadt '
                           'wer wohnt, ist erst hier zu sehen.'),
        'minimum_denominator': MINDESTGROESSE,
        'how_shares_are_guarded': (
            'Anteile werden nur gebildet, wo die Zelle mindestens '
            f'{MINDESTGROESSE} Einwohner hat, und nicht, wo der Zähler größer ist '
            'als der Nenner. Beides kommt von der Cell-Key-Überlagerung. Wie viele '
            'Zellen das je Größe kostet, steht bei der Größe selbst — weggelassen, '
            'nicht gekappt.'),
        'secrecy': ('Der Zensus überlagert Zellenwerte nach dem Cell-Key-Verfahren und '
                    'sperrt kleine Fälle. Gesperrte Zellen bleiben leer und werden nicht '
                    'als Null gezeichnet: bei einem Kilometer Kantenlänge ist das der '
                    'Unterschied zwischen "hier wohnt niemand" und "hier durfte nichts '
                    'gesagt werden".'),
        'no_religion': ('Das Gitter enthält keine Religionsangabe zum Islam. Die '
                        'Religionsdatei des Zensus führt nur römisch-katholisch, '
                        'evangelisch und eine Restkategorie, weil der Zensus 2022 gar '
                        'nicht nach Religion gefragt hat, sondern das Melderegister '
                        'auswertet.'),
        'reference_period': '2022-05-15',
        'source': 'Statistische Ämter des Bundes und der Länder, Zensus 2022, Gitterzellen',
        'source_url': 'https://www.zensus2022.de/DE/Ergebnisse-des-Zensus/_inhalt.html',
        'licence': 'Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)',
        'grid_crs': 'EPSG:3035, Zellmittelpunkte nach WGS 84 umgerechnet',
        'measures': gefunden,
        'columnar': ('Spaltenweise gespeichert: columns.lon[i], columns.lat[i] und '
                     'columns.<größe>[i] gehören zur selben Zelle. Ein null bedeutet '
                     'gesperrt oder nicht ausgewiesen, nicht null Personen.'),
        'count': len(reihe),
        'columns': spalten,
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n',
                        encoding='utf-8')
    print(f'\n{len(reihe)} Zellen in Baden-Württemberg · '
          f'{args.out.stat().st_size // 1024} KiB')


if __name__ == '__main__':
    main()
