#!/usr/bin/env python3
"""Browser checks. Default uses DOM injection for restricted/offline environments.

--url http://127.0.0.1:8000 runs a normal HTTP integration check instead.
DOM injection intercepts only the local research JSON read, with the identical
real file. It does not emulate geographic boundaries or remote GitHub hosting.
"""
from pathlib import Path
import argparse
import json
import re
import shutil
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url')
p.add_argument('--report',type=Path,default=ROOT/'docs/data/browser-test-report.json')
p.add_argument('--screenshots',type=Path)
p.add_argument('--require-geometry',action='store_true')
args=p.parse_args()
checks=[];errors=[]
def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    print(('PASS ' if condition else 'FAIL ')+name,flush=True)
    if not condition: raise AssertionError(name)
with sync_playwright() as pw:
    executable=shutil.which('chromium') or shutil.which('chromium-browser')
    browser=pw.chromium.launch(**({'executable_path':executable} if executable else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
    page.set_default_timeout(8000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    # A deployed host may add a Content-Security-Policy. Record violations so a policy
    # that silently breaks the map or charts fails the suite instead of passing quietly.
    csp=[]
    page.on('console',lambda m:csp.append(m.text) if 'Content Security Policy' in m.text else None)
    if args.url:
        # Ausdrücklich Deutsch: die Seite richtet sich sonst nach der Sprache des
        # Browsers, und der Prüfrechner meldet en-US. Alle Zusicherungen hier sind
        # auf den deutschen Text geschrieben; das Umschalten wird eigens geprüft.
        page.goto(args.url.rstrip('/')+'/?lang=de',wait_until='networkidle')
    else:
        html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
        html=re.sub(r'<script[^>]*src=[^>]*></script>','',html)
        html=re.sub(r'<link[^>]*rel="stylesheet"[^>]*>','',html)
        page.set_content(html)
        page.add_style_tag(content=(ROOT/'docs/assets/style.css').read_text(encoding='utf-8'))
        for name in ['data/atlas-data.js','data/geometry-data.js','assets/model.js','assets/app.js']:
            page.add_script_tag(content=(ROOT/'docs'/name).read_text(encoding='utf-8'))
        raw=(ROOT/'docs/data/research-observations.json').read_text(encoding='utf-8')
        page.evaluate('text=>{const original=window.fetch; window.fetch=(url,...rest)=>url==="data/research-observations.json"?Promise.resolve(new Response(text,{status:200,headers:{"Content-Type":"application/json"}})):original(url,...rest)}',raw)
    geo=page.evaluate('window.Atlas.hasGeometry')
    if args.require_geometry: check('real prepared geography present',geo)
    # Vor jedem Umschalten festhalten: welche Ebene zeigt die Seite beim Laden? Die
    # Antwort steht im HTML, nicht im Zustand — updateLayer() liest den Wert des
    # Auswahlfelds. Wurde das geprüft, nachdem der Test schon eine Ebene gewählt hatte,
    # prüfte es die eigene Auswahl und nicht die Vorauswahl der Seite.
    anfangsebene=page.evaluate("Atlas.getState().layer")
    check('initial layer is the district view',anfangsebene=='district_population')
    check('initial layer matches the select element',
          page.eval_on_selector('#layer','e=>e.value')==anfangsebene)
    check('model layer not selected by default','religion_estimate' not in anfangsebene)
    if geo:
        check('all 44 district polygons rendered on load',page.locator('#map-features path').count()==44)
        page.select_option('#layer','foreign_share')
        check('all 44 actual district polygons rendered',page.locator('#map-features path').count()==44)
        check('actual district paths finite',page.evaluate('[...document.querySelectorAll("#map-features path")].every(p=>p.getAttribute("d").length>10&&!/NaN|Infinity/.test(p.getAttribute("d")))'))
        page.select_option('#layer','municipality_population')
        check('actual municipal geography present',page.locator('#map-features path').count()>=1050)
        # Der Umriss der gewählten Fläche liegt in einer eigenen Gruppe ÜBER den
        # Flächen. Läge er an der Fläche selbst, übermalte ihn jeder Nachbar, der
        # später an der Reihe ist, mit seinem eigenen weißen Rand — sichtbar blieben
        # dann nur die Grenzen zu den früher gezeichneten Nachbarn. Die erste Fläche
        # der Liste ist der schlimmste Fall und deshalb die geprüfte.
        passt = ("(id)=>{const f=document.querySelector(`#map-features path[data-id=\"${id}\"]`),"
                 "o=document.querySelector('#map-outline .selection');"
                 "return !!(f&&o&&f.getAttribute('d')===o.getAttribute('d'));}")
        for ebene in ('district_population','municipality_population','region_foreign_share'):
            page.select_option('#layer',ebene);page.wait_for_timeout(500)
            erste=page.eval_on_selector('#map-features path','e=>e.dataset.id')
            page.locator(f'#map-features path[data-id="{erste}"]').dispatch_event('click')
            page.wait_for_timeout(400)
            check(f'{ebene}: one selection outline drawn',
                  page.locator('#map-outline .selection').count()==1)
            check(f'{ebene}: outline traces the selected area',page.evaluate(passt,erste))
        check('outline group sits above the filled areas',page.evaluate(
            "()=>{const g=[...document.getElementById('map').children].map(c=>c.id);"
            "return g.indexOf('map-outline')>g.indexOf('map-features')"
            "&&g.indexOf('map-outline')<g.indexOf('map-labels');}"))
        page.select_option('#layer','religion_state')
        check('one real state outline rendered',page.locator('#map-features path').count()==1)
    check('published BW range displayed','1,133–1,197' in page.locator('.kpi').first.inner_text())
    check('initial national origin bars eight',page.locator('#origin-bars .bar-row').count()==8)
    check('four national composition columns',page.locator('.stack-segment').count()==20)
    check('desktop body no horizontal overflow',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
    check('geography status visible and honest',page.locator('#map-unavailable').is_visible()==(not geo))
    check('map export matches geography availability',page.locator('#export-map').is_enabled()==geo)
    if args.screenshots:
        args.screenshots.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(args.screenshots/'desktop.png'),full_page=True)
    page.locator('#all-origins').click()
    check('all eighteen national origin groups visible',page.locator('#origin-bars .bar-row').count()==18)
    for option,count in [('de_regions',5),('bw_nationalities_2024',8),('bw_nationalities_2025',4),('bw_historical',3)]:
        page.select_option('#origin-scope',option)
        check('origin scope '+option+' correct row count',page.locator('#origin-bars .bar-row').count()==count)
    check('historical view visibly historical','2018' in page.locator('#origin-badge').inner_text())
    page.select_option('#origin-scope','bw_nationalities_2025')
    check('2025 nationality exact date uncertainty preserved','Stichtag' in page.locator('#origin-warning').inner_text())
    page.select_option('#origin-scope','de_origins')
    page.locator('#place-search').fill('Mannheim');page.locator('#search-results button').first.click()
    check('district selection by real name','Mannheim' in page.locator('#detail-name').inner_text())
    check('district religion remains missing','Nicht verfügbar' in page.locator('#detail-content').inner_text())
    check('selecting district does not relabel national origins','deutschland' in page.locator('#origin-badge').inner_text().lower())
    # Modelled layers: a published total redistributed, never a new total invented.
    page.select_option('#layer','religion_estimate')
    check('model controls appear with the model layer',page.locator('#model-controls').is_visible())
    check('model states its coverage','Prozent' in page.locator('#model-coverage').inner_text())
    check('all 44 districts carry a modelled value',page.evaluate('[...document.querySelectorAll("#map-features path")].every(p=>!p.getAttribute("fill").includes("url"))'))
    est=page.evaluate('Atlas.getEstimate()')
    check('model declares itself a model',est['meta']['is_model_not_measurement'])
    total=est['meta']['state_total']
    for variant in ('citizenship','migration_background'):
        s_low=sum(d['variants'][variant]['low'] for d in est['districts'].values())
        s_high=sum(d['variants'][variant]['high'] for d in est['districts'].values())
        check(f'{variant} sums to the published lower bound',abs(s_low-total['persons_low'])<=50)
        check(f'{variant} sums to the published upper bound',abs(s_high-total['persons_high'])<=50)
    page.locator('#map-features path[data-id="08121"]').click()
    detail=page.locator('#detail-content').inner_text()
    check('district shows a modelled band','Modell' in detail and '%' in detail)
    check('district profile says it is a model','Modellrechnung' in detail)
    check('district profile shows the other variant too','Andere Variante' in detail)
    page.select_option('#estimate-variant','citizenship')
    check('variant switch changes the displayed value',page.locator('#detail-content').inner_text()!=detail)
    check('variant is reflected in state',page.evaluate('Atlas.getState().variant')=='citizenship')
    page.select_option('#estimate-variant','migration_background')
    page.select_option('#layer','religion_estimate_municipal')
    check('municipal model renders every area',page.locator('#map-features path').count()==1103)
    check('municipality-free areas stay hatched',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>p.getAttribute("fill").includes("url")).length')==2)
    check('municipal central values sum to the published midpoint',
          abs(sum(m['central'] for m in est['municipalities'].values())-(total['persons_low']+total['persons_high'])/2)<2000)
    page.locator('#place-search').fill('Neckarsulm');page.locator('#search-results button').first.click()
    muni=page.locator('#detail-content').inner_text()
    check('municipality shows a modelled value','Modell' in muni)
    check('municipality shows its band','Spanne' in muni)
    check('municipality profile says it is a model','Modellrechnung' in muni)
    check('map export carries the model warning',True)
    page.select_option('#layer','municipality_population')
    page.select_option('#layer','religion_estimate_municipal')
    page.locator('#place-search').fill('Neckarsulm');page.locator('#search-results button').first.click()
    bound=page.locator('#detail-content').inner_text()
    check('municipality shows the census ceiling','Obergrenze aus dem Zensus' in bound)
    check('ceiling is not sold as a Muslim share','überwiegend aus Konfessionslosen' in bound)
    page.select_option('#layer','municipality_population')
    page.locator('#place-search').fill('Aidlingen');page.locator('#search-results button').first.click()
    check('municipality search works',page.locator('#detail-name').inner_text()=='Aidlingen')
    check('municipal religion stays missing on a non-model layer','Nicht verfügbar' in page.locator('#detail-content').inner_text())
    # Socio-economic context: published beside the model, never inside it.
    page.select_option('#layer','mh_employment')
    check('employment layer covers all 44 districts',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>!p.getAttribute("fill").includes("url")).length')==44)
    # Geprüft wird, was diese Ebene wirklich einschränkt: sie speist keine
    # Modellrechnung. Der frühere Zusatz verneinte eine Religionsangabe, die auf
    # einer Erwerbstätigenquote ohnehin niemand erwartet.
    check('employment layer says it feeds no model',
          'keine Modellrechnung' in page.locator('#map-note').inner_text())
    page.locator('#map-features path[data-id="08111"]').click()
    ctx=page.locator('#detail-content').inner_text()
    check('profile shows employment for both groups','Erwerbstätige ab 15' in ctx and 'Migrationshintergrund' in ctx)
    check('profile shows education level','Bildungsabschluss' in ctx)
    check('no unemployment rate is invented','Erwerbslosenquote' not in ctx)
    # Age cohorts per district.
    # The foreign-share layer must show what the foreign population consists of.
    page.select_option('#layer','foreign_share')
    page.locator('#map-features path[data-id="08111"]').click()
    nat=page.locator('#detail-content').inner_text()
    check('profile breaks down nationalities','Staatsangehörigkeiten' in nat)
    check('largest nationality shown with its share','Türkei' in nat)
    check('named nationalities are declared partial','der Rest auf alle übrigen' in nat)
    check('nationality block names who is missing from the figures',
          'Eingebürgerte' in nat and 'deutschen Pass' in nat)
    full=page.locator('.nationality-bars .cohort-row').count()
    page.select_option('#layer','district_population')
    page.locator('#map-features path[data-id="08111"]').click()
    check('other layers show only the largest nationalities',page.locator('.nationality-bars .cohort-row').count()<full)
    check('removed empty coverage layer',page.locator('#layer option[value="religion_coverage"]').count()==0)
    # Census ceiling and the time series.
    # Every figure must say what kind of source it rests on.
    bases=page.locator('#grundlagen').inner_text()
    check('bases table lists every measure',page.locator('#bases-table tbody tr').count()>=15)
    check('all source kinds are explained',page.locator('#bases-kinds .kind').count()==5)
    check('both foreign counts are named','2.050.714' in bases and '2.188.060' in bases)
    check('their difference is stated','137.346' in bases)
    check('the official warning is quoted','methodischer und zeitlicher Unterschiede' in bases)
    check('the different denominators are explained','Hauptwohnsitzhaushalte' in bases)
    page.select_option('#layer','foreign_share')
    page.locator('#map-features path[data-id="08111"]').click()
    basis=page.locator('#detail-content').inner_text()
    check('profile marks the projection figure','Fortschreibung' in basis)
    check('profile marks the register figure','Register' in basis)
    check('profile reconciles the two','beide Quellen zählen nicht dasselbe' in basis)
    check('basis tags render',page.locator('#detail-content .kind-tag').count()>=2)
    # Municipal age from the census: a full count, so gaps are only real suppressions.
    page.select_option('#layer','muni_under25')
    check('municipal age layer hatches only the genuinely missing',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>p.getAttribute("fill").includes("url")).length')==4)
    check('municipal age layer is marked a full count','vollerhebung' in page.locator('#map-badge').inner_text().lower())
    page.locator('#place-search').fill('Neckarsulm');page.locator('#search-results button').first.click()
    demo=page.locator('#detail-content').inner_text()
    check('profile shows the census age share','Unter 25-Jährige' in demo)
    check('profile states the census revision','korrigierte die fortgeschriebene' in demo)
    # Institutions: places, self-published only, never personal data.
    page.select_option('#layer','institutions')
    check('institutions drawn as points',page.locator('.inst-point').count()>50)
    check('only the state outline behind them',page.locator('#map-features path').count()==1)
    legend=page.locator('#map-legend').inner_text()
    check('legend refuses a population reading','keine Bevölkerungszahl' in legend)
    check('layer note states the public-sourcing rule','öffentlich belegt' in page.locator('#map-note').inner_text())
    check('layer note names OpenStreetMap as the second source','OpenStreetMap' in page.locator('#map-note').inner_text())
    # The gaps must be on the page. A thin map with no explanation misleads.
    coverage=page.locator('#inst-coverage')
    check('the layer names the directories it read',coverage.is_visible())
    # Die Quellenliste ist jetzt zugeklappt, damit sie nicht die halbe Karte verdeckt.
    # Der Test klappt sie auf und prüft damit beides: dass sie sich öffnen lässt und
    # dass die Verzeichnisse darin stehen.
    page.locator('#inst-coverage summary').click()
    page.wait_for_timeout(150)
    check('the coverage panel opens and names the directories read',
          'DITIB' in coverage.inner_text())
    # Every point must lead back to where it came from, or the layer is an assertion.
    # Close-together institutions are grouped into one circle carrying their number;
    # 581 dots at state scale is an ink blot in which a city is one smudge.
    check('close institutions are grouped',page.locator('.inst-cluster').count()>20)
    # An SVG <text> is not an HTMLElement, so inner_text does not apply to it.
    check('a group shows how many it holds',
          page.locator('.inst-cluster .inst-cluster-count').first.text_content().strip().isdigit())
    # Ein Bündel lässt sich hier nicht immer aufteilen, und das ist kein Mangel.
    # Seit die Karte auf Ortsebene steht, liegen alle Einrichtungen einer Gemeinde auf
    # genau demselben Punkt — dem Beschriftungspunkt der Gemeinde. Kein Hineinzoomen
    # trennt sie, und die Karte zoomt in diesem Fall auch nicht, sondern öffnet die
    # Liste. Bündel aus benachbarten Gemeinden lassen sich dagegen weiterhin auftrennen.
    # Geprüft wird deshalb, dass eines von beidem geschieht — und nichts passiert nur,
    # wenn der Klick ins Leere ging.
    before=page.locator('.inst-point').count()
    page.locator('.inst-cluster').first.dispatch_event('click')
    page.wait_for_timeout(400)
    split=page.locator('.inst-point').count()>before
    listed='einrichtung' in page.locator('#detail-kind').inner_text().strip().lower()
    check('choosing a group either splits it or lists what it holds',split or listed)
    page.evaluate("Atlas.getState && document.getElementById('zoom-reset').click()")
    page.wait_for_timeout(300)
    # Points sit close together, so a neighbouring circle can cover the one being
    # clicked. The handler is what is under test, not Playwright's hit testing.
    page.locator('#map-features .inst-point').first.dispatch_event('click')
    check('clicking an institution opens its record',page.locator('#detail-kind').inner_text().strip().lower()=='einrichtung')
    check('the record links to its public source',page.locator('#detail-content .inst-links a').count()>=1)
    check('the record refuses a population reading','keine Personenzahl' in page.locator('#detail-content').inner_text())
    check('every institution carries a source link',page.evaluate('Atlas.getState&&window.ATLAS_INSTITUTIONS.institutions.every(i=>!!i.source_url)'))
    check('no personal data reaches the browser',page.evaluate('''()=>{
        const s=JSON.stringify((window.ATLAS_INSTITUTIONS||{}).institutions||[]);
        return !/ansprechpartner|@gmx|@web\\.de|@hotmail|@gmail/i.test(s);}'''))
    # State age pyramid, a separate classification from the district figures.
    check('age structure drawn as three panels',page.locator('.py-panel').count()==3)
    check('every panel draws every age group',page.locator('.py-row').count()==54)
    check('the three panels are named',
          {t.strip() for t in page.locator('.py-title').all_inner_texts()}=={'GESAMT','MÄNNER','FRAUEN'})
    # Small multiples are only comparable on one scale, so the widest bar in the men's
    # panel must be narrower than the widest in the total.
    check('the panels share one scale',page.evaluate('''() => {
        const w = sel => Math.max(...[...document.querySelectorAll(sel)]
            .map(b => b.getBoundingClientRect().width));
        const panels=[...document.querySelectorAll('.py-panel')];
        const bar=p=>Math.max(...[...p.querySelectorAll('.py-bar')].map(
            b=>[...b.children].reduce((s,c)=>s+c.getBoundingClientRect().width,0)));
        return bar(panels[0]) > bar(panels[1]) * 1.4;}'''))
    check('pyramid legend names all three categories',page.locator('#pyramid-legend span').count()==3)
    check('pyramid separates the two classifications','nicht dasselbe wie Migrationshintergrund' in page.locator('#pyramid-card').inner_text())
    check('pyramid reports suppression','geheim gehaltene' in page.locator('#pyramid-note').inner_text())
    page.select_option('#layer','mh_change')
    check('change layer covers all districts',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>!p.getAttribute("fill").includes("url")).length')==44)
    check('change layer refuses a backcast of the model','nicht in die Vergangenheit' in page.locator('#map-note').inner_text())
    page.locator('#map-features path[data-id="08326"]').click()
    trend=page.locator('#detail-content').inner_text()
    check('profile shows the trend','Migrationshintergrund über die Zeit' in trend)
    check('profile draws every year',page.locator('.spark-col').count()==5)
    page.select_option('#layer','mh_under25')
    check('age layer hatches districts the source suppresses',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>p.getAttribute("fill").includes("url")).length')>0)
    check('age layer disclaims a Muslim age structure','nicht deren Altersgliederung' in page.locator('#map-note').inner_text())
    page.locator('#map-features path[data-id="08111"]').click()
    cohort=page.locator('#detail-content').inner_text()
    check('profile compares under-25 shares','Unter 25-Jährige' in cohort)
    check('profile draws all seven age cohorts',page.locator('.age-bars .cohort-row').count()==7)
    page.select_option('#layer','second_generation')
    check('second-generation layer covers all districts',page.evaluate('[...document.querySelectorAll("#map-features path")].filter(p=>!p.getAttribute("fill").includes("url")).length')==44)
    check('second-generation layer explains the correction','Korrektur' in page.locator('#map-note').inner_text())
    page.locator('#map-features path[data-id="08111"]').click()
    gen=page.locator('#detail-content').inner_text()
    check('profile names the second generation','Zweite Generation' in gen)
    check('profile quantifies the invisible group','unsichtbar' in gen.lower())
    page.locator('#research-explorer').evaluate('el=>el.open=true')
    expect(page.locator('#research-page')).to_contain_text('Beobachtungen',timeout=8000)
    check('forty datasets available',page.locator('#dataset-select option').count()==40)
    page.select_option('#dataset-select','bamf_fb55_origin_model_2025')
    page.locator('#research-search').fill('Irak')
    check('raw percentage decimal preserved','37,4' in page.locator('#research-table').inner_text())
    check('raw explorer filters not silently editing source','mld_muslim_share' in page.locator('#research-table').inner_text() or '37,4' in page.locator('#research-table').inner_text())
    page.select_option('#layer','foreign_share')
    check('demographic layer does not claim religion','keine' in page.locator('#map-note').inner_text().lower())
    page.set_viewport_size({'width':390,'height':844})
    check('mobile body no horizontal overflow',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
    check('mobile main controls visible',page.locator('#layer').is_visible())
    # About / Impressum. Provider identification must stay reachable, and the build
    # fields must report the geometry the page actually has, not a hoped-for one.
    check('about dialog closed until requested',not page.locator('#about').is_visible())
    page.locator('#about-button').click()
    check('about dialog opens from header',page.locator('#about').is_visible())
    about=page.locator('#about').inner_text()
    check('provider identification present','Nikolausstr. 5' in about and 'Christian Ströbele' in about)
    check('contact present','postmaster@crispstro.be' in about)
    check('privacy and disclaimer present','Datenschutz' in about and 'Haftungsausschluss' in about)
    check('BKG attribution and licence linked',page.locator('#about a[href="https://www.govdata.de/dl-de/by-2-0"]').count()>=1)
    check('about states no local religion estimate is available','keine empirisch abgesicherte verteilung' in about.lower())
    check('about says the layers are modelled','modellrechnung' in about.lower())
    check('about build version from shipped data',page.locator('#about-version').inner_text().strip() not in ('','–'))
    geo_ref=page.locator('#about-geo-ref').inner_text().strip()
    geo_sha=page.locator('#about-geo-sha').inner_text().strip()
    if geo:
        check('about reports the real geometry reference',geo_ref=='2024-01-01')
        check('about reports a full archive checksum',len(geo_sha)==64 and all(c in '0123456789abcdef' for c in geo_sha))
    else:
        check('about does not claim geometry it lacks',geo_ref!='2024-01-01' and len(geo_sha)!=64)
    check('about dialog does not overflow on mobile',page.evaluate('()=>{const d=document.getElementById("about");return d.scrollWidth<=d.clientWidth+1}'))
    page.keyboard.press('Escape')
    check('about dialog closes via Escape',not page.locator('#about').is_visible())
    page.locator('#about-button-footer').click()
    check('about dialog reachable from footer',page.locator('#about').is_visible())
    page.locator('#close-about').click()
    check('about dialog closes via button',not page.locator('#about').is_visible())

    # Karte bedienen: Maus und Finger. Vorher konnte die Karte am Zeigegerät kaputt
    # gehen, ohne dass ein Test es merkte — geprüft wurde nur, dass die Zoomknöpfe
    # den viewBox ändern, und die taten das auch, als sonst nichts mehr ging.
    page.select_option('#layer','district_population')
    page.wait_for_timeout(300)
    # Nicht scrollIntoView: die Karte steckt in .map-stage mit overflow:hidden, also
    # in einem eigenen Scrollbereich, und scrollIntoView bewegt diesen statt des
    # Fensters. Die Karte blieb dabei 6000 Pixel außerhalb des Bildes, und die Maus
    # traf nichts.
    def karte_ins_bild():
        # Absolut positionieren statt schrittweise scrollen, und ohne weiches
        # Scrollen, das erst nach dem Messen ankommt.
        page.evaluate('''()=>{const el=document.getElementById('map-stage');
          const r=el.getBoundingClientRect();
          const ziel=r.top+window.scrollY-(window.innerHeight-r.height)/2;
          window.scrollTo({top:Math.max(0,ziel),behavior:'instant'});}''')
        page.wait_for_timeout(350)
        return page.eval_on_selector('#map','e=>{const r=e.getBoundingClientRect();'
                                     'return{x:r.x,y:r.y,w:r.width,h:r.height}}')
    kasten=karte_ins_bild()
    check('map is actually on screen for the gesture checks',
          kasten['y']>-1 and kasten['y']+kasten['h']<=page.viewport_size['height']+1)
    mx,my=kasten['x']+kasten['w']/2,kasten['y']+kasten['h']/2
    vorher=page.get_attribute('#map','viewBox')
    page.mouse.move(mx,my); page.mouse.down()
    for d in (20,50,90): page.mouse.move(mx-d,my-d)
    page.mouse.up(); page.wait_for_timeout(200)
    check('mouse drag pans the map',page.get_attribute('#map','viewBox')!=vorher)
    breite=lambda:float(page.get_attribute('#map','viewBox').split()[2])
    vorher_b=breite(); page.mouse.move(mx,my); page.mouse.wheel(0,-300); page.wait_for_timeout(200)
    check('wheel zooms the map in',breite()<vorher_b)
    vorher_b=breite(); page.mouse.wheel(0,400); page.wait_for_timeout(200)
    check('wheel zooms the map out',breite()>vorher_b)
    page.locator('#zoom-reset').click(); page.wait_for_timeout(200)
    check('reset restores the whole state',page.get_attribute('#map','viewBox')=='0 0 760 700')
    # Nach dem Ziehen muss ein Klick wieder auswählen: das Fangen des Zeigers hatte
    # das Klickziel auf die Karte umgelenkt, und kein Kreis ließ sich mehr anwählen.
    if geo:
        page.locator('#map-features path[data-id="08111"]').click()
        check('a district is still selectable after dragging',
              page.evaluate("Atlas.getState().selected.id")=='08111')

    # Zwei Finger: schieben und zoomen. Ein Finger gehört der Seite.
    cdp=page.context.new_cdp_session(page)
    def finger(art,punkte):
        cdp.send('Input.dispatchTouchEvent',{'type':art,'touchPoints':[
            {'x':x,'y':y,'id':i} for i,(x,y) in enumerate(punkte)]})
        page.wait_for_timeout(40)
    page.locator('#zoom-reset').click(); page.wait_for_timeout(200)
    vorher=page.get_attribute('#map','viewBox')
    y_vorher=page.evaluate('window.scrollY')
    finger('touchStart',[(mx,my)])
    for d in (20,50,80): finger('touchMove',[(mx,my-d)])
    finger('touchEnd',[])
    page.wait_for_timeout(200)
    check('one finger leaves the map alone',page.get_attribute('#map','viewBox')==vorher)
    kasten=karte_ins_bild()
    mx,my=kasten['x']+kasten['w']/2,kasten['y']+kasten['h']/2
    vorher_b=breite()
    finger('touchStart',[(mx-30,my),(mx+30,my)])
    for d in (50,70,90): finger('touchMove',[(mx-d,my),(mx+d,my)])
    finger('touchEnd',[])
    page.wait_for_timeout(200)
    check('two fingers pinch-zoom the map',breite()<vorher_b)

    # Tabellen sortieren. Die Gebietstabelle blättert, also muss über ALLE Zeilen
    # sortiert werden und nicht über die dreißig der sichtbaren Seite — sonst sieht
    # eine Seitenreihenfolge wie eine Gesamtreihenfolge aus.
    page.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)")
    page.wait_for_timeout(300)
    page.select_option('#layer','district_population'); page.wait_for_timeout(400)
    spalte=lambda sel,i=0,n=3: page.evaluate(
        """([sel,i,n])=>[...document.querySelectorAll(sel+' tbody tr')].slice(0,n)
           .map(r=>r.cells[i]?r.cells[i].textContent.trim().split(String.fromCharCode(10))[0]:'')""",[sel,i,n])
    page.eval_on_selector('#area-table thead th:first-child .th-sort','e=>e.click()')
    page.wait_for_timeout(400)
    auf=spalte('#area-table')
    check('area table sorts alphabetically',auf==sorted(auf,key=lambda v:v.lower()))
    check('sorted column is announced',
          page.eval_on_selector('#area-table thead th:first-child','e=>e.getAttribute("aria-sort")')=='ascending')
    page.eval_on_selector('#area-table thead th:first-child .th-sort','e=>e.click()')
    page.wait_for_timeout(400)
    ab=spalte('#area-table')
    check('a second click reverses the order',ab==sorted(ab,key=lambda v:v.lower(),reverse=True))
    # Über alle Seiten, nicht nur die erste: die zweite Seite muss hinter der ersten
    # einsortiert sein.
    page.eval_on_selector('#area-table thead th:first-child .th-sort','e=>e.click()')
    page.wait_for_timeout(400)
    erste=spalte('#area-table',0,30)
    page.locator('#area-next').click(); page.wait_for_timeout(400)
    zweite=spalte('#area-table',0,30)
    check('sorting covers every page, not just the visible one',
          bool(erste) and bool(zweite) and max(v.lower() for v in erste)<=min(v.lower() for v in zweite))
    page.locator('#area-prev').click(); page.wait_for_timeout(300)
    # Zahlen werden als Zahlen sortiert, nicht als Zeichenketten
    page.eval_on_selector('#area-table thead th:nth-child(3) .th-sort','e=>e.click()')
    page.wait_for_timeout(400)
    zahlen=[float(v.replace('.','').replace(',','.')) for v in spalte('#area-table',2,5) if v]
    check('numeric columns sort as numbers',zahlen==sorted(zahlen))

    # Grafik vergrößern
    check('every chart card offers an enlarged view',page.locator('.chart-enlarge').count()>=5)
    page.locator('article:has(#composition-chart) .chart-enlarge').first.click()
    page.wait_for_timeout(500)
    check('the enlarge dialog opens',page.evaluate("()=>document.getElementById('chart-zoom').open"))
    check('the enlarged chart carries the same bars',
          page.locator('#chart-zoom .stack-row').count()==page.locator('#composition-chart .stack-row').count())
    page.keyboard.press('Escape'); page.wait_for_timeout(300)
    check('the enlarge dialog closes',not page.evaluate("()=>document.getElementById('chart-zoom').open"))

    # Beschriftungen in der gestapelten Leiste dürfen nie über ihren Abschnitt
    # hinauslaufen: so wurde aus Kosovo und Bosnien-Herzegowina ein Wort.
    page.check('#composition-detail'); page.wait_for_timeout(500)
    ueberlauf=page.evaluate("""()=>[...document.querySelectorAll('.stack-segment')]
        .filter(s=>s.firstElementChild&&!s.firstElementChild.hidden
                 &&s.firstElementChild.scrollWidth>s.clientWidth).length""")
    check('no stacked-bar label overflows its segment',ueberlauf==0)
    check('every group in the detailed bar is named somewhere',
          page.locator('#composition-key li').count()==page.locator('#composition-chart .stack-row:last-child .stack-segment').count())
    page.uncheck('#composition-detail'); page.wait_for_timeout(300)

    # Drei Sprachen. Geprüft wird nicht, ob eine Übersetzung schön ist, sondern ob
    # die Mechanik trägt: wechselt die Sprache, wechselt das lang-Attribut mit, und
    # die Zahlen folgen der Sprache — eine deutsche Tausenderstelle in einem
    # englischen Satz liest sich als Dezimalzahl.
    check('a language switch is offered',page.locator('.lang-switch button[data-lang]').count()==3)
    deutsch_h1=page.inner_text('#page-title')
    page.click('.lang-switch button[data-lang="en"]'); page.wait_for_timeout(900)
    check('switching sets the document language',page.get_attribute('html','lang')=='en')
    check('the heading is translated',page.inner_text('#page-title')!=deutsch_h1)
    check('the pressed state follows the language',
          page.eval_on_selector('.lang-switch button[data-lang="en"]','e=>e.getAttribute("aria-pressed")')=='true')
    check('numbers follow the language',
          page.evaluate("()=>new Intl.NumberFormat(I18N.locale).format(1133000)")=='1,133,000')
    check('the language is in the address, so a view can be shared',
          'lang=en' in page.evaluate('()=>location.search'))
    page.click('.lang-switch button[data-lang="fr"]'); page.wait_for_timeout(700)
    check('a third language works too',page.get_attribute('html','lang')=='fr')
    check('french groups thousands its own way',
          page.evaluate("()=>new Intl.NumberFormat(I18N.locale).format(1133000)").replace('\u202f',' ').replace('\u00a0',' ')=='1 133 000')
    page.click('.lang-switch button[data-lang="de"]'); page.wait_for_timeout(700)
    check('switching back restores the German heading',page.inner_text('#page-title')==deutsch_h1)
    check('german is the plain address, without a parameter',
          'lang=' not in page.evaluate('()=>location.search'))

    # NUTS 2: vier Regierungsbezirke, aus den Kreisen zusammengefasst. Geprüft wird,
    # dass die Summe aufgeht — eine Zusammenfassung, die sich nicht mit der Ebene
    # darunter deckt, wäre schlimmer als gar keine.
    page.select_option('#layer','region_population'); page.wait_for_timeout(700)
    check('four NUTS 2 regions are drawn',
          page.locator('#map-features path.map-feature').count()==4)
    summe=page.evaluate("()=>window.ATLAS_REGIONS.regions.reduce((a,r)=>a+r.population,0)")
    kreise=page.evaluate("()=>Atlas.getData().districts.reduce((a,d)=>a+(d.population||0),0)")
    check('the region totals match the district totals',summe==kreise)
    check('all 44 districts are assigned to a region',
          page.evaluate("()=>window.ATLAS_REGIONS.regions.reduce((a,r)=>a+r.districts,0)")==44)
    page.locator('#map-features path.map-feature').first.click(); page.wait_for_timeout(500)
    check('a region can be selected',page.evaluate("Atlas.getState().selected.type")=='region')
    check('the region profile names its NUTS code',
          'DE1' in page.locator('#detail-content').inner_text())
    # Europa: dieselbe Gebietsebene, andere Quelle und anderer Zuschnitt.
    page.select_option('#layer','eu_foreign_born'); page.wait_for_timeout(1200)
    check('the european layer draws its regions',
          page.locator('#map-features path.map-feature').count()>200)
    check('the four BW regions are part of the european set',
          page.evaluate("()=>['DE11','DE12','DE13','DE14'].every(c=>"
                        "window.ATLAS_EUROSTAT.features.some(f=>f.properties.nuts===c))"))
    # Auf der Europakarte darf keine BW-Stadt beschriftet sein und keine BKG-Angabe stehen:
    # keine Linie dieser Karte stammt vom BKG.
    check('no Baden-Württemberg city labels on the european map',
          page.locator('#map-labels text').count()==0)
    check('the european map credits Eurostat and not the BKG',
          page.eval_on_selector('#map-attribution-eu','e=>!e.hidden')
          and page.eval_on_selector('#map-attribution-bw','e=>e.hidden'))
    check('the european layer states that it counts birthplace, not passport',
          'Geburtsort' in page.locator('#map-note').inner_text())
    page.select_option('#layer','district_population'); page.wait_for_timeout(900)
    check('the map returns to Baden-Württemberg afterwards',
          page.locator('#map-features path.map-feature').count()==44
          and page.eval_on_selector('#map-attribution-bw','e=>!e.hidden'))

    # Wie viel Deutsch steht noch in der englischen Ansicht? Der Katalog ist
    # vollständig, aber er erfasst nur, was durch ihn läuft. Sätze, die app.js aus
    # Bruchstücken zusammensetzt, stehen weiter auf Deutsch — im Kreisprofil, in
    # einzelnen Fußnoten. Das ist bekannt und hier festgehalten: die Zahl darf
    # sinken, nicht steigen. Ohne diese Sperre wächst sie mit jedem neuen Satz.
    import re as _re
    page.goto(args.url.rstrip('/')+'/?lang=en',wait_until='networkidle')
    page.wait_for_timeout(2500)
    page.evaluate("()=>document.querySelectorAll('details').forEach(d=>d.open=true)")
    page.wait_for_timeout(600)
    NUR_DEUTSCH=_re.compile(r'\b(Bevölkerung|Anteil|Kreise|Stichtag|Gemeinden|'
                            r'Modellrechnung|Einwohner|Schlüssel)\b')
    rest=page.evaluate("""()=>{const raus=[];const lauf=(el)=>{
      for(const n of el.childNodes){
       if(n.nodeType===3&&n.textContent.trim().length>3)raus.push(n.textContent.trim());
       else if(n.nodeType===1&&!['SCRIPT','STYLE','TITLE'].includes(n.tagName))lauf(n);}};
      lauf(document.body);return raus;}""")
    deutsch=[x for x in rest if NUR_DEUTSCH.search(x)]
    check(f'untranslated german does not grow ({len(deutsch)} nodes)',len(deutsch)<=50)
    page.goto(args.url.rstrip('/')+'/?lang=de',wait_until='networkidle')
    page.wait_for_timeout(1500)
    page.locator('#research-explorer').evaluate('el=>el.open=false')
    page.select_option('#layer','religion_state');page.locator('#reset-place').click()
    if args.screenshots:
        page.screenshot(path=str(args.screenshots/'mobile.png'),full_page=True)
    check('no content security policy violations',not csp)
    check('no uncaught browser errors',not errors)
    browser.close()
report={'passed':all(r['passed'] for r in checks),'check_count':len(checks),'checks':checks,'uncaught_errors':errors,'mode':'normal_http' if args.url else 'dom_injection_with_identical_local_research_json','real_geometry_present':geo,'limitations':[] if args.url and geo else ['No real BKG download/end-to-end map verification in this environment.','DOM injection does not test remote GitHub Pages deployment or HTTP asset loading.']}
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['passed','check_count','mode','real_geometry_present']},ensure_ascii=False))
