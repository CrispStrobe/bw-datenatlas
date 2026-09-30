// Drei Sprachen ohne Baukasten.
//
// Nichts im HTML wird markiert. Der Katalog ist nach dem deutschen Text selbst
// geschlüsselt, und zur Laufzeit wird nachgeschlagen. Das hat zwei Gründe. Erstens
// hätte das Einfügen von Markern die Seite durch einen HTML-Serialisierer geschickt,
// und der schreibt SVG-Attribute klein — aus viewBox wird viewbox, und die Karte ist
// hin. Zweitens kann ein Schlüssel nicht veralten, wenn er der Text ist: ändert sich
// der deutsche Satz, fällt die Übersetzung sichtbar auf Deutsch zurück, statt still
// einen alten Satz weiterzuzeigen.
//
// Übersetzt wird das innerHTML des innersten Elements mit eigenem Text, nicht der
// einzelne Textknoten: ein Link mitten im Satz muss dorthin wandern dürfen, wo die
// andere Sprache ihn braucht.
(function () {
 const SPRACHEN = { de: 'Deutsch', en: 'English', fr: 'Français' };
 const LOCALE = { de: 'de-DE', en: 'en-GB', fr: 'fr-FR' };
 const SKIP = new Set(['SCRIPT', 'STYLE', 'TEMPLATE', 'CODE', 'PRE',
                      'TITLE', 'DESC']);
 const kataloge = { de: {} };
 let aktuell = 'de';
 const gesehen = new Set();

 // Behälter, die das Programm selbst füllt. Ihr Inhalt kommt aus den Daten und wird
 // von app.js übersetzt, nicht von hier — sonst überschriebe die eine Seite, was die
 // andere gerade gezeichnet hat.
 function istDynamisch(el) {
  for (let n = el; n && n !== document.body; n = n.parentElement) {
   const id = n.id || '';
   if (/-(table|chart|bars|legend|key|content|results)$/.test(id)) return true;
   if (n.hasAttribute && n.hasAttribute('data-i18n-skip')) return true;
  }
  return false;
 }

 // Dieselbe Auswahl für das Einsammeln und für das Übersetzen: eine Funktion, zwei
 // Verwendungen. Zwei Fassungen derselben Regel liefen unweigerlich auseinander.
 function uebersetzbareElemente() {
  const raus = [];
  for (const el of document.querySelectorAll('body *')) {
   if (SKIP.has(el.tagName) || el.closest('svg') || istDynamisch(el)) continue;
   const hatEigenenText = [...el.childNodes]
     .some(n => n.nodeType === 3 && n.textContent.trim());
   if (!hatEigenenText) continue;
   // Trägt ein Kind selbst wieder Struktur mit Text, gehört die Übersetzung dorthin.
   if ([...el.children].some(c => c.children.length && c.textContent.trim())) continue;
   const inner = sauber(el.innerHTML);
   if (inner.length < 2 || !/[A-Za-zÄÖÜäöüß]/.test(inner)) continue;
   raus.push(el);
  }
  return raus;
 }

 // 'label' wegen der Gruppen im Ebenen-Auswahlfeld: achtundvierzig Einträge in
 // einer flachen Liste sagen nicht, ob eine Ebene Gemeinden, Kreise oder
 // europäische Regionen zeigt. Die Gruppennamen stehen in einem Attribut und
 // blieben ohne diese Zeile in jeder Sprache deutsch.
 const ATTRIBUTE = ['placeholder', 'aria-label', 'title', 'label'];
 function uebersetzbareAttribute() {
  const raus = [];
  for (const el of document.querySelectorAll('body *')) {
   if (SKIP.has(el.tagName) || el.closest('svg') || istDynamisch(el)) continue;
   for (const attr of ATTRIBUTE) {
    const wert = el.getAttribute(attr);
    if (wert && /[A-Za-zÄÖÜäöüß]/.test(wert)) raus.push([el, attr, wert]);
   }
  }
  return raus;
 }

 // Das Original bleibt am Element hängen: ohne es wäre nach dem ersten Wechsel nicht
 // mehr feststellbar, welcher deutsche Satz hier einmal stand.
 // Eigene Marker gehören nicht in den Schlüssel. Ein übersetzbares Element kann in
 // einem anderen stecken — <strong> in einem Absatz —, und dann trüge das innerHTML
 // des Absatzes das data-de des <strong> mit. Der Schlüssel wäre ein anderer als beim
 // ersten Laden, und die Übersetzung fände sich nicht mehr.
 function sauber(html) {
  return html.replace(/\s+data-de(?:-[a-z-]+)?="[^"]*"/g, '').trim();
 }

 function original(el, attr) {
  const schluessel = attr ? `data-de-${attr}` : 'data-de';
  if (!el.hasAttribute(schluessel)) {
   el.setAttribute(schluessel, attr ? el.getAttribute(attr) : sauber(el.innerHTML));
  }
  return el.getAttribute(schluessel);
 }

 function uebersetze(text, sprache) {
  if (sprache === 'de') return text;
  const k = kataloge[sprache];
  return (k && k[text]) || text;
 }

 function anwenden(sprache) {
  aktuell = sprache;
  document.documentElement.lang = sprache;
  for (const el of uebersetzbareElemente()) {
   const de = original(el, null);
   const neu = uebersetze(de, sprache);
   if (sauber(el.innerHTML) !== neu) el.innerHTML = neu;
  }
  for (const [el, attr] of uebersetzbareAttribute()) {
   const de = original(el, attr);
   el.setAttribute(attr, uebersetze(de, sprache));
  }
  // Kopfbereich: Seitentitel und Beschreibung stehen außerhalb von <body> und
  // werden von der Elementsuche nicht erfasst — im Reiter und in jeder Vorschau
  // stünde sonst weiter Deutsch.
  if (!document.documentElement.dataset.deTitle) {
   document.documentElement.dataset.deTitle = document.title;
   const m = document.querySelector('meta[name="description"]');
   if (m) document.documentElement.dataset.deDescription = m.getAttribute('content') || '';
  }
  document.title = uebersetze(document.documentElement.dataset.deTitle, sprache);
  const beschreibung = document.querySelector('meta[name="description"]');
  if (beschreibung && document.documentElement.dataset.deDescription) {
   beschreibung.setAttribute('content',
     uebersetze(document.documentElement.dataset.deDescription, sprache));
  }
  document.documentElement.dataset.sprache = sprache;
  window.dispatchEvent(new CustomEvent('sprachwechsel', { detail: { sprache } }));
 }

 async function lade(sprache) {
  if (sprache === 'de' || kataloge[sprache]) return;
  try {
   const r = await fetch(`assets/i18n/${sprache}.json`, { cache: 'no-cache' });
   kataloge[sprache] = r.ok ? await r.json() : {};
  } catch (e) { kataloge[sprache] = {}; }
 }

 function gewaehlt() {
  const ausAdresse = new URLSearchParams(location.search).get('lang');
  if (ausAdresse && SPRACHEN[ausAdresse]) return ausAdresse;
  try {
   const gemerkt = localStorage.getItem('atlas-sprache');
   if (gemerkt && SPRACHEN[gemerkt]) return gemerkt;
  } catch (e) { /* ohne Speicher eben nicht */ }
  const vomBrowser = (navigator.language || 'de').slice(0, 2);
  return SPRACHEN[vomBrowser] ? vomBrowser : 'de';
 }

 async function wechsle(sprache) {
  await lade(sprache);
  // Ein leerer Katalog bedeutet: die Datei fehlt oder ließ sich nicht laden. Dann
  // stünde deutscher Text unter lang="en" — eine Vorlesehilfe spräche ihn englisch
  // aus. Lieber ehrlich auf Deutsch bleiben.
  if (sprache !== 'de' && Object.keys(kataloge[sprache] || {}).length < 10) {
   sprache = 'de';
  }
  anwenden(sprache);
  try { localStorage.setItem('atlas-sprache', sprache); } catch (e) { /* egal */ }
  const url = new URL(location.href);
  if (sprache === 'de') url.searchParams.delete('lang');
  else url.searchParams.set('lang', sprache);
  history.replaceState(null, '', url);
 }

 window.I18N = {
  sprachen: SPRACHEN,
  get sprache() { return aktuell; },
  get locale() { return LOCALE[aktuell] || 'de-DE'; },
  // Jede Zeichenkette, die durch t() geht, merkt sich der Katalogsammler. Damit
  // findet er auch, was das Programm erst beim Zeichnen erzeugt — Tabellenköpfe,
  // Beschriftungen, Fußnoten —, ohne dass jemand eine zweite Liste pflegt, die
  // unweigerlich hinter dem Code herhinkt.
  t: (text) => { if (text) gesehen.add(text); return uebersetze(text, aktuell); },
  gesehen: () => [...gesehen],
  wechsle,
  uebersetzbareElemente,
  uebersetzbareAttribute,
  // Für das Einsammeln: gibt den Katalog aus, den die Seite gerade braucht.
  sammle() {
   const raus = {};
   for (const el of uebersetzbareElemente()) raus[original(el, null)] = '';
   for (const [, , wert] of uebersetzbareAttribute()) raus[wert] = '';
   raus[document.documentElement.dataset.deTitle || document.title] = '';
   const m = document.querySelector('meta[name="description"]');
   if (m) raus[document.documentElement.dataset.deDescription || m.getAttribute('content')] = '';
   return raus;
  },
 };

 function schalterVerdrahten() {
  for (const btn of document.querySelectorAll('.lang-switch button[data-lang]')) {
   btn.addEventListener('click', () => wechsle(btn.dataset.lang));
  }
  window.addEventListener('sprachwechsel', (e) => {
   for (const btn of document.querySelectorAll('.lang-switch button[data-lang]')) {
    btn.setAttribute('aria-pressed', String(btn.dataset.lang === e.detail.sprache));
   }
  });
 }

 document.addEventListener('DOMContentLoaded', () => {
  schalterVerdrahten();
  wechsle(gewaehlt());
 });
})();
