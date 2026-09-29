#!/usr/bin/env python3
"""Orthodoxe, Freikirchen, jüdische Gemeinden: was der Zensus 2011 einzeln auswies.

Der Zensus 2022 kennt bei der Religion drei Kategorien — römisch-katholisch, evangelisch
und alles andere in einem Topf. Der Zensus 2011 war feiner: er wies die öffentlich-
rechtlichen Religionsgesellschaften einzeln aus, und damit gibt es genau eine Zählung
der orthodoxen Christinnen und Christen in Baden-Württemberg, Kreis für Kreis.

Das ist für diesen Atlas wichtig, weil die orthodoxen und orientalischen Kirchen die
größte eingewanderte christliche Gruppe des Landes sind und in der Restkategorie von
2022 unsichtbar verschwinden. Baden-Württemberg hatte 2011 mit 2,1 Prozent den höchsten
orthodoxen Bevölkerungsanteil aller Länder; im Bund waren es 1,3 Prozent.

Drei Dinge, die an jeder dieser Zahlen hängen:

  Sie ist von 2011.  Fünfzehn Jahre. Seither sind Menschen aus Rumänien, Bulgarien,
      Syrien und der Ukraine zugewandert, und zwar nicht wenige. Die Zahl ist eine
      Untergrenze für heute, keine Gegenwartsangabe.
  Sie zählt Mitgliedschaft, nicht Glauben.  Gezählt wurde die Zugehörigkeit zu einer
      Religionsgesellschaft des öffentlichen Rechts, wie sie in den Melderegistern
      steht. Wer sich orthodox versteht, aber in keinem Register einer orthodoxen
      Körperschaft geführt wird, steht hier nicht — und der Körperschaftsstatus ist
      von Kirche zu Kirche und von Land zu Land verschieden. Die syrisch-orthodoxe
      Kirche etwa erscheint nur, wo sie diesen Status hat.
  Sie ist geheimgehalten.  Kleine Werte sind mit "/" gesperrt und werden hier nicht
      geraten, sondern als fehlend geführt.

Die Quelle sind die 44 Kreisbände „Zensus 2011 – Baden-Württemberg" des Statistischen
Landesamts. Jeder Band enthält dieselbe Vergleichstabelle mit Kreis, Regierungsbezirk,
Land und Bund. Dass die Landes- und Bundesspalte in allen 44 Bänden identisch sein muss,
ist hier kein Nebenprodukt, sondern die Prüfung: weicht ein Band ab, ist die Auslesung
falsch, nicht die Statistik.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERIE = 'https://www.statistischebibliothek.de/mir/receive/BWSerie_mods_00000583'
HEFT = 'https://www.statistischebibliothek.de/mir/receive/BWHeft_mods_{}'
DATEI = 'https://www.statistischebibliothek.de/mir/servlets/MCRFileNodeServlet/{}'
UA = {'User-Agent': 'BW-Datenatlas/1.0'}

# Die Reihenfolge ist die der Quelle; sie wird beim Auslesen geprüft, damit eine
# veränderte Tabelle nicht stillschweigend in falsche Spalten läuft.
KATEGORIEN = [
    ('roman_catholic', 'Römisch-katholische Kirche'),
    ('protestant', 'Evangelische Kirche'),
    ('protestant_free', 'Evangelische Freikirchen'),
    ('orthodox', 'Orthodoxe Kirchen'),
    ('jewish', 'Jüdische Gemeinden'),
    ('other_public_law', 'Sonstige'),
    ('none', 'Keiner ö.-r. Religionsgesellschaft zugehörig'),
]
SPALTEN = ['kreis', 'regierungsbezirk', 'land', 'bund']

# Tabelle 1.3 derselben Bände kreuzt die Religion mit der Staatsangehörigkeit. Das ist
# die Spalte, die aus einer Konfessionsstatistik eine Aussage über Einwanderung macht:
# unter den Mitgliedern orthodoxer Kirchen sind in manchen Kreisen zwei von drei
# ausländische Staatsangehörige, unter den evangelischen einer von hundert.
STAAT = ['total', 'german', 'foreign', 'foreign_eu27', 'foreign_other_europe',
         'foreign_rest_of_world', 'foreign_unclear']
# Tabelle 1.5 kreuzt dieselben Religionsgesellschaften mit fünf Altersklassen. Sie
# beantwortet die zweite Hälfte der Einwanderungsfrage: eine Gemeinschaft, die durch
# Zuwanderung wächst, ist jung, eine, die durch Austritte und Sterbefälle schrumpft,
# ist alt. Beides steht hier nebeneinander.
ALTER = [('under_18', 'unter 18'), ('a18_29', '18 bis 29'), ('a30_49', '30 bis 49'),
         ('a50_64', '50 bis 64'), ('a65_plus', '65 und älter')]


def hole(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return r.read()


def lade_hefte(ziel: Path) -> list[Path]:
    """Die 48 Bände holen, soweit sie nicht schon liegen."""
    ziel.mkdir(parents=True, exist_ok=True)
    seite = hole(SERIE).decode('utf-8', 'replace')
    ids = sorted(set(re.findall(r'BWHeft_mods_(\d+)', seite)))
    pfade = []
    for i in ids:
        h = hole(HEFT.format(i)).decode('utf-8', 'replace')
        for rel in sorted(set(re.findall(
                r'MCRFileNodeServlet/(BWHeft_derivate_\d+/[^"]+?\.pdf)', h))):
            p = ziel / rel.split('/')[-1]
            if not p.exists():
                p.write_bytes(hole(DATEI.format(rel)))
                time.sleep(0.4)
            pfade.append(p)
        time.sleep(0.3)
    return pfade


def zahl(s: str) -> int | None:
    """Eine Zahl der Tabelle, oder None wo die Geheimhaltung sie weggenommen hat.

    "/" ist gesperrt. Klammern markieren einen Wert, der auf wenigen Fällen beruht;
    er bleibt ein Wert, bekommt aber unten ein Kennzeichen.
    """
    s = s.strip().strip('()').replace(' ', '').replace(' ', '')
    if not s or s == '/' or s == '-':
        return None
    return int(s.replace('.', ''))


def block(text: str) -> list[list[str]] | None:
    """Den Religionsblock einer Tabelle als Zeilen von Zellen.

    Die Überschrift steht auf einer eigenen Zeile; darunter folgen die sieben
    Kategorien, Name links, Zahlen rechts, durch mindestens zwei Leerzeichen getrennt.
    """
    marke = 'Religion (ausführlich)'
    i = text.find(marke)
    if i < 0:
        return None
    zeilen = []
    # In den schmalen Kreuztabellen bricht die letzte Beschriftung über drei Zeilen
    # um ("Keiner ö.-r." / "Religionsgesellschaft" / "zugehörig    94 420 …"). Eine
    # Zeile ohne Zahlen ist deshalb kein Tabellenende, sondern der Anfang eines
    # Namens — vorher brach das Auslesen genau dort ab und lieferte sechs Zeilen.
    offen = ''
    for roh in text[i + len(marke):].splitlines():
        if not roh.strip():
            if zeilen:
                break
            continue
        teile = re.split(r'\s{2,}', roh.strip())
        if len(teile) < 2:
            offen = (offen + ' ' + teile[0]).strip()
            continue
        if offen:
            teile[0] = (offen + ' ' + teile[0]).strip()
            offen = ''
        zeilen.append(teile)
        if len(zeilen) == len(KATEGORIEN):
            break
    return zeilen if len(zeilen) == len(KATEGORIEN) else None


def staatsblock(text: str) -> list[list[str]] | None:
    """Der Religionsblock aus Tabelle 1.3, Religion mal Staatsangehörigkeitsgruppe.

    Die Tabelle läuft über mehrere Seiten; der Religionsteil steht in der Fortsetzung.
    Gesucht wird deshalb ab der Fortsetzungsüberschrift, nicht ab der ersten Seite.
    """
    i = text.find('Noch: 1.3 Bevölkerung nach Staatsangehörigkeitsgruppen')
    if i < 0:
        i = text.find('1.3 Bevölkerung nach Staatsangehörigkeitsgruppen')
    return None if i < 0 else block(text[i:])


def altersblock(text: str) -> list[list[str]] | None:
    """Der Religionsblock aus Tabelle 1.5, Religion mal Altersklasse."""
    i = text.find('1.5 Bevölkerung nach Alter und weiteren demografischen')
    return None if i < 0 else block(text[i:])


def lies(pdf: Path) -> dict | None:
    text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'],
                          capture_output=True, text=True, check=True).stdout
    schluessel = re.search(r'Regionalschlüssel:\s*(\d+)', text)
    if not schluessel:
        return None
    # Die Kreisbände tragen einen fünfstelligen Schlüssel, die neun Stadtkreise einen
    # zwölfstelligen mit angehängten Nullen — dieselbe Ebene, andere Schreibweise. Die
    # vier Regierungsbezirksbände (dreistellig) gehören nicht in diese Tabelle, ihre
    # Werte stehen ohnehin als Spalte in jedem Kreisband.
    ags = schluessel.group(1)
    if len(ags) == 12 and ags.endswith('0000000'):
        ags = ags[:5]
    if len(ags) != 5:
        return None
    name = re.search(r'Zensus 9\. Mai 2011\s+(.+?)\s*\n', text)
    # Die Vergleichstabellen 4.1 (absolut) und 4.2 (Prozent) stellen Kreis,
    # Regierungsbezirk, Land und Bund nebeneinander; die Tabellen davor zeigen
    # nur den Kreis nach Geschlecht und werden hier nicht gebraucht.
    i41 = text.find('4.1 Bevölkerung nach regionaler Einheit')
    i42 = text.find('4.2 Bevölkerung nach regionaler Einheit')
    if i41 < 0 or i42 < 0:
        return None
    absolut = block(text[i41:i42])
    anteil = block(text[i42:])
    if absolut is None or anteil is None:
        return None
    zeile = {'ags': ags, 'name': (name.group(1).strip() if name else '').strip()}
    # Die Kreuztabelle ist eine Zugabe: fehlt sie in einem Band, soll das den
    # Hauptdatensatz nicht kosten. Sie wird dann als fehlend geführt.
    staat = staatsblock(text)
    for n, (feld, label) in enumerate(KATEGORIEN):
        werte = {}
        if staat is not None:
            zellen = staat[n]
            if not zellen[0].startswith(label[:18]):
                raise SystemExit(f'{pdf.name}: Staatsangehörigkeitstabelle erwartet '
                                 f'"{label}", gefunden "{zellen[0]}"')
            # Spalten: Anzahl, %, Deutschland, Ausland insgesamt, EU27,
            # Sonstiges Europa, Sonstige Welt.
            roh = zellen[1:]
            # Spalten der Quelle: Anzahl, %, Deutschland, Ausland insgesamt, EU27,
            # Sonstiges Europa, Sonstige Welt, Sonstige (ungeklärt, staatenlos, ohne
            # Angabe). Die letzte fehlte zuerst, und dann ergaben die drei
            # Herkunftsgruppen zusammen weniger als die Ausländerzahl daneben.
            if len(roh) >= 8:
                for schluessel, wert in zip(
                        STAAT, [roh[0], roh[2], roh[3], roh[4], roh[5], roh[6],
                                roh[7]]):
                    werte[schluessel] = zahl(wert)
        zeile.setdefault('staat', {})[feld] = werte
    alt_tab = altersblock(text)
    for n, (feld, label) in enumerate(KATEGORIEN):
        werte = {}
        if alt_tab is not None:
            zellen = alt_tab[n]
            if not zellen[0].startswith(label[:18]):
                raise SystemExit(f'{pdf.name}: Alterstabelle erwartet "{label}", '
                                 f'gefunden "{zellen[0]}"')
            # Spalten: Anzahl, %, dann die fünf Altersklassen.
            roh = zellen[1:]
            if len(roh) >= 7:
                werte['total'] = zahl(roh[0])
                for (schluessel, _), wert in zip(ALTER, roh[2:7]):
                    werte[schluessel] = zahl(wert)
        zeile.setdefault('alter', {})[feld] = werte
    for n, (feld, label) in enumerate(KATEGORIEN):
        for quelle, endung in ((absolut, ''), (anteil, '_pct')):
            zellen = quelle[n]
            if not zellen[0].startswith(label[:18]):
                raise SystemExit(f'{pdf.name}: erwartet "{label}", gefunden '
                                 f'"{zellen[0]}" — die Tabelle hat sich geändert')
            werte = zellen[1:1 + len(SPALTEN)]
            if len(werte) != len(SPALTEN):
                raise SystemExit(f'{pdf.name}: {label} hat {len(werte)} statt '
                                 f'{len(SPALTEN)} Spalten')
            for spalte, w in zip(SPALTEN, werte):
                if endung:
                    w = w.strip().strip('()').replace(',', '.')
                    zeile[f'{spalte}_{feld}_pct'] = (
                        None if w in ('/', '-', '') else float(w))
                else:
                    zeile[f'{spalte}_{feld}'] = zahl(w)
    return zeile


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdf-dir', type=Path,
                    default=Path.home() / '.cache/bw-datenatlas/zensus2011-bw')
    ap.add_argument('--laden', action='store_true', help='fehlende Bände holen')
    ap.add_argument('--csv', type=Path,
                    default=ROOT / 'inputs/zensus2011-religion-kreise.csv')
    ap.add_argument('--out', type=Path,
                    default=ROOT / 'docs/data/zensus2011-religion.json')
    args = ap.parse_args()

    if args.laden or not args.pdf_dir.is_dir():
        lade_hefte(args.pdf_dir)
    pdfs = sorted(args.pdf_dir.glob('*.pdf'))
    if not pdfs:
        raise SystemExit(f'Keine Bände in {args.pdf_dir} — einmal mit --laden aufrufen')

    kreise = [z for z in (lies(p) for p in pdfs) if z]
    kreise.sort(key=lambda z: z['ags'])
    if len(kreise) != 44:
        raise SystemExit(f'{len(kreise)} Kreisbände gelesen, erwartet sind 44')

    # Land- und Bundesspalte stehen in jedem Band; sie müssen überall gleich sein.
    for feld, _ in KATEGORIEN:
        for spalte in ('land', 'bund'):
            werte = {z[f'{spalte}_{feld}'] for z in kreise}
            if len(werte) != 1:
                raise SystemExit(f'{spalte}/{feld}: {len(werte)} verschiedene Werte in '
                                 f'44 Bänden — die Auslesung stimmt nicht')

    # Die Kreuztabelle gibt es nur je Kreis, kein Landeswert steht in den Bänden.
    # Er wird deshalb aufsummiert — und weil die Geheimhaltung einzelne Zellen
    # wegnimmt, wird mitgezählt, wie viele Kreise je Zelle fehlen. Ohne diese Zahl
    # sähe eine untererfasste Summe aus wie eine vollständige.
    staat_land = {}
    for feld, _ in KATEGORIEN:
        eintrag = {}
        for schluessel in STAAT:
            werte = [z['staat'][feld].get(schluessel) for z in kreise]
            eintrag[schluessel] = sum(w for w in werte if w is not None)
            eintrag[schluessel + '_districts_suppressed'] = sum(
                1 for w in werte if w is None)
        staat_land[feld] = eintrag

    alter_land = {}
    for feld, _ in KATEGORIEN:
        eintrag = {}
        for schluessel in ['total'] + [k for k, _ in ALTER]:
            werte = [z['alter'][feld].get(schluessel) for z in kreise]
            eintrag[schluessel] = sum(w for w in werte if w is not None)
            eintrag[schluessel + '_districts_suppressed'] = sum(
                1 for w in werte if w is None)
        # Die Geheimhaltung trifft die Altersklassen ungleich: bei den orthodoxen
        # Kirchen fehlt „65 und älter" in 23 von 44 Kreisen, „30 bis 49" in keinem.
        # Eine Summe daraus machte die Gemeinschaft jünger, als belegt ist. Statt
        # eines Punktwerts steht deshalb eine Spanne da: unten der gezählte Anteil,
        # oben der Fall, dass alle nicht zugeordneten Personen in diese Klasse
        # fielen. Die Aussage der Grafik muss auch am oberen Rand noch stimmen.
        zugeordnet = sum(eintrag[k] for k, _ in ALTER)
        eintrag['assigned'] = zugeordnet
        eintrag['unassigned'] = max(0, eintrag['total'] - zugeordnet)
        for k, _ in ALTER:
            eintrag[k + '_pct_low'] = (round(100 * eintrag[k] / eintrag['total'], 1)
                                       if eintrag['total'] else None)
            eintrag[k + '_pct_high'] = (
                round(100 * (eintrag[k] + eintrag['unassigned']) / eintrag['total'], 1)
                if eintrag['total'] else None)
        alter_land[feld] = eintrag

    referenz = kreise[0]
    land = {feld: referenz[f'land_{feld}'] for feld, _ in KATEGORIEN}
    bund = {feld: referenz[f'bund_{feld}'] for feld, _ in KATEGORIEN}

    with args.csv.open('w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['ags', 'name'] + [f for f, _ in KATEGORIEN]
                   + [f + '_pct' for f, _ in KATEGORIEN])
        for z in kreise:
            w.writerow([z['ags'], z['name']]
                       + [z[f'kreis_{f}'] for f, _ in KATEGORIEN]
                       + [z[f'kreis_{f}_pct'] for f, _ in KATEGORIEN])

    doc = {
        'type': 'zensus2011_religion_detailed',
        'schema_version': '1.0',
        'what_this_is': (
            'Zugehörigkeit zu einer Religionsgesellschaft des öffentlichen Rechts je '
            'Kreis, Zensus 2011 — und anders als 2022 einzeln ausgewiesen: neben den '
            'beiden großen Kirchen auch evangelische Freikirchen, orthodoxe Kirchen und '
            'jüdische Gemeinden.'),
        'why_2011_and_not_2022': (
            'Der Zensus 2022 kennt bei der Religion nur noch drei Kategorien: '
            'römisch-katholisch, evangelisch und eine einzige Restkategorie. Die '
            'orthodoxen Kirchen sind dort nicht mehr zu sehen. Diese Auszählung von 2011 '
            'ist deshalb die letzte Zählung, die es für sie gibt.'),
        'membership_not_belief': (
            'Gezählt ist die eingetragene Mitgliedschaft in einer Körperschaft des '
            'öffentlichen Rechts, nicht das Bekenntnis. Welche orthodoxe Kirche diesen '
            'Status hat, ist von Kirche zu Kirche und von Land zu Land verschieden; wer '
            'sich orthodox versteht, ohne in einem solchen Register zu stehen, ist hier '
            'nicht gezählt. Die Zahl ist damit eine Untergrenze.'),
        'fifteen_years_old': (
            'Stichtag ist der 9. Mai 2011. Seither sind Menschen aus Rumänien, Bulgarien, '
            'Syrien, dem Irak und der Ukraine zugewandert, also aus Ländern mit großen '
            'orthodoxen und orientalisch-orthodoxen Bevölkerungen. Für die Gegenwart ist '
            'die Zahl zu niedrig, und um wie viel, sagt sie nicht.'),
        'muslims_are_not_a_category_here': (
            'Musliminnen und Muslime erscheinen in dieser Tabelle nicht. Keine '
            'islamische Gemeinschaft hat in Baden-Württemberg den Status einer '
            'Körperschaft des öffentlichen Rechts, sie fallen daher unter „Keiner '
            'ö.-r. Religionsgesellschaft zugehörig" — zusammen mit allen '
            'Konfessionslosen. Auch diese Kategorie ist also keine Zahl über '
            'Religionslosigkeit.'),
        'secrecy': ('Gesperrte Werte ("/") stehen als fehlend und werden nicht '
                    'geschätzt. Betroffen sind vor allem die jüdischen Gemeinden in '
                    'kleinen Kreisen.'),
        'reference_period': '2011-05-09',
        'source': ('Statistisches Landesamt Baden-Württemberg, Zensus 2011 — '
                   'Bevölkerung und Haushalte am 9. Mai 2011, Kreisbände, '
                   'Tabellen 4.1 und 4.2'),
        'source_url': SERIE,
        'attribution': '© Statistisches Landesamt Baden-Württemberg',
        'categories': {f: l for f, l in KATEGORIEN},
        'state_total': land,
        'by_citizenship': staat_land,
        'by_age': alter_land,
        'age_columns': {k: l for k, l in ALTER},
        'what_age_shows': (
            'Tabelle 1.5 derselben Bände kreuzt die Religionsgesellschaft mit fünf '
            'Altersklassen. Eine Gemeinschaft, die durch Zuwanderung wächst, ist jung; '
            'eine, die durch Austritte und Sterbefälle schrumpft, ist alt. Auch hier '
            'sind die Landeswerte Summen der 44 Kreise, und gesperrte Zellen fehlen '
            'darin. Weil die Sperren die Altersklassen ungleich treffen, steht '
            'statt eines Punktwerts eine Spanne: unten der gezählte Anteil, oben '
            'der Fall, dass alle nicht zugeordneten Personen in diese Klasse '
            'fielen.'),
        'citizenship_columns': {
            'total': 'Insgesamt', 'german': 'Deutschland',
            'foreign': 'Ausland insgesamt', 'foreign_eu27': 'EU27-Land',
            'foreign_other_europe': 'Sonstiges Europa',
            'foreign_rest_of_world': 'Sonstige Welt',
            'foreign_unclear': 'Sonstige, ungeklärt oder ohne Angabe'},
        'what_citizenship_shows': (
            'Tabelle 1.3 derselben Bände kreuzt die Religionsgesellschaft mit der '
            'Staatsangehörigkeit. Erst das macht aus einer Konfessionszählung eine '
            'Aussage über Einwanderung: unter den Mitgliedern orthodoxer Kirchen war '
            '2011 ein großer Teil ausländische Staatsangehörige, unter den '
            'evangelischen fast niemand. Gemeint ist der Pass, nicht die Herkunft — '
            'Eingebürgerte und hier Geborene mit deutschem Pass zählen als deutsch, '
            'der Anteil der Eingewanderten ist also höher als der hier gezeigte.'),
        'citizenship_sums_are_district_sums': (
            'Für die Kreuztabelle nennen die Bände keinen Landeswert; er ist hier die '
            'Summe der 44 Kreise. Wo die Geheimhaltung eine Zelle genommen hat, fehlt '
            'sie in der Summe, und wie viele Kreise das je Zelle betrifft, steht '
            'daneben. Die Summen sind damit Untergrenzen.'),
        'germany_total': bund,
        'count': len(kreise),
        'districts': [
            {'ags': z['ags'], 'name': z['name'],
             **{f: z[f'kreis_{f}'] for f, _ in KATEGORIEN},
             **{f + '_pct': z[f'kreis_{f}_pct'] for f, _ in KATEGORIEN},
             'by_citizenship': z['staat'], 'by_age': z['alter']}
            for z in kreise],
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('zensus2011-religion-data.js').write_text(
        'window.ATLAS_ZENSUS2011_RELIGION=' + json.dumps(
            doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')

    print(f"{len(kreise)} Kreise gelesen. Baden-Württemberg 2011:")
    for feld, label in KATEGORIEN:
        print(f'  {label:46s} {land[feld]:>10,}'.replace(',', '.'))
    print('  Ausländische Staatsangehörige je Religionsgesellschaft (Kreissummen):')
    for feld, label in KATEGORIEN:
        e = staat_land[feld]
        if not e['total']:
            continue
        print(f"    {label:46s} {100 * e['foreign'] / e['total']:5.1f} %"
              f"  ({e['foreign']:>9,} von {e['total']:>10,})".replace(',', '.')
              + (f"  · {e['foreign_districts_suppressed']} Kreise gesperrt"
                 if e['foreign_districts_suppressed'] else ''))
    print('  Altersaufbau (Kreissummen, Anteil 65 und älter / unter 18):')
    for feld, label in KATEGORIEN:
        e = alter_land[feld]
        n = sum(e[k] for k, _ in ALTER)
        if not n:
            continue
        gesperrt = max(e[k + '_districts_suppressed'] for k, _ in ALTER)
        print(f"    {label:46s} {100 * e['a65_plus'] / n:5.1f} % / "
              f"{100 * e['under_18'] / n:5.1f} %"
              + (f'  · bis zu {gesperrt} Kreise gesperrt' if gesperrt else ''))
    oben = sorted(kreise, key=lambda z: z['kreis_orthodox_pct'] or 0, reverse=True)[:5]
    print('  Höchste orthodoxe Anteile: '
          + ', '.join(f"{z['name']} {z['kreis_orthodox_pct']} %" for z in oben))


if __name__ == '__main__':
    main()
