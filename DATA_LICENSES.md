# Quellen, Rechte und Namensnennung

## Eigenständiger Anwendungscode

Der Anwendungscode, die Aufbereitungsskripte und die Projektdokumentation stehen unter der MIT-Lizenz (`LICENSE`). Dies lizenziert weder Originalpublikationen noch fremde Datensätze neu. Es werden keine Schriftdateien, Logos oder Drittanbieter-JavaScriptbibliotheken mitgeliefert.

## Statistische Quellen

`inputs/research-v3.zip` enthält den bestehenden, unveränderten Datensnapshot und den separat erstellten Prüfnachtrag. Quellen und Fundstellen stehen in den Originalbeobachtungen und in `docs/data/sources.json`. Die Zusammenstellung enthält aggregierte veröffentlichte Zahlen und gekennzeichnete Rechnungen, keine personenbezogenen Mikrodaten.

Es wird **keine pauschale offene Lizenz für sämtliche zugrunde liegenden statistischen Quellen behauptet**. Für Weiterverwendung und Veröffentlichung sind die jeweiligen Nutzungsbedingungen der Originalanbieter maßgeblich. Insbesondere sind ein Downloadlink, die Veröffentlichung einer Zahl und eine Lizenz für einen vollständigen Bericht nicht dasselbe. Das Projekt verteilt nicht die Original-PDFs mit ihren Abbildungen und Fotos. Bei Zitaten und Weiterverwendung müssen die Originalquelle, Tabelle, Bezugszeit und gegebenenfalls Modellannahmen erhalten bleiben.

## BKG-Geodaten: erst beim Aufbau bezogen

Produkt: Verwaltungsgebiete 1:250 000, Stand 01.01. (VG250).

- Produktbeschreibung: https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html
- Für diese Anwendung fest ausgewählter Archivstand: **01.01.2024**, nicht 2026.
- Archiv: https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2024/
- Lizenz: Datenlizenz Deutschland – Namensnennung – Version 2.0, https://www.govdata.de/dl-de/by-2-0
- Urheberliste: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf

Vorgesehener sichtbarer Quellenvermerk bei Bezug 2026:

> © BKG 2026, dl-de/by-2-0; Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf

Auf Webseiten sind `BKG` mit https://www.bkg.bund.de und `dl-de/by-2-0` mit der Lizenz-URL zu verlinken. Diese Links und die Urheberliste sind bereits direkt unter der Karte eingefügt. Das Jahr bezeichnet das Jahr des letzten Datenbezugs, **nicht** das Gebietsstands- oder Bevölkerungsjahr. Bei späteren Datenbezügen Quellenvermerk und Metadaten gemeinsam aktualisieren.

Veränderungen: Auswahl Baden-Württemberg; Auswahl Landflächen (GF=4); Zusammenführung nach AGS; Umprojektion nach WGS84; kartografische Vereinfachung mit 40 Metern Toleranz; Rundung von Koordinaten auf fünf Dezimalstellen; Verknüpfung mit separaten statistischen Daten. Die statistischen Personenzahlen werden nicht mit den Geokoordinaten gerundet.

Das originale BKG-ZIP ist in der Auslieferung nicht enthalten. Nach erfolgreichem Aufbau sind die veränderten Geodaten, Quell-URL, Lizenz und SHA-256-Prüfsumme des bezogenen Archivs in `docs/data/geometry.json` dokumentiert. Eine Prüfsumme identifiziert die bezogene Datei, authentifiziert aber nicht den Anbieter.

## Amtliche Statistik für die Modellrechnung

Diese Quellen kamen mit der Modellrechnung hinzu. Sie werden beim Aufbau bezogen
beziehungsweise liegen als reduzierte Auszüge in `inputs/`.

### Ausländerzentralregister je Kreis

- Statistisches Landesamt Baden-Württemberg, Statistischer Bericht **A I 4 - j/24**,
  „Ausländische Bevölkerung in Baden-Württemberg am 31. Dezember 2024", Tabelle 4.
- https://www.statistik-bw.de/fileadmin/user_upload/Service/Veroeff/Statistische_Berichte/312424001.pdf
- Bedingungen laut Bericht: „Vervielfältigung und Verbreitung, auch auszugsweise, mit
  Quellenangabe gestattet." Quellenvermerk: © Statistisches Landesamt Baden-Württemberg, Fellbach.
- Verwendet für: ausländische Bevölkerung je Kreis nach Staatsangehörigkeit.

### Mikrozensus über GENESIS-Online Baden-Württemberg

- Tabellen **12211-0502**, **12211-0503**, **12211-0504**, **12211-0513**.
- https://daten.statistik-bw.de/genesisonline/
- Quellenvermerk: © Statistisches Landesamt Baden-Württemberg. Stichprobenerhebung;
  kleine Fallzahlen werden von der Quelle geheim gehalten und bleiben hier fehlend.
- Verwendet für: Migrationshintergrund je Kreis, Herkunftsland auf Landesebene
  (Korrekturfaktoren), zweite Generation, Altersgliederung, Erwerbsbeteiligung und
  Bildungsstand, Zeitreihe 2021–2025.

### Altersaufbau nach Einwanderungsgeschichte

- Statistisches Landesamt Baden-Württemberg, Mikrozensus 2025: „Bevölkerung in
  Baden-Württemberg 2025 nach Altersgruppen, Geschlecht und Einwanderungsgeschichte"
  sowie „... nach Einwanderungsgeschichte".
- Quellenvermerk: © Statistisches Landesamt Baden-Württemberg. Stichprobenerhebung.
- **Eigene Klassifikation:** „Einwanderungsgeschichte" ist nicht dasselbe wie
  „Migrationshintergrund". Diese Zahlen stehen als eigener Landeswert und werden nicht
  mit den Kreiswerten des übrigen Atlas verrechnet.

### Zensus 2022

- „Staatsangehörigkeit nach ausgewählten Ländern" im 100-Meter-Gitter, „Religion in
  Gitterzellen" (erschienen 07.04.2025) sowie die Sonderauswertung „Bevölkerung nach
  Religionszugehörigkeit, Anteil je Gemeinde".
- https://www.zensus2022.de/DE/Ergebnisse-des-Zensus/Gitterzellen.html
- Lizenz: **Datenlizenz Deutschland – Namensnennung – Version 2.0**
  (https://www.govdata.de/dl-de/by-2-0), von destatis für die Zensusdaten ausdrücklich
  angegeben. Quellenvermerk: © Statistische Ämter des Bundes und der Länder, 2024.
  Damit gilt dieselbe benannte offene Lizenz wie für die BKG-Geometrien, nicht nur eine
  Erlaubnis im Fließtext.
- Geheimhaltung nach dem Cell-Key-Verfahren; Einzelwerte sind bewusst überlagert.
- Ebenfalls verwendet: die Regionaltabelle Demografie mit der Einwanderungsgeschichte
  je Gemeinde als Verteilungsschlüssel für die Herkünfte ohne eigene Gemeindedaten.
- Verwendet für: Verteilungsmuster innerhalb der Kreise, die Obergrenze der
  Gemeindewerte und die Prüfung der Gitterzuordnung gegen die amtliche
  Gemeindetabelle. Der Islam ist im Zensus keine eigene Kategorie; die Restkategorie
  „Sonstige, keine, ohne Angabe" ist kein Muslimanteil.

## Bundesweite Vergleichswerte

- Statistisches Bundesamt, Statistischer Bericht **12411**,
  „Bevölkerungsfortschreibung auf Basis Zensus 2022", Berichtsjahr 2025.
- Lizenz: Datenlizenz Deutschland – Namensnennung – Version 2.0.
- Enthält keine Kreis- oder Gemeindeangaben und geht daher nicht in die Karten ein.
  Verwendet ausschließlich als Gegenprobe der Landessummen.

## Einrichtungsverzeichnis

Das Verzeichnis steht hier **auf Ortsebene**: welche Einrichtung es gibt, in welcher
Gemeinde, in welchem Verband und mit welchen Belegen. Straßen stehen nicht darin, und
das ist Absicht.

Einzeln veröffentlichte Anschriften und eine gepflegte Landesliste sind nicht dasselbe.
Sechshundert Impressen und eine Datei sind verschiedene Gegenstände, und es ist der
zweite, dessen Veröffentlichung der Zentralrat der Muslime mit Verweis auf
Sicherheitsgründe eingestellt hat. Das Bundeskriminalamt zählte für 2025 vorläufig 53
Angriffe auf Moscheen (Bundestags-Drucksachen 21/5917 und 21/2705). Dieser Atlas nennt
deshalb den Ort und verlinkt den Beleg; wer die Anschrift sucht, folgt ihm zu der Seite,
auf der die Einrichtung selbst oder eine Behörde sie nennt. Zusammengeführt wird sie
hier nicht.

Die Prüfarbeit — Verzeichnisse abrufen, Anschriften gegen zwei unabhängige Quellen
halten, geokodieren — liegt in einem getrennten, nicht öffentlichen Repository. Von dort
kommt der Auszug, den dieses Repository veröffentlicht.

**Keine Personenangaben.** Namentliche Ansprechpartner, private E-Mail-Adressen und
Mobilnummern werden nicht erhoben, nicht gespeichert und nicht veröffentlicht: Die
Verknüpfung benannter Personen mit einer Religionsgemeinschaft wäre eine besondere
Kategorie personenbezogener Daten nach Artikel 9 DSGVO. Wo die einzige auffindbare
Anschrift die Privatwohnung einer namentlich genannten Person war, ist die Einrichtung
ohne Anschrift geblieben.

**Aufnahmeregel:** Aufgenommen wird, was öffentlich bekannt und öffentlich belegt ist.
Jeder Eintrag nennt die Quelle, aus der er stammt; wo ein zweiter, unabhängiger Beleg
gefunden wurde, steht auch der dabei.

**Verbandszugehörigkeit ist eine eigene Aussage.** Dass an einem Ort eine Einrichtung
besteht, und dass sie einem bestimmten Verband angehört, sind zwei Behauptungen. Die
zweite braucht eine Quelle, die sie auch trifft, und sie wird mit Urheber und Datum
zitiert — nicht von diesem Atlas behauptet. Dasselbe gilt für Aussagen, die Behörden über
eine Einrichtung gemacht haben: Sie stehen wörtlich da, mit Stand, oder gar nicht.

**Punkte auf der Karte.** Jeder Punkt liegt auf dem Beschriftungspunkt seiner Gemeinde
aus den amtlichen Grenzen (BKG VG250) und bezeichnet kein Gebäude. Der Bau rechnet die
Koordinate selbst aus und bricht ab, wenn in einem Feld eine Anschrift steht — auch im
Fließtext einer Fußnote.

Die Liste ist bewusst unvollständig und nennt die nicht erfassten Verbände ausdrücklich.
Eine Einrichtung ist keine Bevölkerungszahl; die Punkte gehen in keine Modellrechnung
ein.

Das Verzeichnis enthält Daten aus OpenStreetMap und wird deshalb als abgeleitete
Datenbank unter der Open Database License (ODbL) 1.0 bereitgestellt;
© OpenStreetMap-Mitwirkende.

## Externe Gegenproben

Diese Quellen gehen **nicht** in die Modellrechnung ein. Sie dienen ausschließlich der
unabhängigen Prüfung und werden zitiert, nicht weiterverteilt.

- Landeshauptstadt Stuttgart, Statistisches Amt: Frisoli, P. & Mäding, A. (2019),
  „Muslime in Stuttgart 2017. Neue Schätzung zur Zahl der in Stuttgart lebenden
  Muslime", Statistik und Informationsmanagement, Monatsheft 7/2019, S. 228–236.
  Eigenständige Schätzung der Stadt aus dem Melderegister: rund 59.000 Personen zum
  31.12.2017, etwa 10 Prozent der Einwohner.
- kartenseite.wordpress.com (2017), „Muslime in Baden-Württemberg, Gemeinden".
  Gemeindekarten auf Grundlage des Zensus 2011 mal bundesweiter Anteile von
  18 Herkunftsländern. Neun veröffentlichte Städtewerte werden zum Vergleich der
  räumlichen Reihenfolge herangezogen.

## Technische Bibliotheken und GitHub Actions

Python-Pakete und Actions werden beim Aufbau von ihren jeweiligen Anbietern bezogen. Ihre eigenen Lizenzen und Nutzungsbedingungen gelten weiterhin. Die ausgelieferte Website lädt keine Bibliotheken, Kartenkacheln oder Schriftarten von einem fremden CDN nach.
