"""Rights notices for selected study results; no grant of third-party rights."""


def export_rights():
    return {
        'license': None,
        'license_status': 'no_blanket_open_license',
        'atlas_material': {
            'license': 'MIT',
            'scope': 'Eigene Erläuterungen und etwaige eigene Rechte an Auswahl und Anordnung.',
        },
        'third_party_material': {
            'relicensed_by_atlas': False,
            'scope': 'Etwaige Rechte an übernommenen Quelleninhalten und Zusammenstellungen.',
        },
        'notice': (
            'Dieser Export enthält ausgewählte veröffentlichte Ergebnisse verschiedener Quellen. '
            'Es wird keine pauschale offene Lizenz für sämtliche Inhalte vergeben. '
            'Die MIT-Lizenz erfasst nur eigenes Material und eigene Rechte des Atlas. '
            'Etwaige Rechte Dritter bleiben unberührt. Ungeschützte Tatsachen werden durch '
            'diesen Hinweis nicht mit neuen Nutzungsbeschränkungen belegt. '
            'Quellen, Fundstellen und Bezugszeiträume sind bei Weiterverwendung zu berücksichtigen.'
        ),
        'documentation_url': 'https://github.com/CrispStrobe/bw-datenatlas/blob/main/DATA_LICENSES.md',
        'source_license_null_means': (
            'Eine Quellenlizenz ist in diesem Export nicht dokumentiert. '
            'Dies bedeutet weder Gemeinfreiheit noch ein Verbot der Nutzung einzelner Tatsachen.'
        ),
    }


def source_rights():
    return {
        'license': None,
        'license_status': 'not_recorded_in_export',
        'relicensed_by_atlas': False,
    }
