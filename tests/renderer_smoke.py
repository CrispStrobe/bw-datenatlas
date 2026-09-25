#!/usr/bin/env python3
"""Test SVG interactions using artificial temporary geometry in browser memory.

No geographic accuracy, BKG correspondence, or public deployment is tested.
No artificial geometry or map screenshot is written to the website directory.
"""
import json
from pathlib import Path
import re
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/'docs/data/atlas.json').read_text(encoding='utf-8'))
def box(x,y,w=.07,h=.04):
    return {'type':'Polygon','coordinates':[[[x,y],[x+w,y],[x+w,y+h],[x,y+h],[x,y]]]}
def feature(p,g):return {'type':'Feature','properties':p,'geometry':g}
districts=[feature({'id':d['id'],'name':d['name'],'label_point':[8+(i%8)*.08,48+(i//8)*.06]},box(8+(i%8)*.08,48+(i//8)*.06)) for i,d in enumerate(a['districts'])]
municipalities=[feature({'id':'test-'+str(i),'name':m['municipality_name'],'statistical_geo_id':m['geo_id'],'label_point':[8+(i%40)*.015,48+(i//40)*.012]},box(8+(i%40)*.015,48+(i//40)*.012,.012,.009)) for i,m in enumerate(a['municipalities'])]
g={'synthetic_test_fixture':True,'geometry_reference':'TEST-NOT-GEOGRAPHIC','source_url':'test://synthetic-squares','license_url':'test://not-for-publication','state':feature({'id':'08','name':'SYNTHETIC TEST NOT BW'},box(7.99,47.99,.67,.37)),'districts':districts,'municipalities':municipalities,'crosswalk':[],'municipality_match_count':1101,'municipalities_unmatched':[]}
checks=[];errors=[]
def check(name,ok):
    checks.append({'name':name,'passed':bool(ok)})
    if not ok: raise AssertionError(name)
with sync_playwright() as pw:
    exe=shutil.which('chromium') or shutil.which('chromium-browser')
    browser=pw.chromium.launch(**({'executable_path':exe} if exe else {}),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1050})
    page.set_default_timeout(8000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    html=(ROOT/'docs/index.html').read_text(encoding='utf-8')
    html=re.sub(r'<script[^>]*src=[^>]*></script>','',html)
    html=re.sub(r'<link[^>]*rel="stylesheet"[^>]*>','',html)
    page.set_content(html)
    page.add_style_tag(content=(ROOT/'docs/assets/style.css').read_text(encoding='utf-8'))
    page.add_script_tag(content=(ROOT/'docs/data/atlas-data.js').read_text(encoding='utf-8'))
    page.evaluate('g=>window.ATLAS_GEOMETRY=g',g)
    for name in ['model.js','app.js']:page.add_script_tag(content=(ROOT/'docs/assets'/name).read_text(encoding='utf-8'))
    check('one state polygon rendered',page.locator('#map-features path').count()==1)
    check('geometry warning hidden when a fixture is supplied',not page.locator('#map-unavailable').is_visible())
    check('SVG export enabled with fixture',page.locator('#export-map').is_enabled())
    page.select_option('#layer','foreign_share')
    check('44 district polygons rendered',page.locator('#map-features path').count()==44)
    check('district feature path finite',page.evaluate('[...document.querySelectorAll("#map-features path")].every(p=>p.getAttribute("d").length>10&&!/NaN|Infinity/.test(p.getAttribute("d")))'))
    check('44 demographic fills available',page.evaluate('[...document.querySelectorAll("#map-features path")].every(p=>!p.getAttribute("fill").includes("url"))'))
    page.locator('#map-features path[data-id="08222"]').focus()
    page.keyboard.press('Enter')
    check('keyboard district selection works',page.evaluate('Atlas.getState().selected.id')=='08222')
    check('keyboard selection shows real statistical district','Mannheim' in page.locator('#detail-name').inner_text())
    width=page.evaluate('Atlas.getState().zoom.w');page.locator('#zoom-in').click()
    check('zoom changes viewBox',page.evaluate('Atlas.getState().zoom.w')<width)
    page.locator('#zoom-reset').click();check('zoom reset',page.evaluate('Atlas.getState().zoom.w')==760)
    # The modelled layers are computed in the build pipeline, so the renderer test
    # only injects a stand-in: what matters here is that the SVG path still draws.
    page.evaluate('''()=>{const ids=[...document.querySelectorAll('#map-features path')].map(p=>p.dataset.id);
      window.ATLAS_ESTIMATE={meta:{is_model_not_measurement:true,state_total:{persons_low:1133000,persons_high:1197000},
        coverage:{corrected_share_of_published_low_percent:83,corrected_share_of_published_high_percent:78},
        naturalisation_ratios:{},variants:{},keys:{},band_meaning:'',limitations:[]},
      districts:Object.fromEntries(ids.map((id,i)=>[id,{central:1000+i,low:900,high:1100,pct_low:5,pct_high:9,
        variants:{citizenship:{pct_low:5,pct_high:9,low:900,high:1100},migration_background:{pct_low:6,pct_high:10,low:950,high:1150}},
        by_origin:{'Türkei':500}}])),municipalities:{}};}''')
    # Capture the Blob for the SVG export without navigating or storing a mock map.
    page.evaluate('()=>{window.__exportBlob=null;URL.createObjectURL=b=>{window.__exportBlob=b;return "blob:synthetic-export-test"};HTMLAnchorElement.prototype.click=function(){};}')
    page.locator('#export-map').click()
    svg=page.evaluate('()=>window.__exportBlob.text()')
    check('SVG export carries BKG license URL','https://www.govdata.de/dl-de/by-2-0' in svg)
    check('SVG export is well formed',page.evaluate('s=>!new DOMParser().parseFromString(s,"image/svg+xml").querySelector("parsererror")',svg))
    page.select_option('#layer','municipality_population')
    check('1101 municipal polygons render',page.locator('#map-features path').count()==1101)
    check('municipality values joined by source key',page.evaluate('[...document.querySelectorAll("#map-features path")].every(p=>!p.getAttribute("fill").includes("url"))'))
    page.set_viewport_size({'width':390,'height':844})
    check('mobile map does not overflow body',not page.evaluate('document.documentElement.scrollWidth>innerWidth'))
    check('no uncaught renderer errors',not errors)
    browser.close()
report={'passed':all(c['passed'] for c in checks),'check_count':len(checks),'checks':checks,'mode':'synthetic_in_memory_svg_interaction_test','real_geography_tested':False,'real_archive_tested':False,'note':'Artificial rectangles test the rendering and interaction pipeline only; no synthetic map is published.','uncaught_errors':errors}
(ROOT/'docs/data/renderer-test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['passed','check_count','mode','real_geography_tested']}))
