# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : documentation_locale.py
# Role          : Corpus local, recommandations et journal de revue humaine
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Prototype sans réseau ni exécution. Les sources externes restent des données."""
import copy
import hashlib
import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / 'data/documentation/catalog.json'
KINDS = {'ip', 'domain', 'email', 'url', 'file'}


def digest(value):
    """Empreinte canonique d'une fiche ou proposition (pas une signature)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('texte non vide requis')
    return value


def _strings(value):
    if not isinstance(value, list) or not value:
        raise ValueError('liste non vide requise')
    for item in value:
        _text(item)


def _inventory(value):
    if not isinstance(value, list):
        raise ValueError('inventaire : liste requise')
    indexed = {}
    for item in value:
        if not isinstance(item, dict):
            raise ValueError('observation outil requise')
        ident = _text(item.get('id'))
        if ident in indexed or not any(item.get('installed') is s for s in (True, False, None)):
            raise ValueError('inventaire ambigu')
        if item.get('version') is not None:
            _text(item['version'])
        indexed[ident] = item
    return indexed


def _proposal(value):
    if not isinstance(value, dict):
        raise ValueError('proposition requise')
    snapshot = copy.deepcopy(value)
    identity = snapshot.pop('id', None)
    if (snapshot.get('schema_version') != 1 or snapshot.get('status') != 'proposed'
            or snapshot.get('execution_authorized', False) is not False
            or digest(snapshot) != identity):
        raise ValueError('proposition modifiée ou invalide')
    for key in ('tool', 'indicator_type', 'corpus_revision', 'tool_revision'):
        _text(snapshot.get(key))
    if (snapshot['indicator_type'] not in KINDS or 'local_version' not in snapshot
            or snapshot.get('preparation_status') not in ('documented_basis', 'needs_review')):
        raise ValueError('contrat de proposition incomplet')
    if snapshot['local_version'] is not None:
        _text(snapshot['local_version'])
    if not isinstance(snapshot.get('references'), list) or not snapshot['references']:
        raise ValueError('références de proposition requises')
    for reference in snapshot['references']:
        if not isinstance(reference, dict):
            raise ValueError('référence objet requise')
        _text(reference.get('id'))
    snapshot['id'] = identity
    return snapshot


def _write_exclusive(path, value):
    # Sérialiser avant création; fichier privé sans écrasement d'une revue.
    content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(content)


class Corpus:
    """Recherche textuelle expérimentale; aucun téléchargement ou import exécuté."""

    def __init__(self, path=DEFAULT_CORPUS):
        self.path = Path(path).resolve()
        self.root = self.path.parent
        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.validate(data)
        self.data = data

    @staticmethod
    def validate(data):
        if not isinstance(data, dict):
            raise ValueError('corpus objet requis')
        if data.get('schema_version') != 1:
            raise ValueError('version de contrat inconnue')
        if not isinstance(data.get('sources'), list) or not isinstance(data.get('tools'), list):
            raise ValueError('sources et tools requis')
        ids = set()
        for source in data['sources']:
            if not isinstance(source, dict):
                raise ValueError('fiche source requise')
            for key in ('id', 'title', 'origin', 'local_path', 'sha256', 'consulted_at',
                        'review_due', 'documented_version', 'version_pattern', 'summary'):
                _text(source.get(key))
            if source['id'] in ids:
                raise ValueError('source dupliquée')
            ids.add(source['id'])
            if source.get('authority') not in ('upstream_manual', 'official', 'community', 'unknown'):
                raise ValueError('autorité inconnue')
            if source.get('verification') not in ('not_consulted', 'consulted_local'):
                raise ValueError('vérification inconnue')
            if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
                raise ValueError('empreinte invalide')
            if date.fromisoformat(source['review_due']) < date.fromisoformat(source['consulted_at']):
                raise ValueError('dates incohérentes')
            local_path = Path(source['local_path'])
            if local_path.is_absolute() or '..' in local_path.parts:
                raise ValueError('chemin local relatif au corpus requis')
            re.compile(source['version_pattern'])
        ids = set()
        for tool in data['tools']:
            if not isinstance(tool, dict):
                raise ValueError('fiche outil requise')
            for key in ('id', 'name', 'function', 'objective', 'expected_result', 'interaction'):
                _text(tool.get(key))
            if tool['id'] in ids:
                raise ValueError('outil dupliqué')
            ids.add(tool['id'])
            if tool['interaction'] not in ('local_read', 'passive', 'network_query', 'active'):
                raise ValueError('interaction inconnue')
            for key in ('indicator_types', 'features', 'prerequisites', 'limits', 'safety', 'sources'):
                _strings(tool.get(key))
            if not set(tool['indicator_types']) <= KINDS:
                raise ValueError('indice inconnu')
            variants = tool.get('sources_by_version', {})
            if not isinstance(variants, dict):
                raise ValueError('sources_by_version : objet requis')
            for version, references in variants.items():
                _text(version)
                _strings(references)
            for key in ('restrictions',):
                if key in tool:
                    _strings(tool[key])
            for key in ('interpretation', 'applicability_note'):
                if key in tool:
                    _text(tool[key])
            if 'documented_options' in tool:
                if not isinstance(tool['documented_options'], list):
                    raise ValueError('documented_options : liste requise')
                for option in tool['documented_options']:
                    if not isinstance(option, dict):
                        raise ValueError('option documentaire objet requis')
                    _text(option.get('argument'))
                    _text(option.get('purpose'))
            if 'documented_operations' in tool:
                operations = tool['documented_operations']
                if not isinstance(operations, list):
                    raise ValueError('documented_operations : liste requise')
                ids_operations = set()
                for operation in operations:
                    if not isinstance(operation, dict):
                        raise ValueError('opération documentaire objet requis')
                    ident = _text(operation.get('id'))
                    if ident in ids_operations:
                        raise ValueError('opération documentaire dupliquée')
                    ids_operations.add(ident)
                    _text(operation.get('syntax'))
                    _strings(operation.get('version_banners'))
                    _strings(operation.get('restrictions'))
                    if (operation.get('status') != 'documented_not_prepared'
                            or not isinstance(operation.get('parameters'), dict)):
                        raise ValueError('opération documentaire sans autorisation seulement')
            # Une référence absente est représentable et sera signalée à la lecture.

    def tools(self):
        return copy.deepcopy(self.data['tools'])

    @staticmethod
    def _score_tool(tool, tokens):
        ident = tool.get('id', '').casefold()
        name = tool.get('name', '').casefold()
        indicators = ' '.join(tool.get('indicator_types', ())).casefold()
        heading = (tool.get('function', '') + ' ' + tool.get('objective', '')).casefold()
        blob = json.dumps(tool, ensure_ascii=False).casefold()
        score = 0
        for word in tokens:
            if word in (ident, name):
                score += 100
            elif word in ident or word in name:
                score += 40
            if word in indicators.split():
                score += 25
            if word in heading:
                score += 15
            score += blob.count(word)
        return score

    def search(self, query):
        """Recherche textuelle déterministe pondérée (ET logique insensible à la casse)."""
        if not isinstance(query, str):
            raise ValueError('requête textuelle requise')
        tokens = query.casefold().split()
        if not tokens:
            return []
        matches = [
            (self._score_tool(t, tokens), idx, copy.deepcopy(t))
            for idx, t in enumerate(self.data['tools'])
            if all(word in json.dumps(t, ensure_ascii=False).casefold() for word in tokens)
        ]
        matches.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in matches]

    def search_ranked(self, query):
        """Recherche documentaire pondérée sur les outils et les sources locales intègres."""
        if not isinstance(query, str):
            raise ValueError('requête textuelle requise')
        tokens = query.casefold().split()
        if not tokens:
            return []
        results = []
        for tool in self.data['tools']:
            blob = json.dumps(tool, ensure_ascii=False).casefold()
            matched = [w for w in tokens if w in blob]
            if len(matched) == len(tokens):
                results.append(dict(
                    kind='tool',
                    id=tool['id'],
                    score=self._score_tool(tool, tokens),
                    matched_tokens=matched,
                    item=copy.deepcopy(tool),
                ))
        for source in self.data['sources']:
            ref = self.reference(source['id'])
            body = ''
            if ref.get('availability') == 'local':
                try:
                    body = self.read_source(source['id'])['text'].casefold()
                except ValueError:
                    body = ''
            meta = (source.get('id', '') + ' ' + source.get('title', '') + ' ' + source.get('summary', '')).casefold()
            combined = meta + '\n' + body
            matched = [w for w in tokens if w in combined]
            if len(matched) == len(tokens):
                score = sum((30 if w in meta else 0) + combined.count(w) for w in tokens)
                results.append(dict(
                    kind='source',
                    id=source['id'],
                    score=score,
                    matched_tokens=matched,
                    item=ref,
                ))
        return sorted(results, key=lambda r: (-r['score'], 0 if r['kind'] == 'tool' else 1, r['id']))

    def reference(self, source_id, version=None, today=None):
        if version is not None:
            _text(version)
        source = next((s for s in self.data['sources'] if s['id'] == source_id), None)
        if source is None:
            return {'id': source_id, 'availability': 'missing', 'verification': 'not_consulted',
                    'compatibility': 'unknown', 'freshness': 'unknown',
                    'authority': 'unknown', 'content_trust': 'untrusted_data'}
        result = copy.deepcopy(source)
        try:
            content = self._source_bytes(source)
        except FileNotFoundError:
            result['availability'] = 'missing'
        except OSError:
            result['availability'] = 'unavailable'
        else:
            result['availability'] = ('local' if hashlib.sha256(content).hexdigest() == source['sha256']
                                      else 'integrity_error')
        zone = self.data.get('date_timezone')
        if zone is not None:
            try:
                reference_zone = ZoneInfo(zone)
            except (ZoneInfoNotFoundError, ValueError, TypeError):
                raise ValueError('Fuseau des dates documentaires absent ou invalide.') from None
        current_date = today or (datetime.now(reference_zone).date() if zone is not None else date.today())
        result['date_timezone'] = zone or 'system_local'
        result['freshness'] = ('stale' if current_date > date.fromisoformat(source['review_due']) else
                               'unknown' if source['verification'] != 'consulted_local'
                               or current_date < date.fromisoformat(source['consulted_at']) else 'current')
        result['compatibility'] = ('unknown' if not version else
                                   'documented' if re.fullmatch(source['version_pattern'], version)
                                   else 'unverified_version')
        # Les textes de la source ne deviennent jamais règles ou instructions.
        result['content_trust'] = 'untrusted_data'
        return result

    def _source_bytes(self, source):
        path = (self.root / source['local_path']).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('source hors du corpus')
        return path.read_bytes()

    def read_source(self, source_id):
        source = next((s for s in self.data['sources'] if s['id'] == source_id), None)
        if source is None:
            raise ValueError('source absente ou intégrité incorrecte')
        try:
            content = self._source_bytes(source)
        except OSError as exc:
            raise ValueError('source absente ou inaccessible') from exc
        if hashlib.sha256(content).hexdigest() != source['sha256']:
            raise ValueError('intégrité incorrecte')
        # L'empreinte porte exactement sur les octets retournés, sans seconde lecture.
        return {'trust': 'untrusted_data', 'text': content.decode('utf-8')}

    def revision(self):
        return digest(self.data)


def _context(tool, kind):
    """Explications documentaires; aucune extraction ni sélection de cible."""
    if tool['id'] != 'dig':
        return tool['objective'], tool['function'], tool['expected_result'], None
    if kind == 'ip':
        return ('Examiner les enregistrements DNS inverses PTR d’une adresse IP.',
                'dig documente la recherche inverse IPv4/IPv6 avec -x; un nom retourné ne prouve pas l’attribution.',
                'Réponse PTR, absence ou erreur du résolveur; aucun nom n’est présumé.', None)
    if kind == 'domain':
        return ('Examiner les enregistrements DNS d’un domaine explicitement sélectionné.',
                'dig permet de choisir une question DNS et son type; A, AAAA, MX ou TXT répondent à des objectifs différents.',
                'Réponse au type choisi, absence ou erreur; ni propriété ni existence de service ne sont établies.', None)
    if kind == 'email':
        return ('Examiner le domaine d’un e-mail après sélection humaine explicite.',
                'Une recherche DNS concerne le domaine sélectionné, jamais la partie locale ni l’existence de la boîte.',
                'Après transformation validée : réponse DNS du domaine, absence ou erreur; aucune vérification de boîte.',
                dict(required=True, action='extract_domain', selection='human', automatic=False, output_types=['domain']))
    return ('Examiner l’hôte d’une URL après sélection humaine explicite.',
            'Seul l’hôte sélectionné peut devenir un nouvel indice domaine ou IP; le chemin, les paramètres et la page ne sont pas analysés.',
            'Après transformation validée : réponse DNS directe ou inverse selon le nouvel indice; aucune requête HTTP.',
            dict(required=True, action='extract_host', selection='human', automatic=False, output_types=['domain', 'ip']))


def recommend(indicator, inventory, corpus=None, today=None):
    """Accepte les dicts d'Agent 2. N'utilise ni n'enregistre la valeur de l'indice.

    Produit des propositions, jamais des résultats ni des commandes exécutables.
    L'inventaire reçu est une observation du producteur, pas revérifiée ici.
    """
    corpus = corpus or Corpus()
    if not isinstance(indicator, dict):
        raise ValueError('indice objet requis')
    if (not isinstance(indicator.get('type'), str) or indicator['type'] not in KINDS
            or indicator.get('validation') != 'valid'):
        return []
    caveats = indicator.get('ambiguities', [])
    if not isinstance(caveats, list) or any(not isinstance(s, str) for s in caveats):
        raise ValueError('ambiguities : liste de textes requise')
    indexed = _inventory(inventory)
    proposals = []
    for tool in corpus.tools():
        if indicator['type'] not in tool['indicator_types']:
            continue
        item = indexed.get(tool['id'], {})
        installed = item.get('installed')
        version = item.get('version')
        # Un manuel d'une autre version n'est pas une condition cumulative et ne
        # remplace jamais une source exacte manquante ou périmée.
        variants = tool.get('sources_by_version', {})
        source_ids = variants.get(version, tool['sources'])
        refs = [corpus.reference(s, version, today) for s in source_ids]
        objective, justification, expected, transformation = _context(tool, indicator['type'])
        uncertainties = list(caveats)
        conditional = tool.get('applicability_note')
        if conditional:
            uncertainties.append(conditional)
        transform = indicator['type'] in ('email', 'url') and tool['id'] == 'dig'
        if transform:
            uncertainties.append('Extraire et valider explicitement un nouvel indice domaine/hôte avant préparation DNS.')
        if installed is not True:
            uncertainties.append('Outil absent.' if installed is False else 'Disponibilité locale inconnue.')
        if not version:
            uncertainties.append('Version locale inconnue. Contrôler le bandeau local avant toute préparation; aucune syntaxe n’est certifiée.')
        for ref in refs:
            if ref['availability'] != 'local':
                uncertainties.append('Source absente ou intégrité non vérifiée : ' + ref['id'] + '; restaurer une copie attribuée et revue, sans récupération réseau implicite.')
            if ref['verification'] != 'consulted_local':
                uncertainties.append('Documentation non consultée : ' + ref['id'])
            if ref['freshness'] != 'current':
                uncertainties.append('Documentation à réexaminer : ' + ref['id'] + '; comparer date et version avant de préparer une opération.')
            if ref['compatibility'] != 'documented':
                uncertainties.append('Compatibilité de version non établie : ' + ref['id'])
            if ref.get('authority') in ('community', 'unknown'):
                uncertainties.append('Source non officielle : ' + ref['id'])
            if ref.get('preparation_note'):
                uncertainties.append(ref['preparation_note'])
        ready = installed is True and not transform and not conditional and bool(refs) and all(
            r['availability'] == 'local' and r['verification'] == 'consulted_local'
            and r['compatibility'] == 'documented' and r['freshness'] == 'current'
            and r.get('authority') in ('official', 'upstream_manual') for r in refs)
        proposal = dict(schema_version=1, status='proposed', tool=tool['id'],
                        objective=objective, justification=justification,
                        indicator_type=indicator['type'], availability=('present' if installed is True else
                        'absent' if installed is False else 'unknown'), local_version=version,
                        inventory_origin=item.get('detection_origin', 'unknown'),
                        references=refs, prerequisites=tool['prerequisites'], limits=tool['limits'],
                        safety=tool['safety'], interaction=tool['interaction'],
                        network_required=tool['interaction'] in ('network_query', 'active'),
                        expected_result=expected, uncertainties=uncertainties,
                        preparation_status='documented_basis' if ready else 'needs_review',
                        command_parameters={'indicator_type': indicator['type'], 'tool': tool['id'],
                                            'version': version},
                        corpus_revision=corpus.revision(), tool_revision=digest(tool))
        proposal.update(recommendation_kind='documentary', command_status='not_prepared',
                        execution_authorized=False,
                        indicator_status='valid_with_caveats' if caveats else 'valid',
                        requires_indicator_transform=transform, target_transformation=transformation,
                        source_selection='exact_version' if version in variants else 'default',
                        features=tool['features'], restrictions=tool.get('restrictions', []),
                        interpretation=tool.get('interpretation', tool['expected_result']),
                        documented_options=tool.get('documented_options', []),
                        documented_operations=tool.get('documented_operations', []),
                        applicability='conditional' if conditional else 'indicator_type')
        proposal['id'] = digest(proposal)
        proposals.append(proposal)
    # Tri stable : les outils présents passent avant les absents, sans masquer
    # leurs versions inconnues, réserves ou alternatives documentées.
    order = {'present': 0, 'unknown': 1, 'absent': 2}
    return sorted(proposals, key=lambda p: (order[p['availability']],
                  0 if p['preparation_status'] == 'documented_basis' else 1))


class Reviews:
    """Un fichier immuable par événement; usage local, identité humaine déclarative.

    Le code appelant doit recueillir l'action humaine explicite. Ce composant ne
    peut authentifier un humain ni empêcher le propriétaire du disque de l'éditer.
    """

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def record(self, proposal, decision, actor, reason, *, human_confirmed=False, supersedes=None):
        if human_confirmed is not True or decision not in ('approved', 'rejected'):
            raise ValueError('action humaine explicite et décision requises')
        _text(actor)
        _text(reason)
        snapshot = _proposal(proposal)
        # Vérifier l'historique même pour une revue sans remplacement explicite.
        history = self.history()
        if supersedes is not None:
            previous = next((e for e in history if e['event_id'] == supersedes), None)
            if previous is None:
                raise ValueError('événement précédent inconnu')
            if any(e['supersedes'] == supersedes for e in history):
                raise ValueError('événement déjà remplacé; désigner sa nouvelle revue')
            if any(previous['proposal'][k] != snapshot[k] for k in ('tool', 'indicator_type')):
                raise ValueError('remplacement entre méthodes différentes refusé')
        event_id = uuid.uuid4().hex
        event = dict(event_id=event_id, timestamp=datetime.now(timezone.utc).isoformat(),
                     decision=decision, actor=actor, reason=reason, proposal=snapshot,
                     supersedes=supersedes, human_confirmation=True,
                     scope='documentation', execution_authorized=False)
        event['sha256'] = digest(event)
        _write_exclusive(self.directory / (event_id + '.json'), event)
        return copy.deepcopy(event)

    def history(self):
        events = []
        for path in sorted(self.directory.glob('*.json')):
            event = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(event, dict):
                raise ValueError('événement objet requis')
            checksum = event.pop('sha256', None)
            if digest(event) != checksum or event.get('event_id') != path.stem:
                raise ValueError('journal altéré')
            if (event.get('decision') not in ('approved', 'rejected')
                    or event.get('human_confirmation') is not True
                    or event.get('scope', 'documentation') != 'documentation'
                    or event.get('execution_authorized', False) is not False):
                raise ValueError('revue documentaire invalide')
            _text(event.get('actor'))
            _text(event.get('reason'))
            timestamp = datetime.fromisoformat(_text(event.get('timestamp')))
            if timestamp.tzinfo is None:
                raise ValueError('horodatage sans fuseau')
            _proposal(event.get('proposal'))
            if 'supersedes' not in event:
                raise ValueError('lien de remplacement manquant')
            event['sha256'] = checksum
            events.append(event)
        indexed = {e['event_id']: e for e in events}
        replaced = set()
        for event in events:
            previous = event['supersedes']
            if previous is None:
                continue
            if not isinstance(previous, str) or previous not in indexed or previous in replaced:
                raise ValueError('historique de remplacement incohérent')
            replaced.add(previous)
            if any(indexed[previous]['proposal'][k] != event['proposal'][k]
                   for k in ('tool', 'indicator_type')):
                raise ValueError('remplacement entre méthodes différentes')
            visited = {event['event_id']}
            while previous is not None:
                if not isinstance(previous, str) or previous in visited or previous not in indexed:
                    raise ValueError('cycle ou lien absent dans les revues')
                visited.add(previous)
                previous = indexed[previous]['supersedes']
        return sorted(events, key=lambda e: (e['timestamp'], e['event_id']))

    def approved(self, corpus, inventory=None, today=None):
        """Historique des approbations, avec remplacements explicites et péremption."""
        events = self.history()
        indexed_inventory = _inventory(inventory) if inventory is not None else None
        replaced = {e['supersedes'] for e in events if e['supersedes']}
        tools = {t['id']: t for t in corpus.tools()}
        results = []
        for event in events:
            if event['decision'] != 'approved':
                continue
            proposal = event['proposal']
            reasons = []
            tool = tools.get(proposal['tool'])
            if tool is None or digest(tool) != proposal['tool_revision']:
                reasons.append('Fiche outil modifiée ou absente.')
            if corpus.revision() != proposal['corpus_revision']:
                reasons.append('Révision du corpus modifiée; revue requise.')
            for old in proposal['references']:
                current = corpus.reference(old['id'], proposal['local_version'], today)
                if (current['availability'] != 'local' or current['freshness'] != 'current'
                        or current['compatibility'] != 'documented'
                        or current['verification'] != 'consulted_local'
                        or current.get('authority') not in ('official', 'upstream_manual')):
                    reasons.append('Source ou version à réexaminer : ' + old['id'])
            if indexed_inventory is not None:
                local = indexed_inventory.get(proposal['tool'], {})
                if local.get('installed') is not True or local.get('version') != proposal['local_version']:
                    reasons.append('Inventaire local modifié ou outil absent.')
            else:
                reasons.append('Inventaire actuel non fourni; disponibilité non revérifiée.')
            if proposal.get('preparation_status') != 'documented_basis':
                reasons.append('Approbation documentaire avec réserves de préparation conservées.')
            results.append(dict(event=event, superseded=event['event_id'] in replaced,
                                potentially_obsolete=bool(reasons), reasons=reasons,
                                scope='documentation', execution_authorized=False))
        return results


def stage_update(candidate, destination):
    """Valide la structure et conserve un candidat; n'active jamais un corpus.

    La provenance, les droits, les versions et le contenu nécessitent une revue.
    Les chemins des sources seront vérifiés relativement au corpus à son ouverture.
    """
    candidate = copy.deepcopy(candidate)
    Corpus.validate(candidate)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = destination / (digest(candidate) + '.json')
    _write_exclusive(target, {'status': 'pending_human_review', 'candidate': candidate})
    return target
