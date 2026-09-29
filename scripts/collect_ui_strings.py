#!/usr/bin/env python3
"""Sammelt die übersetzbaren Texte der Seite ein — mit dem Code der Seite selbst.

Die Auswahl, welche Elemente übersetzt werden, steht in docs/assets/i18n.js. Sie hier
ein zweites Mal zu beschreiben hieße, zwei Fassungen derselben Regel zu pflegen, und
die laufen auseinander. Stattdessen wird die Seite geladen und I18N.sammle() gefragt.

    python scripts/collect_ui_strings.py            # nach docs/assets/i18n/de.json
    python scripts/collect_ui_strings.py --pruefen  # meldet nur, was fehlt
"""
from __future__ import annotations
import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sammeln(port: int) -> list[str]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = b.new_context(viewport={'width': 1440, 'height': 1000},
                             locale='de-DE').new_page()
        # Ausdrücklich auf Deutsch: sonst richtet sich die Seite nach der Sprache
        # des Browsers, und der Sammler trüge die englische Fassung als deutschen
        # Schlüssel ein — der Katalog übersetzte dann Englisch nach Englisch.
        page.goto(f'http://127.0.0.1:{port}/?lang=de', wait_until='load')
        # Auf die Karte warten, nicht auf die Uhr: die Geometriedatei ist drei
        # Megabyte groß, und vor ihr gibt es keine Kartenhinweise einzusammeln.
        try:
            page.wait_for_selector('#map-features path', timeout=30000)
        except Exception:
            print('  Warnung: keine Kartenflächen — Kartenhinweise fehlen im Katalog')
        page.wait_for_timeout(1200)
        # Die Seite einmal durchspielen: jede Kartenebene, jede Kennzahl, jede
        # aufklappbare Tabelle. Was das Programm dabei durch t() schickt, merkt sich
        # I18N — anders wären Tabellenköpfe und Fußnoten nie vollständig zu fassen,
        # weil immer nur eine Ebene gleichzeitig gezeichnet ist.
        page.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)")
        page.wait_for_timeout(400)
        # Auch das Auswahlfeld der Befragungen: dort wird immer nur ein Block
        # gezeichnet, und die Beschriftungen der übrigen laufen sonst nie durch t().
        for wahl, feld in (('#layer', 'layer'), ('#survey-select', 'survey'),
                           ('#azr-indicator', 'azr'),
                           ('#origin-scope', 'origin'), ('#flow-area-scope', 'flow'),
                           ('#flow-range', 'range'), ('#filter-source', 'quelle')):
            try:
                werte = page.eval_on_selector_all(f'{wahl} option', 'e=>e.map(o=>o.value)')
            except Exception:
                continue
            for w in werte:
                try:
                    page.select_option(wahl, w)
                    page.wait_for_timeout(120)
                except Exception:
                    pass
        for haken in ('#composition-detail', '#all-origins', '#only-landtag'):
            for zustand in (True, False):
                try:
                    page.set_checked(haken, zustand)
                    page.wait_for_timeout(120)
                except Exception:
                    pass
        # Auch etwas auswählen: das Gebietsprofil wird erst beim Anklicken gezeichnet,
        # und seine Sätze laufen erst dann durch t(). Ohne diesen Schritt fehlen sie im
        # Katalog, und die Übersetzung fällt später still auf Deutsch zurück.
        # Jede Ebene mit eigenem Profil muss dabei sein. Die Bundesländer-Ebene
        # fehlte zuerst, und damit fehlten ihre sechs Profilsätze im Katalog.
        for ebene in ('region_population', 'eu_foreign_born', 'de_muslim_share',
                      'muni_catholic', 'grid_foreign_share',
                      'district_population'):
            try:
                page.select_option('#layer', ebene)
                page.wait_for_timeout(500)
                page.locator('#map-features path.map-feature').first.click()
                page.wait_for_timeout(400)
            except Exception:
                pass
        # Baden-Württemberg auf der Unterrichtsebene: nur dort erscheint der Hinweis,
        # dass der Nenner nicht erfasst ist.
        try:
            page.select_option('#layer', 'de_religious_education')
            page.wait_for_timeout(500)
            page.locator('#map-features path[data-id="DE08"]').dispatch_event('click')
            page.wait_for_timeout(400)
        except Exception:
            pass
        try:
            page.select_option('#layer', 'de_muslim_share')
            page.wait_for_timeout(500)
            # dispatch_event statt click: die Fläche kann teilweise verdeckt
            # sein, und geprüft wird hier der Textfluss, nicht die Trefferfläche.
            page.locator('#map-features path[data-id="DE04+DE02"]').dispatch_event('click')
            page.wait_for_timeout(400)
        except Exception:
            pass
        page.wait_for_timeout(400)
        texte = page.evaluate('()=>Object.keys(I18N.sammle()).concat(I18N.gesehen())')
        b.close()
    return texte


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', type=int, default=8177)
    ap.add_argument('--pruefen', action='store_true')
    args = ap.parse_args()

    server = subprocess.Popen(
        ['python3', '-m', 'http.server', str(args.port), '--directory', str(ROOT / 'docs')],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(2)
        texte = sorted(sammeln(args.port))
    finally:
        server.terminate()

    # Die Anzeigetexte der Kartenebenen stehen in app.js und nicht im HTML; die
    # Seite zeigt immer nur die gerade gewählte Ebene, also wären sie beim Einsammeln
    # aus dem Dokument nie vollständig.
    import re as _re
    quelle = (ROOT / 'docs/assets/app.js').read_text(encoding='utf-8')
    for feld in ('title', 'badge', 'date', 'note', 'limitation'):
        for m in _re.finditer(feld + r":'((?:[^'\\]|\\.){4,}?)'", quelle):
            wert = m.group(1).replace("\\'", "'")
            if _re.search(r'[A-Za-zÄÖÜäöüß]', wert):
                texte.append(wert)
    texte.append('Nicht verfügbar')
    # Eine Jahreszahl ist in jeder Sprache dieselbe.
    texte = sorted({x for x in set(texte)
                    if not _re.fullmatch(r'[\d\s.,%·–-]+', x)})

    ziel = ROOT / 'docs/assets/i18n/de.json'
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(texte, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(texte)} Texte, {sum(len(t) for t in texte)} Zeichen -> {ziel.name}')

    fehlt_gesamt = 0
    for sprache in ('en', 'fr'):
        pfad = ROOT / f'docs/assets/i18n/{sprache}.json'
        vorhanden = json.loads(pfad.read_text(encoding='utf-8')) if pfad.is_file() else {}
        fehlt = [t for t in texte if not vorhanden.get(t)]
        ueberzaehlig = [t for t in vorhanden if t not in texte]
        fehlt_gesamt += len(fehlt)
        print(f'  {sprache}: {len(texte)-len(fehlt)} übersetzt, {len(fehlt)} offen, '
              f'{len(ueberzaehlig)} veraltet')
        for t in fehlt[:3]:
            print(f'      offen: {t[:80]}')
    if args.pruefen and fehlt_gesamt:
        raise SystemExit(f'{fehlt_gesamt} Texte ohne Übersetzung')


if __name__ == '__main__':
    main()
