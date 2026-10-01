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
            page.select_option('#population-view', 'states')
            page.locator('nav a[href="#herkunft"]').click()
            page.wait_for_function("document.querySelector('#population-view').value==='origins'")
            assert page.locator('#population-view').input_value() == 'origins'
            assert page.locator('#view-origins').is_visible()
            checks += 3
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
            page.select_option('#basis-view', 'incidents')
            for value in page.eval_on_selector_all('#report-findings-select option', 'els=>els.map(e=>e.value)'):
                page.select_option('#report-findings-select', value)
                report = page.evaluate('id=>window.ATLAS_REPORT_FINDINGS.reports.find(r=>r.id===id)', value)
                assert page.locator('#report-findings-body .bar-row').count() == len(report['items'])
                assert all('%' not in text for text in page.locator('#report-findings-body .bar-value').all_text_contents())
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), value
                if value == 'uem_overview':
                    page.locator('#report-findings-body summary').click()
                    assert page.locator('#report-findings-body .sources-list article').count() == 16
                checks += 3
            page.select_option('#basis-view', 'bases')
            for value in page.eval_on_selector_all('#survey-select option', 'els=>els.map(e=>e.value)'):
                page.select_option('#survey-select', value)
                block = page.evaluate('n=>window.ATLAS_SURVEY_ITEMS.blocks[Number(n)]', value)
                assert page.locator('#survey-blocks table tbody tr').count() >= len(block['items'])
                kind = block.get('chart', {}).get('kind')
                if kind == 'distribution':
                    assert page.locator('#survey-blocks .survey-stack').count() == len(block['chart']['rows'])
                elif kind == 'time':
                    assert page.locator('#survey-blocks .survey-time circle').count() == len(block['items'])*(1+len(block['chart'].get('related', [])))
                else:
                    assert page.locator('#survey-blocks .bar-row').count() >= len(block['items'])
                page.locator('#survey-enlarge').click()
                assert page.locator('#chart-zoom').evaluate('el=>el.open')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                page.locator('#chart-zoom-close').click()
                checks += 3
                if block['block'].startswith('evs2017_'):
                    assert page.locator('#survey-blocks table th').filter(has_text='Gültige Antworten').count() == 0
                    assert all(i['source_kind'] == 'published_table' for i in block['items'])
                    if len({i['question_ref'] for i in block['items']}) > 1:
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
