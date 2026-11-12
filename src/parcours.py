# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : parcours.py
# Role          : Assemblage des indices, sources et commandes sans execution
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Orchestration déterministe; la réponse IA ne pilote jamais ce parcours."""
import copy
import fcntl
from functools import wraps
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import commandes
import documentation_locale as documentation
import indices_outils as indices
import installation
from conversation import (prepare_command, safe_display, detect_prompt_injection,
                          isolate_untrusted_content, audit_file_prompt_injection)

GOALS = (
    ('metadata', ('métadonn', 'metadata', 'exif'), {'exiftool': 8, 'file': 2}),
    ('capture', ('capture', 'pcap', 'paquet', 'trafic'), {'tshark': 8, 'file': 2}),
    ('identify', ('nature du fichier', 'type de fichier', 'identifier le fichier', 'format du fichier'), {'file': 8, 'exiftool': 2}),
    ('registration', ('enregistrement', 'whois', 'registrar', 'propriétaire'), {'whois': 8, 'dig': 2}),
    ('dns', ('dns', 'résolution', 'enregistrement dns', 'adresse ip'), {'dig': 8, 'whois': 2}),
    ('url', ('url', 'http', 'site web', 'page'), {'curl': 8, 'dig': 2}),
)
GOAL_LABELS = {'metadata': 'métadonnées', 'capture': 'capture réseau',
               'identify': 'nature du fichier', 'registration': 'enregistrement',
               'dns': 'informations DNS', 'url': 'ressource HTTP(S)'}

def infer_goal(text, indicator):
    value = text.casefold()
    for goal, phrases, weights in GOALS:
        if any(phrase in value for phrase in phrases):
            return goal, weights
    if indicator['type'] == 'file':
        return 'identify', {'file': 6, 'exiftool': 4, 'tshark': 1, 'strings': 1}
    if indicator['type'] == 'url':
        return 'url', {'curl': 6, 'dig': 2}
    if indicator['type'] == 'email':
        return 'dns', {'dig': 6}
    return 'dns', {'dig': 8, 'whois': 2}



CASE_ID_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')
RESERVED_CASE_ACTIONS = {'list', 'liste', 'status', 'statut', 'log', 'journal', 'close', 'fermer'}


def validate_case_id(case_id):
    if (not isinstance(case_id, str) or not CASE_ID_PATTERN.fullmatch(case_id)
            or case_id in ('.', '..') or case_id.lower() in RESERVED_CASE_ACTIONS):
        raise ValueError('Identifiant de dossier invalide (1 à 64 caractères alphanumériques, ., _, -).')
    return case_id


def _guard_case_write(function):
    """Sérialise les écritures coopératives et refuse un état de session périmé."""
    @wraps(function)
    def guarded(self, *args, **kwargs):
        opening = function.__name__ == 'open_case'
        cid = (args[0] if args else kwargs.get('case_id')) if opening else self.active_case_id
        if cid is None and not opening:
            return function(self, *args, **kwargs)
        directory = self.case_dir(cid, create=opening and not kwargs.get('existing_only', False))
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            if not opening and self.state is not None:
                current_path = directory / 'case.json'
                installation.no_links(current_path)
                current = self._verify_case(json.loads(current_path.read_text(encoding='utf-8')), cid)
                if current.get('sha256') != self.state.get('sha256'):
                    raise ValueError('Dossier modifié par une autre session ; le rouvrir avant toute écriture.')
            return function(self, *args, **kwargs)
        finally:
            os.close(descriptor)
    return guarded


class CaseManager:
    """Gestionnaire de dossiers d'enquête isolés avec journalisation horodatée chaînée."""

    def __init__(self, base_dir=None):
        self._base_dir = Path(base_dir) if base_dir is not None else None
        self.active_case_id = None
        self.state = None

    def _cases_root(self, create=False):
        root = self._base_dir if self._base_dir is not None else installation.user_data_path()
        installation.no_links(root)
        cases = root / 'cases'
        installation.no_links(cases)
        if create:
            installation.private_directory(root)
            installation.private_directory(cases)
        return cases

    def case_dir(self, case_id=None, create=False):
        cid = validate_case_id(case_id or self.active_case_id)
        directory = self._cases_root(create=create) / cid
        installation.no_links(directory)
        if create:
            installation.private_directory(directory)
        return directory

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _sign_case(payload):
        body = copy.deepcopy(payload)
        body.pop('sha256', None)
        body['sha256'] = documentation.digest(body)
        return body

    @classmethod
    def _verify_case(cls, payload, expected_id):
        if not isinstance(payload, dict) or payload.get('schema_version') != 1:
            raise ValueError('Schéma de dossier d’enquête invalide.')
        if payload.get('case_id') != expected_id:
            raise ValueError('Identifiant de dossier incohérent.')
        snapshot = copy.deepcopy(payload)
        recorded_hash = snapshot.pop('sha256', None)
        if not recorded_hash or documentation.digest(snapshot) != recorded_hash:
            raise ValueError('Intégrité du dossier d’enquête compromise : ' + str(expected_id))
        for key in ('indicators', 'prepared_commands', 'contexts'):
            if not isinstance(payload.get(key), list):
                raise ValueError('Structure de dossier d’enquête corrompue : ' + key)
        return payload

    def _verify_and_load_journal(self, directory, expected_id):
        journal_path = directory / 'journal.jsonl'
        installation.no_links(journal_path)
        if not journal_path.exists():
            raise ValueError('Journal d’enquête absent pour le dossier : ' + str(expected_id))
        entries = []
        prev_hash = '0' * 64
        for idx, line in enumerate(journal_path.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError('Entrée de journal invalide.')
            recorded_hash = entry.pop('sha256', None)
            if (entry.get('seq') != idx or entry.get('case_id') != expected_id
                    or entry.get('prev_sha256') != prev_hash
                    or documentation.digest(entry) != recorded_hash):
                raise ValueError('Chaîne d’intégrité du journal d’enquête rompue.')
            timestamp = datetime.fromisoformat(entry.get('timestamp', ''))
            if timestamp.tzinfo is None:
                raise ValueError('Horodatage sans fuseau dans le journal d’enquête.')
            entry['sha256'] = recorded_hash
            prev_hash = recorded_hash
            entries.append(entry)
        if not entries:
            raise ValueError('Journal d’enquête vide.')
        return entries

    def _append_journal(self, directory, case_id, event_type, summary, details):
        journal_path = directory / 'journal.jsonl'
        installation.no_links(journal_path)
        entries = self._verify_and_load_journal(directory, case_id) if journal_path.exists() else []
        prev_hash = entries[-1]['sha256'] if entries else '0' * 64
        entry = dict(
            seq=len(entries) + 1,
            timestamp=self._now(),
            case_id=case_id,
            event_type=event_type,
            summary=summary,
            details=copy.deepcopy(details),
            prev_sha256=prev_hash,
        )
        entry['sha256'] = documentation.digest(entry)
        entries.append(entry)
        serialized = ''.join(json.dumps(item, ensure_ascii=False, sort_keys=True) + '\n' for item in entries)
        installation.atomic_write(journal_path, serialized.encode('utf-8'), 0o600)
        return entry

    def _save_case(self, directory, state):
        state['updated_at'] = self._now()
        signed = self._sign_case(state)
        case_path = directory / 'case.json'
        installation.no_links(case_path)
        installation.atomic_write(
            case_path,
            (json.dumps(signed, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8'),
            0o600,
        )
        self.state = signed
        return copy.deepcopy(signed)

    @_guard_case_write
    def open_case(self, case_id, title=None, *, investigation_framework=None, create_only=False, existing_only=False):
        if investigation_framework is not None and (not isinstance(investigation_framework, str) or len(investigation_framework) > 4000):
            raise ValueError('Cadre de l’enquête invalide')
        cid = validate_case_id(case_id)
        if title is not None and (not isinstance(title, str) or len(title) > 200):
            raise ValueError('Titre de dossier invalide.')
        directory = self.case_dir(cid, create=True)
        case_path = directory / 'case.json'
        installation.no_links(case_path)
        if create_only and case_path.exists():
            raise ValueError('Ce dossier existe déjà ; utilisez /investigation open.')
        if existing_only and not case_path.exists():
            raise ValueError('Dossier introuvable ; utilisez /investigation create.')
        if case_path.exists():
            raw = json.loads(case_path.read_text(encoding='utf-8'))
            state = self._verify_case(raw, cid)
            self.status(cid)
            state.pop('closed_at', None)
            state.pop('archived_at', None)
            state.pop('sealed_journal_sha256', None)
            if title:
                state['title'] = title.strip()
            self._append_journal(directory, cid, 'case_reopened', 'Réouverture du dossier d’enquête.',
                                 {'title': state.get('title', '')})
            saved = self._save_case(directory, state)
        else:
            now = self._now()
            state = dict(
                schema_version=1,
                case_id=cid,
                title=(title or '').strip(),
                created_at=now,
                updated_at=now,
                indicators=[],
                prepared_commands=[],
                contexts=[],
                latest_analysis=None,
                investigation_framework='',
            )
            self._append_journal(directory, cid, 'case_created', 'Création du dossier d’enquête isolé.',
                                 {'title': state['title'], 'framework': '', 'provided': False})
            saved = self._save_case(directory, state)
        self.active_case_id = cid
        if investigation_framework is not None:
            return CaseManager.record_framework.__wrapped__(self, investigation_framework or '')
        return saved

    @_guard_case_write
    def record_framework(self, framework):
        if not isinstance(framework, str) or len(framework) > 4000:
            raise ValueError('Cadre de l’enquête invalide')
        if not self.active_case_id:
            raise ValueError('Aucun dossier actif')
        directory = self.case_dir()
        self.state['investigation_framework'] = framework.strip()
        self._append_journal(directory, self.active_case_id, 'investigation_framework',
                             'Cadre de l’enquête consigné (facultatif).',
                             {'framework': framework.strip(), 'provided': bool(framework.strip())})
        return self._save_case(directory, self.state)

    @_guard_case_write
    def record_finding(self, finding):
        from osint_guardrails import Finding
        if not isinstance(finding, Finding):
            raise ValueError('Finding requis')
        if not self.active_case_id:
            raise ValueError('Aucun dossier actif')
        directory = self.case_dir()
        row = finding.to_dict()
        row['sha256'] = documentation.digest(row)
        self.state.setdefault('findings', []).append(row)
        self._append_journal(directory, self.active_case_id, 'finding_recorded',
                             'Constat qualifié consigné.', row)
        return self._save_case(directory, self.state)

    @_guard_case_write
    def close_case(self):
        if not self.active_case_id:
            return None
        cid = self.active_case_id
        directory = self.case_dir(cid, create=False)
        seal = self._append_journal(directory, cid, 'case_closed', 'Fermeture du dossier d’enquête.', {})
        self.state['closed_at'] = seal['timestamp']
        self.state['sealed_journal_sha256'] = seal['sha256']
        self._save_case(directory, self.state)
        self.active_case_id = None
        self.state = None
        return cid

    @_guard_case_write
    def rename_case(self, title):
        if not self.active_case_id:
            raise ValueError('Aucun dossier actif.')
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError('Titre attendu : 1 à 200 caractères.')
        directory = self.case_dir()
        self.status()
        self._append_journal(directory, self.active_case_id, 'case_renamed',
                             'Titre du dossier modifié.', {'old': self.state['title'], 'new': title.strip()})
        self.state['title'] = title.strip()
        return self._save_case(directory, self.state)

    @_guard_case_write
    def archive_case(self):
        if not self.active_case_id:
            raise ValueError('Aucun dossier actif.')
        directory = self.case_dir()
        self.status()
        event = self._append_journal(directory, self.active_case_id, 'case_archived',
                                     'Dossier archivé ; réouverture explicite possible.', {})
        self.state['archived_at'] = event['timestamp']
        self._save_case(directory, self.state)
        # close_case seals the journal with the existing, verified closing format.
        return CaseManager.close_case.__wrapped__(self)

    @_guard_case_write
    def delete_case(self):
        """Delete only the verified active case; UI must obtain explicit approval."""
        import shutil
        if not self.active_case_id:
            raise ValueError('Aucun dossier actif.')
        self.status()
        directory = self.case_dir()
        cid = self.active_case_id
        shutil.rmtree(directory)
        self.active_case_id, self.state = None, None
        return cid

    @_guard_case_write
    def record_analysis(self, analysis_result):
        if not self.active_case_id or self.state is None:
            return None
        directory = self.case_dir(self.active_case_id, create=False)
        now = self._now()
        recorded_indicators = []
        for ind in analysis_result.get('indicators', []):
            entry = dict(
                recorded_at=now,
                type=ind.get('type'),
                original=ind.get('original'),
                normalized=ind.get('normalized'),
                validation=ind.get('validation'),
                ambiguities=list(ind.get('ambiguities', [])),
            )
            entry['sha256'] = documentation.digest(entry)
            self.state['indicators'].append(entry)
            recorded_indicators.append(entry)
        self.state['latest_analysis'] = copy.deepcopy(analysis_result)
        self._append_journal(
            directory,
            self.active_case_id,
            'analysis_recorded',
            f"Analyse enregistrée ({len(recorded_indicators)} indice(s)).",
            {'indicators': [{'type': i['type'], 'normalized': i['normalized'], 'validation': i['validation'],
                             'sha256': i['sha256']} for i in recorded_indicators]},
        )
        return self._save_case(directory, self.state)

    @_guard_case_write
    def record_preparation(self, preparation_result):
        if not self.active_case_id or self.state is None:
            return None
        directory = self.case_dir(self.active_case_id, create=False)
        now = self._now()
        cmd = preparation_result.get('command', preparation_result)
        entry = dict(
            recorded_at=now,
            status=cmd.get('status'),
            tool_id=cmd.get('tool_id'),
            operation=cmd.get('operation'),
            display=cmd.get('display'),
            argv=cmd.get('argv'),
            error=cmd.get('error'),
            executed=False,
            plan_id=cmd.get('id'),
        )
        entry['sha256'] = documentation.digest(entry)
        self.state['prepared_commands'].append(entry)
        if isinstance(self.state.get('latest_analysis'), dict):
            self.state['latest_analysis']['last_preparation'] = copy.deepcopy(preparation_result)
        self._append_journal(
            directory,
            self.active_case_id,
            'command_prepared',
            f"Préparation enregistrée ({entry['status']}).",
            {'status': entry['status'], 'tool_id': entry['tool_id'], 'display': entry['display'],
             'error': entry['error'], 'sha256': entry['sha256']},
        )
        return self._save_case(directory, self.state)

    @_guard_case_write
    def record_context(self, selected_context):
        if not self.active_case_id or self.state is None:
            return None
        directory = self.case_dir(self.active_case_id, create=False)
        now = self._now()
        snapshot = copy.deepcopy(selected_context)
        context_hash = documentation.digest(snapshot)
        entry = dict(
            recorded_at=now,
            context_sha256=context_hash,
            selected_choice=snapshot.get('selected_choice'),
            context=snapshot,
        )
        entry['sha256'] = documentation.digest(entry)
        self.state['contexts'].append(entry)
        self._append_journal(
            directory,
            self.active_case_id,
            'context_selected',
            'Contexte technique associé au dossier.',
            {'context_sha256': context_hash, 'selected_choice': snapshot.get('selected_choice')},
        )
        return self._save_case(directory, self.state)

    @_guard_case_write
    def record_execution(self, execution_result):
        """Consigne la sortie complète d'une exécution approuvée dans le journal chaîné."""
        if not self.active_case_id or self.state is None:
            return None
        snapshot = copy.deepcopy(execution_result)
        directory = self.case_dir(self.active_case_id, create=False)
        self._append_journal(directory, self.active_case_id, 'command_executed',
                             'Résultat de la commande approuvée : ' + str(snapshot.get('tool') or 'outil'),
                             snapshot)
        return self._save_case(directory, self.state)

    @_guard_case_write
    def record_security_audit(self, audit_report):
        if not self.active_case_id or self.state is None:
            return None
        directory = self.case_dir(self.active_case_id, create=False)
        self._append_journal(
            directory,
            self.active_case_id,
            'security_audit',
            f"Audit anti-injection sur {audit_report['path']} (injection={audit_report['injection_detected']}).",
            {
                'path': audit_report['path'],
                'sha256': audit_report['sha256'],
                'sha256_scope': audit_report.get('sha256_scope', 'unspecified'),
                'bytes_inspected': audit_report['bytes_inspected'],
                'truncated': audit_report['truncated'],
                'injection_detected': audit_report['injection_detected'],
                'detected_patterns': audit_report['detected_patterns'],
            },
        )
        return self._save_case(directory, self.state)

    def read_journal(self, case_id=None):
        cid = validate_case_id(case_id or self.active_case_id)
        directory = self.case_dir(cid, create=False)
        return self._verify_and_load_journal(directory, cid)

    def status(self, case_id=None):
        cid = validate_case_id(case_id or self.active_case_id)
        directory = self.case_dir(cid, create=False)
        case_path = directory / 'case.json'
        installation.no_links(case_path)
        if not case_path.exists():
            raise ValueError('Dossier d’enquête introuvable : ' + cid)
        state = self._verify_case(json.loads(case_path.read_text(encoding='utf-8')), cid)
        journal = self._verify_and_load_journal(directory, cid)
        seal = state.get('sealed_journal_sha256')
        if seal and (seal != journal[-1]['sha256'] or journal[-1]['event_type'] != 'case_closed'):
            raise ValueError('Scellement du journal incohérent.')
        return dict(
            closed_at=state.get('closed_at'),
            archived_at=state.get('archived_at'),
            sealed_journal_sha256=seal,
            case_id=cid,
            title=state.get('title', ''),
            path=str(directory),
            created_at=state['created_at'],
            updated_at=state['updated_at'],
            indicators_count=len(state['indicators']),
            prepared_commands_count=len(state['prepared_commands']),
            contexts_count=len(state['contexts']),
            journal_entries_count=len(journal),
            sha256=state['sha256'],
            journal_head_sha256=journal[-1]['sha256'],
            integrity='verified',
            integrity_scope='stored_checksums_only',
            integrity_limitations=(
                'Empreintes locales cohérentes ; aucune signature ni authentification. '
                'Une réécriture complète ou une troncature du journal peut rester indétectable. '
                'Écritures de l’état et du journal distinctes, sans transaction durable.'
            ),
        )

    def list_cases(self):
        cases_root = self._cases_root(create=False)
        if not cases_root.exists():
            return []
        items = []
        for entry in sorted(cases_root.iterdir(), key=lambda p: p.name):
            if not entry.is_symlink() and not entry.is_dir():
                continue
            cid = entry.name
            try:
                items.append(self.status(cid))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                items.append(dict(
                    case_id=cid,
                    title='',
                    path=str(entry),
                    created_at=None,
                    updated_at=None,
                    indicators_count=0,
                    prepared_commands_count=0,
                    contexts_count=0,
                    journal_entries_count=0,
                    sha256=None,
                    journal_head_sha256=None,
                    integrity='integrity_error: ' + str(exc),
                ))
        return items


def methods_reviews(base_dir=None):
    """Accès au registre d'approbation humaine des méthodes (uchambuzi-data/methods)."""
    root = Path(base_dir) if base_dir is not None else installation.user_data_path()
    installation.no_links(root)
    installation.private_directory(root)
    methods_dir = root / 'methods'
    installation.no_links(methods_dir)
    installation.private_directory(methods_dir)
    return documentation.Reviews(methods_dir)


def stage_corpus_file(candidate_path, base_dir=None):
    """Valide et met en quarantaine un candidat d'actualisation documentaire sans l'activer."""
    src = Path(candidate_path).expanduser()
    installation.no_links(src)
    src = src.resolve()
    if not src.is_file():
        raise ValueError('Fichier candidat introuvable : ' + str(src))
    candidate = json.loads(src.read_text(encoding='utf-8'))
    root = Path(base_dir) if base_dir is not None else installation.user_data_path()
    installation.no_links(root)
    installation.private_directory(root)
    staging_dir = root / 'corpus-staging'
    installation.no_links(staging_dir)
    installation.private_directory(staging_dir)
    return documentation.stage_update(candidate, staging_dir)


def analyse(text, *, kind=None, versions=False):
    if kind is not None:
        indicators = [indices.classify(text, kind)]
    elif text.startswith(('/', './', '../', '~/')):
        indicators = [indices.classify(text, 'file')]
    else:
        indicators = indices.extract(text)
    seen = set()
    unique = []
    duplicates = []
    for indicator in indicators:
        value = indicator['normalized'] or indicator['original']
        if not isinstance(indicator['type'], str) or not isinstance(value, str):
            unique.append(indicator)
            continue
        key = (indicator['type'], value)
        if key in seen:
            duplicates.append(copy.deepcopy(indicator))
        else:
            seen.add(key)
            unique.append(indicator)
    indicators = unique
    inventory = indices.inventory(versions=versions)
    result = dict(indicators=indicators, inventory=inventory, recommendations=[], choices=[], errors=[],
                  duplicates=duplicates, summaries=[])
    try:
        corpus = documentation.Corpus()
        for indicator in indicators:
            proposals = documentation.recommend(indicator, inventory, corpus)
            goal, weights = infer_goal(text if kind is None else '', indicator)
            for proposal in proposals:
                score = 2 * weights.get(proposal['tool'], 0)
                if proposal['availability'] == 'present': score += 12
                if proposal['preparation_status'] == 'documented_basis': score += 4
                if proposal['requires_indicator_transform']: score -= 3
                if proposal['applicability'] == 'conditional': score -= 2
                proposal['goal'] = goal
                proposal['rank_score'] = score
                proposal['ranking_reason'] = (f"Adéquation à l'objectif supposé {GOAL_LABELS[goal]} : {weights.get(proposal['tool'], 0)} ; "
                                              f"présence locale : {proposal['availability']} ; "
                                              f"base documentaire : {proposal['preparation_status']}.")
                proposal['id'] = documentation.digest({k: v for k, v in proposal.items() if k != 'id'})
            proposals.sort(key=lambda row: (-row['rank_score'], row['tool']))
            theoretical = max(proposals, key=lambda row: weights.get(row['tool'], 0), default=None)
            usable = next((row for row in proposals if row['availability'] == 'present'
                           and row['local_version'] and not row['requires_indicator_transform']
                           and row['tool'] in commandes.EXACT_VERSIONS
                           and row['preparation_status'] == 'documented_basis'), None)
            result['summaries'].append({'indicator_id': indicator['id'], 'goal': GOAL_LABELS[goal],
                                        'theoretical_tool': theoretical['tool'] if theoretical else None,
                                        'local_tool': usable['tool'] if usable else None})
            result['recommendations'].extend(proposals)
            result['choices'].extend({'indicator': indicator, 'recommendation': r} for r in proposals)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Ne jamais présenter une liste partielle comme une analyse complète.
        result.update(recommendations=[], choices=[], summaries=[])
        result['errors'].append('Documentation indisponible ou invalide : ' + str(exc))
    return result


def refusal(code, message):
    return dict(schema_version=1, status='refused', error={'code': code, 'message': message},
                argv=None, display=None, execution='disabled', executed=False,
                approval={'required': True, 'status': 'not_requested', 'scope': 'manual_execution'},
                technical_result={'status': 'not_run', 'exit_code': None, 'stdout': None, 'stderr': None})


def context_for_choice(analysis, number):
    """Projection explicite d'une proposition; conserve références, limites et refus."""
    import copy
    if type(number) is not int or not 1 <= number <= len(analysis.get('choices', [])):
        raise ValueError('Numéro de proposition invalide pour /context.')
    choice = analysis['choices'][number - 1]
    tool = choice['recommendation']['tool']
    context = dict(selected_choice=number, indicator=choice['indicator'],
                   recommendation=choice['recommendation'],
                   inventory=[row for row in analysis['inventory'] if row['id'] == tool],
                   errors=analysis.get('errors', []))
    if 'last_preparation' in analysis:
        context['last_preparation'] = analysis['last_preparation']
    context['selection_limits'] = ('Proposition explicitement sélectionnée seulement ; '
                                   'les autres propositions et outils restent affichés dans le terminal. '
                                   'Le dernier résultat de préparation, si présent, est conservé intégralement.')
    return copy.deepcopy(context)


def prepare_selected(analysis, number, *, parameters, constraints):
    """Refait observations et sources après la saisie humaine des paramètres.

    L'indice est reclassifié depuis son original. Son éventuel changement bloque
    la préparation; on ne transporte jamais silencieusement un périmètre ancien.
    """
    if type(number) is not int or number < 1 or number > len(analysis.get('choices', [])):
        return refusal('invalid_selection', 'Sélection absente ou invalide; refaire /analyze.')
    selected = analysis['choices'][number - 1]
    old = selected['indicator']
    indicator = indices.classify(old['original'], old['type'])
    if indicator['validation'] != 'valid' or indicator['normalized'] != old['normalized']:
        return refusal('changed_indicator', 'Indice modifié ou invalide; refaire /analyze.')
    tool_id = selected['recommendation']['tool']
    kind = indicator['type']
    if tool_id in commandes.LOCAL_OPERATIONS and kind == 'file':
        operation = commandes.LOCAL_OPERATIONS[tool_id]
    elif tool_id == 'dig' and kind in ('domain', 'ip'):
        operation = 'dns_query' if kind == 'domain' else 'dns_reverse'
    else:
        return refusal('unsupported_indicator', 'Préparation directe non prise en charge. Pour URL/e-mail, choisir explicitement un nouvel indice domain ou ip avec /indicator.')
    # Contrôles de version déclarés et bornés, jamais d'analyse ni de cible passée aux outils.
    inventory = indices.inventory(versions=True)
    try:
        proposals = documentation.recommend(indicator, inventory, documentation.Corpus())
        proposal = next((r for r in proposals if r['tool'] == tool_id), None)
        if proposal is None:
            return refusal('missing_recommendation', 'Recommandation devenue indisponible.')
        command = prepare_command(commandes, proposal, indicator, inventory,
                                  operation=operation, parameters=parameters, constraints=constraints)
        # Conserver la référence fraîche pour l'affichage; le plan et son empreinte restent intacts.
        return {'recommendation': proposal, 'command': command}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return refusal('documentation_unavailable', 'Documentation indisponible ou invalide : ' + str(exc))


def render_recommendation(proposal):
    print(safe_display(f"Outil : {proposal['tool']} — {proposal['objective']}"))
    if proposal['tool'] not in commandes.EXACT_VERSIONS:
        print('Recommandation informative ; préparation non prise en charge par ce prototype.')
    print(safe_display(f"Disponibilité : {proposal['availability']} ; version : {proposal['local_version'] or 'inconnue'} ; base : {proposal['preparation_status']}"))
    if 'ranking_reason' in proposal:
        print(safe_display('Classement : ' + proposal['ranking_reason']))
    print(safe_display('Justification : ' + proposal['justification']))
    for key, label in [('prerequisites', 'Prérequis'), ('limits', 'Limite'), ('safety', 'Précaution'), ('uncertainties', 'Incertitude'), ('restrictions', 'Restriction')]:
        for value in proposal.get(key, []):
            print(safe_display(f'  {label} : {value}'))
    for ref in proposal['references']:
        print(safe_display(f"  Source : {ref.get('title', ref['id'])} | {ref.get('origin', 'origine absente')} | {ref.get('local_path', 'copie absente')} | version {ref.get('documented_version', 'inconnue')} | consultation {ref.get('consulted_at', 'inconnue')} ({ref.get('date_timezone', 'fuseau non déclaré')}) | {ref['availability']}, {ref['compatibility']}, {ref['freshness']}, {ref['verification']}"))
    print(safe_display('Résultat attendu, non observé : ' + proposal['expected_result']))
    if proposal.get('interpretation'):
        print(safe_display('Interprétation prudente : ' + proposal['interpretation']))


def render_analysis(result):
    print('Analyse locale. Aucune commande d’investigation exécutée.')
    if not result['indicators']:
        print('Aucun indice reconnu ; préciser avec /indicator TYPE VALEUR.')
    for indicator in result['indicators']:
        print(safe_display(f"Indice {indicator['type']} : {indicator['normalized'] or indicator['original']} — {indicator['validation']}"))
        print(safe_display(indicator['explanation']))
        for value in indicator['ambiguities']:
            print(safe_display('  Limite : ' + value))
        if indicator['validation'] != 'valid':
            print('Préparation refusée : indice invalide ou non vérifié.')
    if result.get('duplicates'):
        print(safe_display(f"Doublons regroupés : {len(result['duplicates'])}."))
    for summary in result.get('summaries', []):
        print(safe_display(f"Objectif supposé : {summary['goal']} ; option documentaire : "
                           f"{summary['theoretical_tool'] or 'aucune'} ; candidat local documenté : "
                           f"{summary['local_tool'] or 'aucun vérifié'}."))
    for error in result['errors']:
        print(safe_display('Préparation refusée : ' + error))
    for number, choice in enumerate(result['choices'], 1):
        print(f'\nProposition {number} :')
        render_recommendation(choice['recommendation'])
    if result['choices']:
        print('Pour examiner une commande : /prepare NUMERO. Les versions seront contrôlées localement.')


def render_preparation(result):
    if 'command' in result:
        render_recommendation(result['recommendation'])
        result = result['command']
    if result['status'] != 'prepared':
        print(safe_display(f"Préparation refusée [{result['error']['code']}] : {result['error']['message']}"))
        return
    print(safe_display('Commande préparée pour examen : ' + result['display']))
    print(safe_display(f"Opération : {result['operation_type']} ; risque : {result['risk']} ; réseau requis par l’outil : {result['network_required']}"))
    for item in result['parameter_explanations']:
        print(safe_display(f"  {item['argument']} : {item['explanation']}"))
    for label, key in [('Prérequis', 'prerequisites'), ('Limite', 'limitations')]:
        for value in result[key]:
            print(safe_display(f'{label} : {value}'))
    for source in result['sources']:
        print(safe_display(f"Syntaxe : {source['title']} ; {source['path']} ; {source['origin']} ; SHA-256 {source['sha256']}"))
    print('Approbation humaine en attente. Exécution désactivée. Résultat technique : non exécuté.')
