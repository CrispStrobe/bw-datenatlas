# BW-Datenatlas: muslimische Bevölkerung und demografische Grundlagen

**Statisches GitHub-Pages-Projekt · zusammengestellt am 25.09.2026**

Interaktive Kartenansichten, Herkunftsdiagramme, Datenexplorer, Quellenprüfung und CSV-/JSON-/SVG-Exporte. HTML, CSS und JavaScript ohne Frontend-Framework, ohne API-Schlüssel, ohne Kartenkachelserver und ohne externe Browserbibliotheken. Die Benutzeroberfläche ist deutsch und für Desktop und Smartphone angelegt.

## Status der Auslieferung

**Veröffentlicht und geprüft.** Das Repository ist öffentlich, die amtlichen BKG-Geometrien werden beim Aufbau bezogen und verarbeitet, und die Seite läuft auf zwei Hosts:

- Vercel: https://bw-datenatlas.vercel.app
- GitHub Pages: https://crispstrobe.github.io/bw-datenatlas/

Der GitHub-Workflow baut jede abgeleitete Datei aus den Originalquellen neu auf — BKG-Archiv, amtlicher Ausländerbericht, Zensus-Gitter — und bricht ab, wenn eine Modelldatei nicht byteidentisch reproduziert wird. 44 von 44 Kreisen und 1.101 von 1.101 Gemeinden sind den amtlichen Geometrien zugeordnet, ohne offene Fälle.

## Zwei Repositories

Dieses Repository veröffentlicht den Atlas. Die Modellrechnung, die amtlichen Geometrien
und die Zensus-Auswertungen liegen vollständig hier und werden bei jedem Push neu gebaut
und gegen das Eingecheckte geprüft.

Das Einrichtungsverzeichnis steht **auf Ortsebene**: welche Einrichtung es gibt, in
welcher Gemeinde, in welchem Verband, mit welchen Belegen — ohne Straße. Die
Straßenanschriften, die Prüfskripte und die Verbandsverzeichnisse liegen in einem
getrennten, nicht öffentlichen Repository, das den Auszug für dieses hier erzeugt.

Der Grund ist nicht die Lizenz — das Verzeichnis bleibt ODbL, weil OpenStreetMap darin
steckt — sondern was eine einzelne Datei leicht macht. Sechshundert Impressen und eine
gepflegte Landesliste sind verschiedene Gegenstände, und es ist der zweite, dessen
Veröffentlichung der Zentralrat der Muslime mit Verweis auf Sicherheitsgründe eingestellt
hat; das Bundeskriminalamt zählte für 2025 vorläufig 53 Angriffe auf Moscheen
(Bundestags-Drucksachen 21/5917, 21/2705). Dieser Atlas zeigt deshalb, wo es Gemeinden
gibt, und verlinkt für alles Weitere die Quelle.

Was das kostet, steht dazu: Die Ortsebenen-Datei ist für dieses Repository eine
**Eingabe**, keine Ableitung. Alles, was darauf aufbaut, wird weiterhin byteidentisch
nachgebaut und geprüft; die Datei selbst kann die CI hier nicht neu herleiten.

## Was der Atlas zeigt und was er nicht zeigt

Der BAMF-Forschungsbericht 55 nennt für BW 2025 **1.133.000–1.197.000** muslimische Religionsangehörige einschließlich Alevitinnen und Aleviten; Abbildung 4 nennt **10,1–10,7 %**. Bezugsbevölkerung sind private Hauptwohnsitzhaushalte des Mikrozensus. Der Bericht stellt ausdrücklich fest, dass differenzierte Analysen *innerhalb* der Bundesländer aus den MLD-Daten nicht möglich sind.

**Es gibt daher keine erhobene muslimische Bevölkerungsverteilung auf 44 Kreise oder 1.101 Gemeinden.** Der Atlas rechnet stattdessen eine offengelegte Modellverteilung: die veröffentlichte Landessumme wird nach Herkunft verteilt und trägt überall eine Spanne. Sie erfindet keine Summe, und sie ist keine Messung der Religionszugehörigkeit.

Ebenso bleibt Tabelle 2 des BAMF-Berichts eine Herkunftsstatistik für **Deutschland**, nicht für BW. Keine deutsche Herkunftsquote wird unbemerkt auf BW oder einen Kreis übertragen.

## Enthaltene Ansichten

| Kartenebene | Gebiet und Bezug | Aussage |
|---|---|---|
| Muslimische Bevölkerung · Landeswert | BW gesamt, 2025 | Veröffentlichte Landes-Spanne; eine einheitliche Fläche bedeutet keine gleichen Kreisanteile. |
| **Modell je Kreis** | 44 Kreise | Verteilte Landessumme nach Herkunft, mit Spanne und zwei wählbaren Varianten. |
| **Modell je Gemeinde** | 1.101 Gemeinden | Verteilung des Kreiswerts, breitere Spannen, gegen die Zensus-Obergrenze geprüft. |
| Ausländische Staatsangehörige | 44 Kreise, 30.11.2024 | Anteil aus gleichzeitigen amtlichen Beständen; im Profil die Zusammensetzung nach 25 Staatsangehörigkeiten. |
| Einwohnerzahl | 44 Kreise, 30.11.2024 | Absolute Bevölkerung, keine Dichte. |
| Einwohnerzahl | 1.101 Gemeinden, 30.06.2024 | Gesamt, männlich und weiblich. |
| Erwerbstätige mit Migrationshintergrund | 44 Kreise, Mikrozensus 2024 | Anteil an der Bevölkerung ab 15; keine Erwerbslosenquote, da die Quelle sie geheim hält. |
| Unter 25-Jährige mit Migrationshintergrund | 44 Kreise, Mikrozensus 2024 | Altersgliederung; schraffiert, wo zu viele Altersgruppen geheim gehalten sind. |
| Zweite Generation mit deutschem Pass | 44 Kreise, Mikrozensus 2024 | Der Teil der Bevölkerung, den die Ausländerstatistik nicht sieht. |
| Veränderung Migrationshintergrund | 44 Kreise, 2021–2025 | Entwicklung in Prozentpunkten; das Religionsmodell wird nicht rückgerechnet. |
| Ausländische Staatsangehörige · Gemeindeanteil | 1.101 Gemeinden, 2025 | Gemessen, nicht modelliert — die einzige direkt erhobene Größe, die neben der Modellrechnung auf derselben Ebene steht. |
| Aus den Anwerbestaaten | 44 Kreise, AZR 31.12.2025 | Anteil **an der ausländischen Bevölkerung des Kreises**, nicht an seinen Einwohnern. |
| Türkische Staatsangehörige | 44 Kreise, AZR 31.12.2025 | Ebenso ein Anteil an den Ausländern; Eingebürgerte haben einen deutschen Pass und fehlen. |
| Seit 25 Jahren oder länger hier | 44 Kreise, AZR 31.12.2025 | Verweildauer der ausländischen Bevölkerung; Bundesmedian als Strich im Balken. |
| Islamische und alevitische Einrichtungen | Ortsebene, 1.101 Gemeinden | Punkt in der Ortsmitte, kein Gebäude; jeder Eintrag verlinkt seinen Beleg. |

Dazu Herkunftsdiagramme für Deutschland und BW, ein Datenexplorer mit allen 6.367
Beobachtungen aus 40 Datensätzen, Gebietstabellen sowie CSV-, JSON- und SVG-Exporte.

Seit September 2026 außerdem, alles amtlich und quellenverlinkt: Wanderungsbewegung 2023
nach Kreisen, Herkunfts- und Zielgebieten und Altersgruppen aus dem Bericht A III 1-j;
Zu- und Fortzüge des Landes seit 1995; durchschnittliche Aufenthaltsdauer nach
Staatsangehörigkeit; Einbürgerungen seit 2000; und die Kennzahlen des
Ausländerzentralregisters je Kreis.

**Warum die Modellrechnung nicht auf neuere Registerdaten wechselt.** Der Landesbericht
A I 4-j nennt 25 Staatsangehörigkeiten je Kreis, darunter Kosovo, Bosnien-Herzegowina,
Afghanistan, Irak und Nordmazedonien. Die frei herunterladbaren Alternativen nennen
weniger: die Kartendatei des Bundes fünf, der nationale Jahresbericht die fünf größten je
Kreis, und die GENESIS-Tabellen des Landes kennen überhaupt keine Kreisgliederung. Die
vollständige Tabelle (GENESIS 12521-0041, rund 215 Staatsangehörigkeiten je Kreis)
existiert, ihr direkter CSV-Abruf ist aber zurückgezogen. Ein Wechsel würde das Modell
also vergröbern, nicht verfeinern. Geprüft wird es trotzdem: 220 Vergleiche über 44
Kreise und fünf Länder gegen das Bundesregister, alle innerhalb der Toleranz, die ein
Jahr Abstand zwischen den Stichtagen zulässt.

Die neuesten Religionsmodellwerte beziehen sich auf **2025**. Der Projektstand 2026 ist kein neues Religionsmessjahr.

## Auf GitHub Pages veröffentlichen

1. Den **Inhalt dieses Ordners**, einschließlich `.github/workflows/pages.yml`, in ein neues GitHub-Repository übernehmen. Standardbranch: `main`. Ein öffentliches Repository ist die unkomplizierte Variante. Nicht nur `docs/` hochladen: Der Workflow braucht auch `inputs/`, `scripts/` und `tests/`.
2. In **Settings → Pages → Build and deployment → Source** die Option **GitHub Actions** wählen.
3. Unter **Actions → Datenatlas auf GitHub Pages → Run workflow** den Ablauf starten. Bei einem Push auf `main` startet er ebenfalls. Erst wenn Datenprüfung, BKG-Aufbereitung und HTTP-Browsertest bestanden sind, veröffentlicht der Deploy-Job die Seite; dessen Ausgabe zeigt die URL.

GitHub-Dokumentation: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

Der erste Aufbau braucht Internetzugriff für Pakete und das BKG-Archiv (rund 66 MB). Bei einem Downloadfehler bricht der Aufbau ab, statt eine scheinbar fertige Karte aus Ersatzgeometrien zu veröffentlichen. Erneut ausführen oder das amtliche Archiv lokal verwenden. Eine aus der Quelle unerwartet geänderte Dateistruktur kann eine Anpassung des Importers erfordern; der reale Erstlauf ist noch offen.

### Mit Git und lokalem Repository

```bash
git init
git add .
git commit -m "Add BW data atlas with documented sources"
git branch -M main
# Die folgende URL durch das eigene Repository ersetzen.
git remote add origin https://github.com/DEIN-KONTO/DEIN-REPOSITORY.git
git push -u origin main
```

Eine echte Betreiberkennzeichnung/Kontaktseite und die für den Betreiber erforderlichen rechtlichen Angaben müssen vor öffentlichem Betrieb ergänzt werden. Das Projekt enthält absichtlich keine erfundenen Verantwortlichen. Das Fehlen von Tracking ersetzt keine Prüfung der konkreten Hosting- und Veröffentlichungspflichten.

## Lokal starten

Python 3.10+; für die isolierten JavaScript-Tests Node.js 20+.

```bash
python scripts/build_data.py
python -m pip install -r requirements-geography.txt
python scripts/prepare_geometry.py
python scripts/validate_geometry.py
python -m http.server 8000 --directory docs
```

Im Browser `http://localhost:8000` öffnen. Alle Browserdateien sind nach dem Geodatenaufbau lokal; es werden keine externen Kartenkacheln angefordert.

Mit vorhandenem **amtlichem** BKG-Archiv:

```bash
python scripts/prepare_geometry.py --archive /pfad/vg250_01-01.utm32s.shape.ebenen.zip
```

Ein direktes Öffnen von `docs/index.html` zeigt die wesentlichen Ansichten auch ohne Server. Das spätere Nachladen der großen Forschungs-JSON kann bei `file://` vom Browser blockiert werden; dafür den HTTP-Server nutzen. Das ZIP mit den Originaldaten bleibt direkt zugänglich.

## Karten, Gebietsschlüssel und Gebietsstände

Der Build nutzt fest das BKG-Archiv **VG250, 01.01.2024**, passend zur zeitlichen Nähe der vorliegenden demografischen Daten – nicht stillschweigend die neuesten 2026er Grenzen. Der aktuelle BKG-Produktstand kann jünger sein. Quelle, Datum, Lizenz, Bearbeitungen und Prüfsumme stehen nach dem Aufbau in `docs/data/geometry.json`.

Kreise werden über ihre amtlichen fünfstelligen Schlüssel verbunden. Die ältere Gemeindetabelle hat nur für Stuttgart einen bereits bestätigten AGS. Der Importer ordnet die übrigen Gemeinden anhand des **normalisierten Namens innerhalb desselben amtlichen Kreises** zu. Er erzeugt keine Schlüssel aus Tabellenpositionen und verwendet keine unscharfe Namenssuche. Eindeutig zugeordnete AGS stehen in `municipality-ags-crosswalk.json`. Unklare Zuordnungen bleiben offen und sichtbar; gemeindefreie Flächen erhalten keine erfundene Bevölkerung.

Der reale Abgleich ist erst nach dem BKG-Download geprüft. Der Build verlangt alle 44 Kreise und mindestens 1.050 eindeutige Gemeindezuordnungen; fehlende Gemeindezuordnungen werden gesondert protokolliert und schraffiert. **1.101 Datensätze bedeutet vor dem Erstlauf nicht automatisch 1.101 erfolgreich kartierte Geometrien.** Der Schwellenwert lässt einzelne Namens-/Gebietsstandsabweichungen zu, statt sie durch geratenes Matching zu verdecken.

## Die Modellrechnung

Für jeden Kreis *k*:

```
Eₖ = Σ_c  Aₖ,c × rc × sc
Mₖ = Eₖ + (T − ΣE) × MHₖ / ΣMH
```

- **T** — veröffentlichte BW-Spanne 2025 (1.133.000–1.197.000). Beide Varianten summieren sich exakt darauf; eine Prüfung sichert das ab.
- **Aₖ,c** — ausländische Bevölkerung der Staatsangehörigkeit *c* im Kreis (Ausländerzentralregister, 31.12.2024), acht Herkunftsgruppen.
- **sc** — bundesweiter muslimischer Anteil der Herkunftsgruppe (BAMF FB55, Tabelle 2). Die fünf widersprüchlichen Werte aus Tabelle 1 bleiben gesperrt.
- **rc** — Korrektur für Eingebürgerte und hier geborene Nachkommen, aus dem Mikrozensus: Türkei 2,03, Kosovo 1,91, Irak 1,60, Syrien 1,24, Afghanistan 1,02.
- **MHₖ** — Bevölkerung mit Migrationshintergrund im Kreis.

Die Staatsangehörigkeitsdaten erklären **78 bis 83 Prozent** der Landessumme. Der Rest — Pakistan, Marokko, Iran, Libanon und weitere ohne Kreisangabe — folgt dem Migrationshintergrund.

**Zwei Varianten** sind wählbar: mit oder ohne die Korrektur *rc*. Der Abstand zwischen ihnen wird im Kreisprofil ausgewiesen und gehört zur Unsicherheit.

**Gemeinden** erhalten keine eigene Schätzung. Der Kreiswert wird verteilt: der türkisch-bosnische Anteil folgt dem im Zensus 2022 gemessenen Siedlungsmuster, der Rest der Einwohnerzahl.

### Grenzen, die bleiben

- Die Anteile *sc* stammen aus der Erhebung MLD 2020. Der BAMF-Bericht rechnet seine Werte für 2025 selbst damit; neuere existieren nicht. Das ist die größte Fehlerquelle.
- Nur 8 von 18 Herkunftsgruppen haben eine Entsprechung je Kreis.
- Die Bezugszeiten der Bausteine unterscheiden sich (2025, 31.12.2024, 2024, 2022, 2019/2020).
- Die Spanne umfasst Landesspanne, Variantenwahl und auf Gemeindeebene den Verteilungsschlüssel — **nicht** den Fehler der bundesweiten Herkunftsanteile.
- Es ist kein Konfidenzintervall im statistischen Sinn.

### Falsifikationstest gegen den Zensus

Der Zensus 2022 weist je Gemeinde nur katholisch, evangelisch und „Sonstige, keine, ohne Angabe" aus. Muslimische Einwohner fallen zwangsläufig in die Restkategorie, deren Anteil ist damit eine harte Obergrenze. Alle 1.101 Gemeinden werden dagegen geprüft; eine Überschreitung bricht den Aufbau ab. Der mittlere Abstand beträgt 28,5 Punkte — die Grenze bindet selten, was selbst ein Befund ist. Die Restkategorie ist **kein** Muslimanteil; sie besteht überwiegend aus Konfessionslosen.

## Prüfnachtrag und Quellenerhalt

`inputs/research-v3.zip` ist der unveränderte Ausgangssnapshot. `scripts/build_data.py` erzeugt Ansichten, überschreibt aber die Originalbeobachtungen nicht. Der Prüfnachtrag ist separat enthalten. Die Quelle „Brachat-Schwarz 2020“ verweist im Quellenkatalog jetzt auf das im Nachtrag bestätigte Original-PDF (Monatsheft **4/2020**, S. 3–10); die abweichende Katalogangabe bleibt dokumentiert.

Die fünf abweichenden MLD-Parameter aus Tabelle 1 des hochgeladenen BAMF FB55 werden nicht als Modellparameter verwendet. Die Diagramme übernehmen veröffentlichte Ergebnisse aus Tabelle 2, die Länderansicht aus Tabelle 3. Die Bestätigung der 18 historischen Anteilsparameter in Tabelle 2 anhand FB38 ist **keine** vollständige Validierung der Hochrechnung. Die Identität des hochgeladenen FB55 mit einer möglicherweise später korrigierten Onlinefassung ist nicht bestätigt. Es werden weder eine korrigierte Bundesschätzung noch heimlich korrigierte Quellenwerte erzeugt.

## Verzeichnisstruktur

```text
.github/workflows/pages.yml         Aufbau, Tests und Pages-Veröffentlichung
inputs/research-v3.zip              Unveränderte Sammlung + Prüfnachtrag
inputs/muslim-shares-fb55-table2.json   Modellparameter: 18 Herkunftsanteile
inputs/mikrozensus-12211-05*.csv    Reduzierte GENESIS-Auszüge (Kreise)
inputs/zensus2022-religion-gemeinden-bw.csv  Obergrenze je Gemeinde
scripts/build_data.py               Netzunabhängige Aufbereitung der Sammlung
scripts/prepare_geometry.py         BKG-Download und AGS-/Namenszuordnung
scripts/prepare_district_origins.py Herkünfte je Kreis aus dem amtlichen Bericht
scripts/prepare_district_migration.py   Migrationshintergrund je Kreis
scripts/prepare_district_age.py     Altersgliederung je Kreis
scripts/prepare_district_generations.py Zweite Generation und Familienstand
scripts/prepare_district_socioeconomics.py  Erwerb und Bildung
scripts/prepare_municipal_origins.py    Zensus-Gitter auf Gemeinden
scripts/build_estimate.py           Modellrechnung je Kreis
scripts/build_municipal_estimate.py Verteilung auf Gemeinden
scripts/build_timeseries.py         Zeitreihe 2021–2025
scripts/check_religion_upper_bound.py   Falsifikationstest gegen den Zensus
scripts/validate_geometry.py        Geografie-Prüfung vor Veröffentlichung
tests/                              Daten-, Modell-, Browser- und Parser-Tests
docs/                               Ausgelieferte Website, Daten und Exporte
vercel.json / .vercelignore         Auslieferung auf Vercel mit Sicherheits-Headern
```

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py' -v   # Daten und Modellrechnung
node --test tests/model.test.cjs                          # Hilfsfunktionen
python scripts/check_religion_upper_bound.py              # Zensus-Obergrenze

# Browsertests, nach Geodatenaufbau:
python -m pip install 'playwright>=1.50,<2' && python -m playwright install chromium
python tests/renderer_smoke.py                            # künstliche Geometrien
python -m http.server 8000 --directory docs &
python tests/browser_smoke.py --url http://localhost:8000 --require-geometry
```

Stand: **66 Python-Prüfungen, 93 Browserprüfungen, 16 Rendererprüfungen, 10 Geodaten-Gates.**

Die Rendererprüfungen erzeugen ausschließlich temporäre künstliche Quadrate. Diese sind **keine BW-Grenzen**, werden nicht mitgeliefert und bestätigen weder die echte BKG-Struktur noch reale Namensübereinstimmungen. Der Workflow prüft davon getrennt das echte aufbereitete Archiv und die ausgelieferte Seite über HTTP.

Der Workflow baut außerdem jede Modelldatei neu auf und bricht ab, wenn sie nicht byteidentisch reproduziert wird.

## Aktualisierung

Neue Veröffentlichungen zuerst als eigene Quellenbeobachtungen mit Bezugszeit, Grundgesamtheit, Einheit, Rundung, Fundstelle und Qualitätsvermerken aufnehmen. Den Ausgangssnapshot und die erwarteten Testwerte nur zusammen mit einem nachvollziehbaren Änderungsprotokoll austauschen. Ein Datenupdate benötigt stets eine inhaltliche Prüfung; dieses Repository beinhaltet **keinen automatischen Live-Religionszähler**.

Was die Modellrechnung tatsächlich genauer machen würde, in dieser Reihenfolge:

1. **Aktuellere Herkunftsanteile.** Die Anteile stammen aus MLD 2020. Eine neue MLD-Erhebung wäre der größte Gewinn — sie liegt außerhalb dieses Projekts.
2. **Mehr Herkunftsgruppen je Kreis.** Pakistan, Marokko, Iran, Libanon, Albanien, Montenegro, Bangladesch, Jordanien und die Gruppen Ägypten/Algerien/Libyen/Tunesien sowie Jemen/Saudi-Arabien/VAE fehlen in Tabelle 4 des amtlichen Berichts und in den Kreistabellen von GENESIS. Eine Kreistabelle nach Staatsangehörigkeit jenseits der dort ausgewiesenen 25 würde die Abdeckung über 83 Prozent heben.
3. **Herkunft je Gemeinde.** Das Zensus-Gitter enthält nur Türkei und Bosnien-Herzegowina. Syrien, Afghanistan, Irak und Kosovo fehlen; deshalb sind die Gemeindespannen breit.

Europäische Quellen helfen hier nicht: Eurostat weist Staatsangehörigkeit auf NUTS-2-Ebene aus, also gröber als Kreise; Pew und die World Religion Database sind national. Visum-, Asyl- oder Staatsangehörigkeitszahlen werden nicht mit muslimischer Bevölkerung gleichgesetzt.

## Lizenzen

Code: `LICENSE` (MIT). Quellendaten, BKG-Namensnennung und Grenzen der Weiterverwendung: `DATA_LICENSES.md`.
