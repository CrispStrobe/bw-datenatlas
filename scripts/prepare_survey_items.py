#!/usr/bin/env python3
"""„Was gefragt wurde" — Befragungsergebnisse, streng getrennt von allen Zählungen.

Dieser Atlas zählt und schätzt Menschen. Dies hier ist etwas anderes: Antworten auf
Fragen. Beides in einem Abschnitt zu zeigen wäre der schwerste Fehler, den er machen
könnte, denn eine Prozentzahl sieht wie die andere aus, und niemand sieht einem
Balken an, ob dahinter ein Register steht oder ein Fragebogen.

Deshalb ein eigener Abschnitt, eine eigene Überschrift und an jeder Zeile vier
Angaben, die bei Zählungen weniger wiegen und hier alles entscheiden:

  Grundgesamtheit   wer überhaupt gefragt wurde — 88,6 Prozent WOVON?
  Fallzahl          bei Untergruppen oft klein; 603 Befragte sind nicht 5.000
  Erhebungszeitraum nicht das Erscheinungsjahr; dazwischen liegen oft zwei Jahre
  Fundstelle        Abbildung und Seite, damit jede Zahl nachzuschlagen ist

Wo die Quelle die Fragennummern nennt, stehen auch die. Bei Einstellungsfragen hängt
das Ergebnis am Wortlaut, und wer den Wortlaut nachlesen will, muss die Frage finden
können.

Keine Karte, keine Kartenebene, keine Verrechnung mit Bevölkerungszahlen. Diese
Zahlen gehen in keine Modellrechnung dieses Atlas ein.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
try:
    from .export_rights import export_rights, source_rights
except ImportError:
    from export_rights import export_rights, source_rights

ROOT = Path(__file__).resolve().parents[1]

# Der Atlas handelt von Baden-Württemberg; die weiter gefassten Erhebungen stehen
# daneben, nicht davor.
RAUM_RANG = {'Baden-Württemberg': 0, 'Deutschland': 1,
             'Sechs europäische Länder': 2, 'Mehrere Länder': 3}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=ROOT / 'inputs/befragungsitems.csv')
    ap.add_argument('--evs-input', type=Path, default=ROOT / 'inputs/evs-items.csv')
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/data/survey-items.json')
    args = ap.parse_args()

    bloecke: dict[str, dict] = {}
    rows = []
    for path in (args.input, args.evs_input):
        with path.open(encoding='utf-8') as fh:
            rows.extend(csv.DictReader(fh))
    for r in rows:
        b = bloecke.setdefault(r['block'], {
            'block': r['block'], 'title': r['block_title'],
            # Was für den ganzen Block gilt und nicht an eine Zeile gehört: der
            # Wortlaut der Fragen und das, was die Stichprobe nicht hergibt. Die
            # Kopfzeile eines Blocks stammt aus seiner ersten Zeile; wo die Balken
            # verschiedene Grundgesamtheiten haben, reicht das nicht.
            'note': r.get('block_note') or None,
            # Über welches Gebiet der Block spricht. Bei zehn Blöcken sieht
            # man das dem Titel nicht mehr an, und ein Wert aus sechs
            # Ländern liest sich sonst wie einer über dieses Land.
            'scope': r.get('scope') or None, 'items': []})
        b['items'].append({
            'label': r['label'],
            # Die Skala im Einzelnen. Ein Balken, der die beiden zustimmenden
            # Kategorien addiert, ist die Rechnung, die auch die Quelle im Text
            # macht — aber die vier Stufen gehören daneben, sonst verschwindet
            # der Unterschied zwischen "voll und ganz" und "eher zu".
            'detail': r.get('detail') or None,
            'value': float(r['value']),
            'unit': r['unit'],
            'study': r['study'],
            'population': r['population'],
            'base_n': int(r['base_n']) if r['base_n'] else None,
            'field_period': r['field_period'],
            'question_ref': r['question_ref'] or None,
            'source_title': r['source_title'],
            'source_url': r['source_url'],
            'source_locator': r['source_locator'] or None,
            'source_rights': source_rights(),
            **({'weighted_valid_n': float(r['weighted_valid_n'])}
               if r.get('weighted_valid_n') else {}),
            **({'valid_n': int(r['valid_n'])} if r.get('valid_n') else {}),
            **({'source_kind': r['source_kind']} if r.get('source_kind') else {}),
        })

    chart_path = ROOT / 'inputs/survey-charts.json'
    charts = json.loads(chart_path.read_text(encoding='utf-8'))
    def prepare_chart(key, chart):
        if key not in bloecke:
            raise ValueError(f'Unknown chart block: {key}')
        for related in chart.get('related', []):
            if related not in bloecke:
                raise ValueError(f'Unknown related block: {related}')
        for row in chart.get('rows', []):
            if chart['kind'] == 'distribution' and 'items' in row:
                indices = range(len(bloecke[key]['items'])) if row['items'] == 'all' else row['items']
                row['segments'] = [
                    {'label': bloecke[key]['items'][i]['label'].split(': ', 1)[-1],
                     'value': bloecke[key]['items'][i]['value']} for i in indices]
        if chart.get('main_chart'):
            prepare_chart(key, chart['main_chart'])
    for key, chart in charts.items():
        prepare_chart(key, chart)
        bloecke[key]['chart'] = chart
    # These detail strings encode explicitly published categories. Preserve them
    # as structured segments; never infer unreported answers from agreement.
    import re
    for b in bloecke.values():
        for item in b['items']:
            detail = item.get('detail') or ''
            parts = []
            complete = False
            if b['block'] == 'bw_kopftuch_2012':
                parts = [('Stört mich', item['value'])]
                match = re.fullmatch(r'stört mich nicht (\d+)', detail)
                if match:
                    parts.append(('Stört mich nicht', float(match[1])))
                    complete = True
            elif detail.startswith('Zustimmung:') and 'Ablehnung:' in detail:
                parts = [(label.strip(), float(value)) for value, label in
                         re.findall(r'(\d+(?:[.,]\d+)?) % ([^+;]+)', detail)]
                complete = True
            elif b['block'] == 'bw_religioese_vielfalt':
                parts = [(label.strip(), float(value)) for label, value in
                         re.findall(r'([^·]+?) (\d+)\s*(?:·|$)', detail)]
                complete = True
            elif re.match(r'^(Eher hilfreich|Arbeitslos|Sehr wichtig|Eher zustimmend):', detail):
                parts = [(label.strip(), float(value.replace(',', '.'))) for label, value in
                         re.findall(r'([^;]+): (\d+(?:[.,]\d+)?) %', detail)]
            if detail.startswith('Arbeitslos:'):
                complete = True
            if parts:
                item['response_distribution_complete'] = complete
                item['response_distribution'] = [{'label': label, 'value': value} for label, value in parts]

    doc = {
        'type': 'survey_items',
        'schema_version': '1.2',
        'rights': export_rights(),
        'what_this_is': ('Antworten auf Fragen, nicht gezählte Menschen. Ein eigener '
                         'Abschnitt, weil eine Prozentzahl wie die andere aussieht und '
                         'niemand einem Balken ansieht, ob dahinter ein Register steht '
                         'oder ein Fragebogen.'),
        'why_the_metadata_matters': (
            'Bei Befragungen entscheidet über das Ergebnis, wer gefragt wurde, wie viele '
            'es waren und wie die Frage lautete. An jeder Zeile stehen deshalb '
            'Grundgesamtheit, Fallzahl, Erhebungszeitraum und Fundstelle — und wo die '
            'Quelle sie nennt, auch die Fragennummern.'),
        'why_2012_and_2019_are_not_a_trend': (
            'Die beiden Landesumfragen von 2012 und 2019 haben verschiedene '
            'Grundgesamtheiten: 2012 wurden Deutsche ab 18 Jahren befragt, also '
            'Wahlberechtigte, 2019 deutschsprechende Personen ab 18 Jahren. Wer die '
            'Werte als Entwicklung liest, vergleicht auch zwei verschieden '
            'abgegrenzte Bevölkerungen. Der Landesbericht weist selbst darauf hin.'),
        'not_in_any_model': ('Diese Zahlen gehen in keine Modellrechnung dieses Atlas '
                             'ein und werden mit keiner Bevölkerungszahl verrechnet.'),
        'count': sum(len(b['items']) for b in bloecke.values()),
        # Der Block mit Landesbezug zuerst: dies ist ein Atlas über
        # Baden-Württemberg, und die bundesweiten Werte stehen daneben, nicht davor.
        'scope_order': ['Baden-Württemberg', 'Deutschland',
                        'Sechs europäische Länder', 'Mehrere Länder'],
        'blocks': sorted(bloecke.values(),
                         key=lambda b: (RAUM_RANG.get(b['scope'], 9), b['title'])),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    args.out.with_name('survey-items-data.js').write_text(
        'window.ATLAS_SURVEY_ITEMS=' + json.dumps(doc, ensure_ascii=False,
                                                  separators=(',', ':')) + ';\n',
        encoding='utf-8')
    print(f"{doc['count']} Befragungswerte in {len(bloecke)} Blöcken:")
    for b in doc['blocks']:
        n = {i['base_n'] for i in b['items'] if i['base_n']}
        print(f"  {b['title'][:52]:52s} {len(b['items']):2d} Zeilen · "
              f"n={', '.join(str(x) for x in sorted(n)) or 'nicht angegeben'}")


if __name__ == '__main__':
    main()
