#!/usr/bin/env python3
"""Build selected public incident statistics and the UEM research index."""
import json
from pathlib import Path
from urllib.parse import urlsplit
try:
    from .export_rights import export_rights, source_rights
except ImportError:
    from export_rights import export_rights, source_rights

ROOT = Path(__file__).resolve().parents[1]


def validate(doc):
    ids = [r['id'] for r in doc['reports']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate report IDs')
    for report in doc['reports']:
        for source in report['sources']:
            if urlsplit(source['url']).scheme != 'https' or not source['locator']:
                raise ValueError('Missing public source or locator')
        for item in report['items']:
            if item['unit'] != 'count' or not isinstance(item['value'], int) or item['value'] < 0:
                raise ValueError('Incident statistics must be non-negative integer counts')
        if 'total' in report and sum(i['value'] for i in report['items']) != report['total']:
            raise ValueError('Incident types do not reconcile with the source total')
    if len(doc['uem_studies']) != 16:
        raise ValueError('UEM study inventory must cover the 16 commissioned studies/reports')


def main():
    doc = json.loads((ROOT / 'inputs/report-findings.json').read_text())
    validate(doc)
    doc['schema_version'] = '1.1'
    doc['rights'] = export_rights()
    for report in doc['reports']:
        for source in report['sources']:
            source['source_rights'] = source_rights()
    for study in doc['uem_studies']:
        study['source_rights'] = source_rights()
    text = json.dumps(doc, ensure_ascii=False, indent=2) + '\n'
    (ROOT / 'docs/data/report-findings.json').write_text(text)
    (ROOT / 'docs/data/report-findings-data.js').write_text('window.ATLAS_REPORT_FINDINGS = ' + text.rstrip() + ';\n')
    print(f"{len(doc['reports'])} Berichtsansichten; {len(doc['uem_studies'])} UEM-Unterstudien")


if __name__ == '__main__':
    main()
