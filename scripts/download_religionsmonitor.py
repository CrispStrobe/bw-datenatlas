#!/usr/bin/env python3
"""Download freely linked Religionsmonitor PDFs into an ignored local cache.

Catalog entries and checksums stay in inputs/; PDFs retain their source licence
and are not redistributed with the atlas. A download is not a content review.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.parse import urljoin, urlparse
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.bertelsmann-stiftung.de'
CATALOG = BASE + '/de/unsere-projekte/religionsmonitor/publikationen/'
MANIFEST = ROOT / 'inputs/religionsmonitor-publications.json'

class Links(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.urls = set(); self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for key, value in attrs:
                if key == 'href' and value:
                    self.urls.add(urljoin(BASE, value))

def fetch(url, path):
    subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                    '--max-time', '45', '--retry', '1', '--output', str(path), url],
                   check=True, capture_output=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/religionsmonitor')
    args = parser.parse_args(); args.cache.mkdir(parents=True, exist_ok=True)
    prior = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'publications': []}
    pdfs = {r['url'] for r in prior['publications']}
    entries, failures = set(), []
    for page in range(1, 6):
        url = CATALOG + '?tx_rsmbstpublications_pi1%5Bpage%5D=' + str(page) + '&type=372694'
        path = args.cache / f'catalog-{page}.html'
        try:
            fetch(url, path)
            for link in Links(path.read_text()).urls:
                if urlparse(link).path.lower().endswith('.pdf'): pdfs.add(link)
                if '/publikationen/publikation/did/' in link: entries.add(link)
        except (subprocess.CalledProcessError, OSError) as e:
            failures.append({'url': url, 'error': type(e).__name__})
    def inspect(url):
        path = args.cache / ('entry-' + hashlib.sha256(url.encode()).hexdigest()[:16] + '.html')
        try:
            fetch(url, path)
            return url, [u for u in Links(path.read_text()).urls
                         if urlparse(u).path.lower().endswith('.pdf')], None
        except (subprocess.CalledProcessError, OSError) as e:
            return url, [], type(e).__name__
    with ThreadPoolExecutor(max_workers=4) as pool:
        products = list(pool.map(inspect, sorted(entries)))
    for url, links, error in products:
        pdfs.update(links)
        if error: failures.append({'url': url, 'error': error})
    def download(url):
        filename = urlparse(url).path.rsplit('/', 1)[-1]
        path = args.cache / filename
        try:
            if not path.exists(): fetch(url, path)
            data = path.read_bytes()
            if not data.startswith(b'%PDF'): raise ValueError('not a PDF')
            subprocess.run(['pdftotext', '-layout', str(path), str(path.with_suffix('.txt'))],
                           check=True, capture_output=True)
            return {'url': url, 'filename': filename, 'sha256': hashlib.sha256(data).hexdigest(),
                    'bytes': len(data), 'status': 'downloaded', 'review_status': 'not_reviewed'}
        except (subprocess.CalledProcessError, OSError, ValueError) as e:
            return {'url': url, 'status': 'download_failed', 'error': type(e).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        publications = list(pool.map(download, sorted(pdfs)))
    # Preserve an explicitly documented review when refreshing downloads.
    reviews = {r['url']: r for r in prior['publications']}
    for row in publications:
        if row.get('sha256') != reviews.get(row['url'], {}).get('sha256'):
            continue
        for key in ['review_status', 'reviewed_pages', 'used_blocks']:
            if key in reviews.get(row['url'], {}): row[key] = reviews[row['url']][key]
    doc = {'retrieved_on': date.today().isoformat(), 'catalog_url': CATALOG,
           'scope': 'Frei verlinkte PDFs aus fünf Katalogseiten und den verlinkten Publikationsseiten, ergänzt um direkt benannte Studien. Kostenpflichtige Volltexte sind nicht enthalten. Download und inhaltliche Prüfung sind getrennt dokumentiert.',
           'catalog_entries': [{'url': u, 'pdf_links': links} for u, links, _ in products],
           'catalog_failures': failures, 'publications': publications}
    encoded = json.dumps(doc, ensure_ascii=False, indent=2) + '\n'
    MANIFEST.write_text(encoded)
    (ROOT / 'docs/data/religionsmonitor-publications.json').write_text(encoded)
    print(f"{len(entries)} catalog entries; {sum(r['status']=='downloaded' for r in publications)}/{len(publications)} PDFs downloaded; {len(failures)} catalog failures")
    if failures or any(r['status'] != 'downloaded' for r in publications): raise SystemExit(1)

if __name__ == '__main__': main()
