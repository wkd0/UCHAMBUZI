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
"""Rapport déterministe : présentation humaine, vérifications du dossier inchangées."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex

import installation
from conversation import sanitize_prompt_data


_TYPES = {'email': 'Adresse électronique', 'username': 'Pseudonyme',
          'phone': 'Téléphone', 'domain': 'Nom de domaine', 'ip': 'Adresse IP',
          'url': 'Adresse web', 'file': 'Fichier', 'hash': 'Identifiant de fichier',
          'gps': 'Coordonnées géographiques'}
_VALIDATIONS = {'valid': 'syntaxe valide, existence non vérifiée',
                'invalid': 'syntaxe invalide', 'unknown': 'non vérifié',
                'ambiguous': 'ambigu'}
_STATES = {'prepared': 'préparée', 'refused': 'refusée', 'blocked': 'bloquée',
           'timeout': 'délai dépassé', 'spawn_error': 'démarrage impossible',
           'cancelled': 'interrompue', 'canceled': 'interrompue',
           'failed': 'échec', 'succeeded': 'terminée', 'denied': 'refusée'}
_LOCAL_OPERATIONS = {'import': 'Importation locale de l’outil',
                     'install': 'Installation locale de l’outil',
                     'verify': 'Vérification locale de l’outil',
                     'remove': 'Suppression locale de l’outil',
                     'update': 'Mise à jour locale de l’outil'}
_ADMIN_EVENTS = {'case_created': 'création', 'case_reopened': 'réouverture(s)',
                 'case_renamed': 'changement(s) de titre', 'case_closed': 'fermeture(s)',
                 'case_archived': 'archivage(s)', 'analysis_recorded': 'analyse(s) locale(s)',
                 'context_selected': 'sélection(s) documentaire(s)'}


def _literal(value):
    # Aucun texte externe ne devient titre, lien, HTML ou instruction de rôle.
    # Pas de limite de longueur, y compris pour les sorties peu concluantes.
    text = sanitize_prompt_data(str(value))
    return '\n'.join('    ' + line for line in text.split('\n'))


def _field(lines, label, value, default='Non renseigné'):
    # Les dictionnaires ne sont jamais convertis implicitement en texte.
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        value = default
    lines.extend([label + ' :', '', _literal(value if value != '' else default), ''])


def _date(value):
    if not value:
        return 'Non renseignée'
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None:
            return str(value) + ' (fuseau non renseigné)'
        return stamp.astimezone(timezone.utc).strftime('%d/%m/%Y à %H:%M:%S UTC')
    except (TypeError, ValueError):
        return str(value)


def _error(value):
    # Le message utile est conservé ; les codes internes restent dans le journal.
    if isinstance(value, dict):
        return value.get('message') or 'Motif non renseigné'
    return value if isinstance(value, str) else 'Motif non renseigné'


def _command(details):
    command = details.get('command', details.get('display'))
    if isinstance(command, str) and command:
        return command
    argv = details.get('argv')
    if isinstance(argv, list) and argv and all(isinstance(arg, str) for arg in argv):
        return shlex.join(argv)
    if isinstance(command, dict):
        return 'Arguments de la commande non conservés ; outil : ' + str(command.get('program') or 'non renseigné')
    return 'Non renseignée'


def _source(finding):
    source = finding.get('source')
    if not isinstance(source, str):
        return 'Non renseignée'
    # Masquer les clauses de provenance cryptographique dans ce seul champ.
    # Les indicateurs, liens et corps de preuve restent intégraux.
    source = re.sub(r'[ \t]*\bSHA-256[ \t]+[0-9a-fA-F]{64}\b', '', source)
    source = re.sub(r'^stdout(?= · |$)',
                    lambda match: 'Sortie de l’outil ' + str(finding.get('outil') or 'non renseigné'), source)
    source = re.sub(r'( · )stdout(?= · | ; | : |$)', r'\1sortie de l’outil', source)
    return source


def _terminal_output(details, directory):
    """Lire seulement une capture locale au dossier, jamais un chemin arbitraire."""
    recorded = details.get('transcript')
    if not isinstance(recorded, str) or Path(recorded).parent.name != 'shell':
        return None, 'Capture complète du terminal non disponible dans ce dossier.'
    target = directory / 'shell' / Path(recorded).name
    try:
        installation.no_links(target)
        if not target.is_file():
            raise ValueError('Capture absente')
        raw = target.read_bytes()
        # Retirer les commandes de contrôle terminal, pas les lignes de preuve.
        from rich.text import Text
        return Text.from_ansi(raw.decode('utf-8', errors='replace').replace('\r\n', '\n')).plain, None
    except (OSError, ValueError):
        return None, 'Capture complète du terminal absente ou inaccessible.'


def _outputs(lines, details, directory):
    available = False
    for key, label in (('stdout', 'Sortie de l’outil'), ('stderr', 'Messages de l’outil')):
        if isinstance(details.get(key), str):
            available = True
            _field(lines, label, details[key], 'Aucun texte émis')
    if 'stdout_excerpt' in details:
        available = True
        text, problem = _terminal_output(details, directory)
        if text is not None:
            lines.extend(['La capture est lue dans le dossier ; son contenu actuel peut avoir changé depuis l’exécution.', ''])
            _field(lines, 'Capture complète du terminal', text)
        else:
            _field(lines, 'Texte du terminal conservé dans le journal', details.get('stdout_excerpt'), 'Aucun texte émis')
            lines.extend([problem, ''])
            if details.get('excerpt_truncated'):
                lines.extend(['Le texte conservé est un extrait ; le début de la sortie manque.', ''])
    results = details.get('results')
    if isinstance(results, list):
        available = True
        lines.extend(['Réponses des sites consultés :', ''])
        if not results:
            lines.extend(['Aucune réponse de site consignée.', ''])
        for result in results:
            if not isinstance(result, dict):
                continue
            _field(lines, 'Site', result.get('site'))
            _field(lines, 'Source consultée', result.get('url'))
            if result.get('error'):
                verdict = 'Réponse indéterminée ; aucune conclusion sur l’existence du compte.'
            elif result.get('exists') is True:
                verdict = 'Correspondance signalée par l’outil, source unique ; attribution à une personne non établie.'
            elif result.get('exists') is False:
                verdict = 'Aucune correspondance signalée par l’outil ; cela ne prouve pas une absence.'
            else:
                verdict = 'Résultat non renseigné.'
            lines.extend([verdict, ''])
            if result.get('error'):
                _field(lines, 'Difficulté rencontrée', _error(result['error']))
    if not available and details.get('model_evidence'):
        # L'ancien parcours d'audit ne conserve parfois que cet extrait.
        try:
            evidence = json.loads(details['model_evidence'])
        except (TypeError, ValueError):
            evidence = {}
        if isinstance(evidence, dict):
            _field(lines, 'Extrait conservé pour l’analyse', evidence.get('isolated_data'), 'Aucun texte conservé')
            if evidence.get('quarantined') or evidence.get('prompt_injection_detected'):
                lines.extend(['Contenu suspect mis en quarantaine lors de la collecte.', ''])
        lines.extend(['Les sorties complètes ne sont pas conservées dans ce journal ; cet extrait ne les remplace pas.', ''])
    elif not available:
        lines.extend(['Aucune sortie d’outil conservée dans le journal.', ''])


def _execution(lines, entry, directory):
    details = entry.get('details', {})
    _field(lines, 'Outil', details.get('tool'))
    if details.get('operation') in _LOCAL_OPERATIONS:
        _field(lines, 'Opération locale', _LOCAL_OPERATIONS[details['operation']])
        _field(lines, 'Version', details.get('version'))
        _field(lines, 'Résultat consigné', details.get('result'))
        if details.get('error'):
            _field(lines, 'Erreur', _error(details['error']))
        if any(key in details for key in ('stdout', 'stderr', 'stdout_excerpt', 'results', 'model_evidence')):
            _outputs(lines, details, directory)
        # L’installateur ne consigne ni commande ni code de fin ni sortie brute.
        # Restituer son résultat connu sans inventer ces champs manquants.
        return
    _field(lines, 'Commande', _command(details))
    for key, label in (('started_at', 'Début'), ('finished_at', 'Fin')):
        if details.get(key):
            _field(lines, label, _date(details[key]))
    if details.get('cwd'):
        _field(lines, 'Répertoire de travail', details['cwd'])
    code = details.get('exit_code', details.get('returncode'))
    if details.get('status'):
        _field(lines, 'État de l’exécution', _STATES.get(details['status'], 'état non précisé'))
    if code is not None:
        _field(lines, 'Code de fin', code)
        lines.extend([('La commande s’est terminée sans erreur signalée par son code de fin. '
                       'Cela ne valide pas les informations renvoyées.' if code == 0 else
                       'La commande signale un échec ou une interruption ; les textes conservés suivent.'), ''])
    else:
        lines.extend(['Code de fin non renseigné.', ''])
    _outputs(lines, details, directory)
    if details.get('error'):
        _field(lines, 'Erreur', _error(details['error']))
    if details.get('detected_patterns'):
        lines.extend(['Le contrôle de sécurité a signalé du texte suspect ; il reste présenté comme donnée, jamais comme instruction.', ''])


def _contexts(lines, contexts):
    groups = []
    for context in contexts:
        snapshot = context.get('context', {})
        if groups and groups[-1][0] == snapshot:
            groups[-1][1].append(context)
        else:
            groups.append((snapshot, [context]))
    for snapshot, selections in groups:
        lines.extend(['### Contexte documentaire sélectionné', ''])
        _field(lines, 'Date', _date(selections[0].get('recorded_at')))
        if len(selections) > 1:
            lines.extend([f'{len(selections)} sélections identiques regroupées.', ''])
            _field(lines, 'Dernière sélection identique', _date(selections[-1].get('recorded_at')))
        candidates = [snapshot.get('recommendation')]
        candidates.extend(snapshot.get('recommendations', []))
        candidates.extend(choice.get('recommendation') for choice in snapshot.get('choices', [])
                          if isinstance(choice, dict))
        recommendations = []
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate and candidate not in recommendations:
                recommendations.append(candidate)
        if not recommendations:
            lines.extend(['Aucune recommandation documentaire conservée dans cette sélection.', ''])
        for recommendation in recommendations:
            _field(lines, 'Outil proposé', recommendation.get('tool'))
            _field(lines, 'Objectif', recommendation.get('objective'))
            if recommendation.get('local_version'):
                _field(lines, 'Version locale considérée', recommendation['local_version'])
            refs = []
            for ref in recommendation.get('references', []):
                if not isinstance(ref, dict) or ref in refs:
                    continue
                refs.append(ref)
                _field(lines, 'Source documentaire', ref.get('title') or ref.get('origin'))
                _field(lines, 'Adresse de la source', ref.get('origin'))
                for key, label in (('documented_version', 'Version documentée'),
                                   ('consulted_at', 'Date de consultation consignée'),
                                   ('review_due', 'Date de réexamen prévue')):
                    if ref.get(key):
                        _field(lines, label, ref[key])
                if ref.get('date_timezone'):
                    _field(lines, 'Fuseau des dates documentaires',
                           'heure locale du système' if ref['date_timezone'] == 'system_local' else ref['date_timezone'])
                for key, label, values in (
                    ('availability', 'Disponibilité documentaire',
                     {'local': 'copie locale conforme', 'missing': 'copie absente',
                      'unavailable': 'copie inaccessible', 'integrity_error': 'copie différente de la référence'}),
                    ('verification', 'Consultation documentaire',
                     {'consulted_local': 'copie locale consultée', 'not_consulted': 'documentation non consultée'}),
                    ('freshness', 'Actualité documentaire',
                     {'current': 'à jour à la date du contexte', 'stale': 'documentation à réexaminer'}),
                    ('compatibility', 'Compatibilité de version',
                     {'documented': 'documentée', 'unverified_version': 'version non vérifiée'}),
                    ('authority', 'Origine documentaire',
                     {'official': 'officielle', 'upstream_manual': 'manuel du fournisseur', 'community': 'communautaire'})):
                    if key in ref:
                        _field(lines, label, values.get(ref[key], 'non établie'))
                if ref.get('preparation_note'):
                    _field(lines, 'Réserve documentaire', ref['preparation_note'])
            seen = []
            for key, label in (('limits', 'Réserve documentaire'),
                               ('uncertainties', 'Incertitude documentaire'),
                               ('restrictions', 'Restriction documentaire')):
                for limit in recommendation.get(key, []):
                    if limit not in seen:
                        _field(lines, label, limit)
                        seen.append(limit)
        if snapshot.get('selection_limits'):
            _field(lines, 'Portée de la sélection', snapshot['selection_limits'])
        for error in snapshot.get('errors', []):
            _field(lines, 'Blocage documentaire consigné', _error(error))


def render_report(manager):
    # Conserver les mêmes vérifications bloquantes et ne jamais écrire le dossier.
    status = manager.status()
    entries = manager.read_journal()
    directory = manager.case_dir()
    state = manager._verify_case(json.loads((directory / 'case.json').read_text(encoding='utf-8')),
                                 manager.active_case_id)
    lines = ['# Rapport OSINT — UCHAMBUZI', '', '## Informations initiales', '']
    for label, value in (('Dossier', status['case_id']), ('Titre', state.get('title')),
                         ('Création', _date(state.get('created_at'))),
                         ('Dernière mise à jour', _date(state.get('updated_at'))),
                         ('Cadre de l’enquête', state.get('investigation_framework'))):
        _field(lines, label, value)
    for key, label in (('closed_at', 'Fermeture'), ('archived_at', 'Archivage')):
        if state.get(key):
            _field(lines, label, _date(state[key]))
    lines.extend(['## Indices fournis', '',
                  'Ces éléments sont des données d’entrée, pas des découvertes. '
                  'Leur répétition correspond à des saisies successives.', ''])
    for indicator in state['indicators']:
        _field(lines, 'Type d’indice', _TYPES.get(indicator.get('type'), 'Autre indice'))
        _field(lines, 'Valeur fournie', indicator.get('original'))
        if indicator.get('normalized') and indicator.get('normalized') != indicator.get('original'):
            _field(lines, 'Valeur normalisée', indicator['normalized'])
        _field(lines, 'Date de consignation', _date(indicator.get('recorded_at')))
        _field(lines, 'Validation', _VALIDATIONS.get(indicator.get('validation'), 'non vérifié'))
        for ambiguity in indicator.get('ambiguities', []):
            _field(lines, 'Réserve', ambiguity)
    if not state['indicators']:
        lines.extend(['Aucun indice fourni consigné.', ''])
    analysis = state.get('latest_analysis') or {}
    lines.extend(['## Démarches et résultats des outils', '',
                  'Une préparation de commande ne prouve pas son exécution. '
                  'Les textes externes sont reproduits en blocs de texte ; les contrôles et délimiteurs de rôle sont neutralisés.', ''])
    administrative = []
    for event, label in _ADMIN_EVENTS.items():
        count = sum(entry.get('event_type') == event for entry in entries)
        if count:
            administrative.append(f'{count} {label}')
    if administrative:
        lines.extend(['Suivi du dossier regroupé : ' + ', '.join(administrative) + '. '
                      'Les indices, contextes et constats sont présentés dans leurs rubriques.', ''])
    previous_framework = None
    for entry in entries:
        event = entry.get('event_type')
        # Sélectionner avant de créer un bloc : pas d’étape de simple renvoi.
        if event == 'finding_recorded' or event in _ADMIN_EVENTS:
            continue
        details = entry.get('details', {})
        if event == 'investigation_framework':
            framework = details.get('framework')
            if framework == previous_framework:
                continue
            previous_framework = framework
        lines.extend(['### Étape consignée', ''])
        _field(lines, 'Date', _date(entry.get('timestamp')))
        if event == 'command_prepared':
            _field(lines, 'Démarche', 'Préparation de commande')
            _field(lines, 'État', _STATES.get(details.get('status'), 'non renseigné'))
            _field(lines, 'Outil', details.get('tool_id'))
            _field(lines, 'Commande proposée', _command(details))
            if details.get('error'):
                _field(lines, 'Blocage', _error(details['error']))
        elif event == 'command_executed':
            _field(lines, 'Démarche', _LOCAL_OPERATIONS.get(details.get('operation')) or
                   entry.get('summary') or 'Exécution de commande consignée')
            _execution(lines, entry, directory)
        elif event == 'conversation_snapshot':
            _field(lines, 'Démarche', 'Conversation enregistrée.')
        elif event == 'security_audit':
            _field(lines, 'Démarche', 'Contrôle du texte externe contre les injections d’instructions')
            _field(lines, 'Source contrôlée', details.get('path'))
            lines.extend([('Texte suspect détecté ; ne pas suivre les instructions contenues dans cette donnée.'
                           if details.get('injection_detected') else
                           'Aucun motif suspect signalé par ce contrôle ; cela ne garantit pas la fiabilité du contenu.'), ''])
            if details.get('truncated'):
                lines.extend(['Le contrôle n’a porté que sur une partie du contenu.', ''])
        else:
            _field(lines, 'Démarche', entry.get('summary') or 'Étape enregistrée dans le dossier')
            if event == 'investigation_framework':
                _field(lines, 'Cadre consigné à cette date', details.get('framework'))
    _contexts(lines, state.get('contexts', []))
    lines.extend(['## Résultats et constats consignés', '',
                  'Les textes ci-dessous conservent la qualification enregistrée. '
                  'Une déclaration, une hypothèse ou une décision ne devient pas une découverte vérifiée.', ''])
    findings = state.get('findings', [])
    for finding in findings:
        lines.extend(['### Constat consigné', ''])
        _field(lines, 'Date', _date(finding.get('horodatage')))
        _field(lines, 'Outil ou mode de collecte', finding.get('outil'))
        _field(lines, 'Source', _source(finding))
        _field(lines, 'Nature consignée', finding.get('nature'))
        _field(lines, 'Certitude consignée', finding.get('certitude'))
        _field(lines, 'Texte intégral du constat', finding.get('valeur'))
    if not findings:
        lines.extend(['Aucun constat qualifié consigné. Les éventuelles sorties d’outils figurent dans les démarches.', ''])
    lines.extend(['## Erreurs et blocages', ''])
    problems = False
    for entry in entries:
        details = entry.get('details', {})
        if entry.get('event_type') not in ('command_prepared', 'command_executed'):
            continue
        code = details.get('exit_code', details.get('returncode'))
        local_failure = (details.get('operation') in _LOCAL_OPERATIONS and
                         details.get('result') in ('échec', 'échec apt', 'empreinte incorrecte'))
        if (details.get('error') or details.get('status') in ('refused', 'blocked', 'timeout', 'spawn_error', 'cancelled', 'canceled', 'failed', 'denied')
                or (code is not None and code != 0) or local_failure):
            problems = True
            _field(lines, 'Date', _date(entry.get('timestamp')))
            _field(lines, 'Outil', details.get('tool') or details.get('tool_id'))
            if details.get('operation') in _LOCAL_OPERATIONS:
                _field(lines, 'Opération locale', _LOCAL_OPERATIONS[details['operation']])
            _field(lines, 'Difficulté', _error(details['error']) if details.get('error') else
                   details['result'] if local_failure else
                   _STATES.get(details.get('status'), 'Code de fin signalant un échec ou une interruption'))
            lines.extend(['Voir le résultat consigné dans les démarches ci-dessus.', ''])
        if any(isinstance(result, dict) and result.get('error') for result in details.get('results', [])):
            problems = True
            _field(lines, 'Date', _date(entry.get('timestamp')))
            _field(lines, 'Outil', details.get('tool'))
            lines.extend(['Des réponses de sites sont indéterminées ; chaque site et son message figurent dans les démarches.', ''])
    for error in analysis.get('errors', []):
        problems = True
        _field(lines, 'Blocage de la dernière analyse conservée', _error(error))
    if not problems:
        lines.extend(['Aucun échec explicite relevé dans les champs d’exécution et de préparation. '
                      'Les réserves exprimées dans les textes des outils et les constats restent applicables.', ''])
    lines.extend(['## Conclusions et réserves', '',
                  'Ce rapport restitue les éléments consignés ; il ne vérifie pas indépendamment les sources '
                  'et ne relève jamais automatiquement leur niveau de certitude.', '',
                  'Une source unique reste à recouper. Une correspondance signalée par un outil '
                  'n’établit pas l’identité d’une personne. Une absence de résultat ne prouve pas une absence de fait.', ''])
    if not any(entry.get('event_type') == 'command_executed' for entry in entries):
        lines.extend(['Aucune exécution d’outil consignée dans ce journal.', ''])
    return '\n'.join(lines)


def export_report(manager):
    report = render_report(manager)
    target = manager.case_dir() / 'report.md'
    installation.no_links(target)
    installation.atomic_write(target, report.encode('utf-8'), 0o600)
    return target
