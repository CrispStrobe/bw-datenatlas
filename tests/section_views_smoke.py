"""Exercise every consolidated view and source deep link on desktop and phone."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(QuietHandler, directory=str(ROOT / 'docs')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
checks = 0
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width in (1440, 375):
            page = browser.new_page(viewport={'width': width, 'height': 950}, locale='de-DE')
            errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{srv.server_port}/?lang=de')
            page.wait_for_function('window.Atlas && window.ATLAS_SURVEY_ITEMS')
            ids = page.eval_on_selector_all('[id]', 'els=>els.map(e=>e.id)')
            assert len(ids) == len(set(ids)), 'duplicate IDs'
            assert page.eval_on_selector_all('main>section[id]', 'els=>els.map(e=>e.id)') == [
                'karte', 'herkunft', 'befragungen', 'grundlagen']
            assert page.locator('#population-view').input_value() == 'origins'
            assert page.locator('#map-bamf-definition').is_hidden()
            page.select_option('#layer', 'religion_estimate')
            assert page.locator('#map-bamf-definition').is_visible()
            page.select_option('#layer', 'district_population')
            assert page.locator('#map-bamf-definition').is_hidden()
            page.select_option('#population-view', 'states')
            page.locator('nav a[href="#herkunft"]').click()
            page.wait_for_function("document.querySelector('#population-view').value==='origins'")
            assert page.locator('#population-view').input_value() == 'origins'
            assert page.locator('#view-origins').is_visible()
            assert page.locator('#view-incidents').locator('xpath=ancestor::section').get_attribute('id') == 'herkunft'
            assert page.locator('#view-estimates').locator('xpath=ancestor::section').get_attribute('id') == 'herkunft'
            assert page.locator('#basis-view option[value=incidents], #basis-view option[value=estimates]').count() == 0
            checks += 6
            assert page.locator('#all-origins').locator('xpath=ancestor::*[contains(@class, "chart-card")]').count() == 1
            method_link = page.locator('.kpi.is-estimate a[href="#bamf-methodik"]')
            assert method_link.count() == 1
            method_link.click()
            assert page.locator('#bamf-methodik').is_visible()
            assert 'Mikrozensus 2025' in page.locator('#bamf-methodik').inner_text()
            method_text = page.locator('#bamf-methodik').inner_text()
            assert 'keine Zahlen praktizierender' in method_text
            assert 'Veränderungen der religiösen Selbstzuordnung seit 2019' in method_text
            assert 'Erhebungen bis 2013' in method_text
            assert page.locator('#sources-list a[href="https://mediendienst-integration.de/fileadmin/Dateien/Muslime_Spielhaus_MDI.pdf"]').count() == 1
            page.select_option('#population-view', 'origins')
            checks += 8
            for field in ('population-view', 'basis-view'):
                selected = page.locator('#' + field).input_value()
                section = page.locator('#' + field).locator('xpath=ancestor::section')
                assert section.locator('.view-panel:visible').count() == 1
                for value in page.eval_on_selector_all('#' + field + ' option', 'els=>els.map(e=>e.value)'):
                    page.select_option('#' + field, value)
                    page.wait_for_timeout(140)
                    assert section.locator('.view-panel:visible').count() == 1, value
                    assert page.locator('#view-' + value).is_visible(), value
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), value
                    checks += 3
                page.select_option('#' + field, selected)
            page.select_option('#population-view', 'incidents')
            for value in page.eval_on_selector_all('#report-findings-select option', 'els=>els.map(e=>e.value)'):
                page.select_option('#report-findings-select', value)
                report = page.evaluate('id=>window.ATLAS_REPORT_FINDINGS.reports.find(r=>r.id===id)', value)
                assert page.locator('#report-findings-body .bar-row').count() == len(report.get('time_series', report['items']))
                assert all('%' not in text for text in page.locator('#report-findings-body .bar-value').all_text_contents())
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), value
                assert value not in ('uem_overview', 'bw_antisemitism_schools')
                assert page.locator('#report-findings-body .notice').evaluate(
                    "el=>!!(el.compareDocumentPosition(document.querySelector('#report-findings-body .horizontal-bars')) & Node.DOCUMENT_POSITION_PRECEDING)")
                checks += 3
            page.select_option('#population-view', 'origins')
            page.select_option('#basis-view', 'bases')
            for value in page.eval_on_selector_all('#survey-select option', 'els=>els.map(e=>e.value)'):
                page.select_option('#survey-select', value)
                block = page.evaluate('n=>window.ATLAS_SURVEY_ITEMS.blocks[Number(n)]', value)
                sources = page.evaluate('''b=>{
                    const all=window.ATLAS_SURVEY_ITEMS.blocks,seen=new Set();
                    const visit=b=>{
                        if(seen.has(b.block))return [];
                        seen.add(b.block);
                        return [b,...(b.chart?.related||[]).flatMap(id=>visit(all.find(x=>x.block===id)))];
                    };
                    return visit(b);
                }''', block)
                assert page.locator('#survey-blocks .compact-details table tbody tr').count() == sum(len(b['items']) for b in sources), block['block']
                kind = block.get('chart', {}).get('kind')
                if kind == 'collection':
                    assert page.locator('#survey-blocks > .survey-panel').count() == len(block['chart']['panels'])
                    if block['block'] == 'rm2026_zusammenhalt':
                        dimensions = page.locator('#survey-blocks .survey-panel[data-block="rm2026_dimensions"]')
                        dimensions.evaluate('el=>el.open=true')
                        assert dimensions.locator('.survey-matrix tbody td').count() == 36
                        assert dimensions.locator('.survey-matrix tbody tr').nth(2).locator('td').all_text_contents() == ['62,0 Punkte', '66,0 Punkte', '47,0 Punkte', '55,0 Punkte']
                        questions = page.locator('#survey-blocks > .survey-question-details')
                        assert questions.count() == 1
                        assert not questions.evaluate('el=>el.open')
                        assert dimensions.evaluate("el=>!!(el.querySelector('.survey-matrix').compareDocumentPosition(document.querySelector('#survey-blocks > .survey-question-details')) & Node.DOCUMENT_POSITION_FOLLOWING)")
                        questions.locator('summary').click()
                        assert 'zunehmende Vielfalt' in questions.inner_text()
                        assert 'Bundesregierung' in questions.inner_text()
                        checks += 6
                    if block['block'] == 'fgz2023_network_religion':
                        model = page.locator('#survey-blocks .survey-panel[data-block="fgz2025_trust_region"]')
                        model.evaluate('el=>el.open=true')
                        assert model.locator('.survey-dot-row').count() == 2
                        assert model.locator('.survey-key').count() == 1
                        assert 'nicht statistisch signifikant' in model.inner_text()
                        assert 'Erfasste Merkmale laut Methodenbericht' in model.inner_text()
                        positions = model.locator('.survey-dot').evaluate_all('els=>els.map(el=>parseFloat(el.style.left))')
                        assert positions[0] < 50 < positions[1]
                        assert '%' not in model.locator('.survey-dot-values').first.inner_text()
                        checks += 6
                    if block['block'] == 'rm2017_wahrheit':
                        country = page.locator('#survey-blocks .survey-panel[data-block="rm_countries_kernel"]')
                        country.evaluate('el=>el.open=true')
                        assert country.locator('.survey-matrix tbody td').count() == 12
                        assert country.locator('.survey-matrix tbody tr').nth(1).locator('td').first.inner_text() == 'nicht publiziert'
                        assert '72,0 %' in country.locator('.survey-matrix tbody tr').first.inner_text()
                        youth = page.locator('#survey-blocks .survey-panel[data-block="empirica2018_truth"]')
                        youth.evaluate('el=>el.open=true')
                        assert youth.locator('.survey-dot-row').count() == 4
                        assert '%' not in youth.locator('.survey-dot-scale').inner_text()
                        assert '1,0' in youth.locator('.survey-dot-scale').inner_text()
                        positions = youth.locator('.survey-dot').evaluate_all('els=>els.map(el=>parseFloat(el.style.left))')
                        assert abs(positions[0] - 42.5) < .001 and abs(positions[1] - 70) < .001
                        assert youth.locator('.survey-key').count() == 1
                        checks += 8
                    if block['block'] == 'pollack2010_model':
                        panel = page.locator('#survey-blocks .survey-panel').first
                        positions = panel.locator('.survey-dot').evaluate_all('els=>els.map(el=>parseFloat(el.style.left))')
                        assert len(positions) == 10
                        assert abs(positions[0] - 96.1667) < .001
                        assert positions[4] < 50 and positions[5] < 50
                        values = panel.locator('.survey-dot-values').all_text_contents()
                        assert '-0,170' in values[2] and '+0,113' in values[1]
                        assert all('%' not in value for value in values)
                        assert '-0,300' in panel.locator('.survey-dot-scale').inner_text()
                        checks += 6
                elif kind == 'responses':
                    assert page.locator('#survey-blocks .survey-stack').count() == len(block['items'])
                elif kind == 'distribution':
                    assert page.locator('#survey-blocks .survey-stack').count() == len(block['chart']['rows'])
                elif kind == 'matrix':
                    assert page.locator('#survey-blocks .survey-matrix tbody td').count() == len(block['items'])
                elif kind == 'compare' and block['chart'].get('layout') == 'dots':
                    assert page.locator('#survey-blocks .survey-dot-row').count() == len(block['items'])
                elif kind == 'time':
                    assert page.locator('#survey-blocks .survey-time circle').count() == len(block['items'])*(1+len(block['chart'].get('related', [])))
                else:
                    assert page.locator('#survey-blocks .bar-row').count()+page.locator('#survey-blocks .survey-distribution, #survey-blocks .survey-compact-row').count() >= len(block['items'])
                assert page.locator('#survey-blocks > .survey-evidence').count() == 1
                for diagram in page.locator('#survey-blocks .survey-shared-distributions').all():
                    assert diagram.locator('.survey-key').count() == 1
                if block['block'] == 'fes2025_migration':
                    assert page.locator('#survey-blocks .survey-country-group').count() == 5
                    assert 'Sozialsystem auszunutzen' in page.locator('#survey-blocks').inner_text()
                    assert page.locator('#survey-blocks table th').filter(has_text='Antwortverteilung').count() == 1
                    assert '19,1 %' in page.locator('#survey-blocks table').text_content()
                if block['block'] == 'fundamentalismus_sciics':
                    first_panel = page.locator('#survey-blocks .survey-panel').first
                    assert first_panel.locator('.survey-dot-row').count() == 6
                    assert first_panel.locator('.survey-dot').count() == 12
                    assert '49,9 %' in first_panel.inner_text()
                    assert '20,5 %' in first_panel.inner_text()
                    assert 'Wurzeln' in first_panel.locator('.survey-question').inner_text()
                if block['block'] == 'rias2026_muslim_antisemitismus':
                    assert page.locator('#survey-blocks .survey-key').count() == 1
                    assert 'kein Recht zu existieren' in page.locator('#survey-blocks .survey-panel[data-block="rias2026_muslim_antisemitismus"] .survey-question').inner_text()
                    assert '34,8 %' in page.locator('#survey-blocks table:not(.survey-matrix)').text_content()
                    assert '712' in page.locator('#survey-blocks table:not(.survey-matrix)').text_content()
                if block['block'] == 'evs2017_zugehoerigkeit':
                    assert 'wirklich deutsch' in page.locator('#survey-blocks .survey-question').inner_text()
                page.locator('#survey-enlarge').click()
                assert page.locator('#chart-zoom').evaluate('el=>el.open')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.locator('#chart-zoom-close').click()
                checks += 3
                if block['block'].startswith('evs2017_'):
                    assert page.locator('#survey-blocks table th').filter(has_text='Gültige Antworten').count() == 0
                    assert all(i['source_kind'] == 'published_table' for i in block['items'])
                    if kind != 'collection' and len({i['question_ref'] for i in block['items']}) > 1:
                        assert 'Fragen ' not in page.locator('#survey-blocks .survey-meta').inner_text()
                    checks += 2
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), value
                checks += 3
            assert not page.locator('#source-directory').get_attribute('open')
            page.evaluate("location.hash='source-bamf_fb55'")
            page.wait_for_timeout(200)
            assert page.locator('#source-bamf_fb55').is_visible()
            page.evaluate("location.hash='pyramid-card'")
            page.wait_for_timeout(250)
            assert page.locator('#pyramid-card').is_visible()
            assert page.locator('#population-view').input_value() == 'pyramid'
            for anchor, field, value in [('kontext', 'population-view', 'flows'),
                                          ('published-estimates-card', 'population-view', 'estimates'),
                                          ('view-incidents', 'population-view', 'incidents'),
                                          ('daten', 'basis-view', 'downloads'),
                                          ('methodik', 'basis-view', 'method'),
                                          ('quellen', 'basis-view', 'sources')]:
                page.evaluate(f"location.hash='{anchor}'")
                page.wait_for_timeout(200)
                assert page.locator('#' + field).input_value() == value
                assert page.locator('#view-' + value).is_visible()
                checks += 2
            assert not errors, errors
            checks += 5
            out = ROOT / 'test-results'; out.mkdir(exist_ok=True)
            for field, value in [('population-view', 'origins'),
                                 ('basis-view', 'bases'), ('survey-select', '0')]:
                page.select_option('#' + field, value)
            page.eval_on_selector('#source-directory', 'el=>el.open=false')
            page.evaluate("location.hash='herkunft'")
            page.wait_for_timeout(200)
            page.screenshot(path=str(out / f'consolidated-{width}.png'), full_page=True)
            page.close()
        browser.close()
finally:
    srv.shutdown()
print(json.dumps({'passed': True, 'checks': checks}))
