# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : osint_report.py
# Role          : Export Markdown local du dossier verifie
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Rapport local déterministe depuis un dossier et son journal vérifiés."""
import json
import installation
from conversation import sanitize_prompt_data


def _literal(value):
    # Blocs indentés : aucune donnée ne devient titre, lien ou HTML actif.
    text = sanitize_prompt_data(str(value))
    return '\n'.join('    '+line for line in text.split('\n'))


def render_report(manager):
    status = manager.status()
    entries = manager.read_journal()
    import json
    state = manager._verify_case(json.loads((manager.case_dir() / 'case.json').read_text(encoding='utf-8')), manager.active_case_id)
    lines = ['# Rapport OSINT — UCHAMBUZI', '', '## Dossier', '',
             _literal(status['case_id']), '', '## Cadre de l’enquête', '',
             _literal(state.get('investigation_framework') or 'Non renseigné'), '',
             '## Indices', '', _literal(json.dumps(state['indicators'], ensure_ascii=False, sort_keys=True, indent=2)), '',
             '## Commandes exécutées', '']
    for entry in entries:
        if entry['event_type'] == 'command_executed':
            lines.extend([_literal(json.dumps(entry['details'], ensure_ascii=False, sort_keys=True, indent=2)), ''])
    lines.extend(['## Constats qualifiés', ''])
    for finding in state.get('findings', []):
        lines.extend([_literal(json.dumps(finding, ensure_ascii=False, sort_keys=True, indent=2)), ''])
    lines.extend(['## Empreintes SHA-256', '', _literal('État : '+status['sha256'])])
    for entry in entries:
        lines.append(_literal(str(entry['seq'])+' '+entry['event_type']+' : '+entry['sha256']))
    lines.extend(['', '## Limites', '', status['integrity_limitations'], '',
                  'Les constats sont qualifiés par l’enquêteur ; aucune certitude n’est promue automatiquement. '
                  'Les données externes restent non fiables. Une absence de résultat ne prouve pas une absence de fait.', ''])
    return '\n'.join(lines)


def export_report(manager):
    report = render_report(manager)
    target = manager.case_dir() / 'report.md'
    installation.no_links(target)
    installation.atomic_write(target, report.encode('utf-8'), 0o600)
    return target
