# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_sessions.py
# Role          : Sessions conversationnelles et contexte professionnel
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""API de session independante de l'interface ; aucune execution d'outil."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from focus_contracts import Message, Model, Role, SessionSnapshot, Settings
from focus_storage import CorruptSession, Storage
from focus_workspace import directory, resource

VERSION = 2
_SECRET = re.compile(r'(?i)(?:api[_ -]?key|token|password|mot de passe|secret)\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{12,}')
_ANY_CASE = object()


def now():
    return datetime.now(timezone.utc).isoformat()


def _validate(data):
    if data.get('version') == 1:
        data = copy.deepcopy(data)
        data['version'] = VERSION
        data.setdefault('revision', 0)
        data.setdefault('history_enabled', True)
        data.setdefault('context', {})
    if data.get('version') != VERSION:
        raise CorruptSession('Version de session non prise en charge')
    if (not isinstance(data.get('name'), str) or not isinstance(data.get('messages'), list)
            or not isinstance(data.get('context'), dict) or type(data.get('revision')) is not int
            or type(data.get('history_enabled')) is not bool):
        raise CorruptSession('Structure de session invalide')
    case_id = data.get('case_id')
    if data.get('case_created') is not None and not isinstance(data['case_created'], str):
        raise CorruptSession('Identite du dossier invalide')
    if case_id is not None:
        from parcours import validate_case_id
        try:
            validate_case_id(case_id)
        except ValueError as exc:
            raise CorruptSession('Dossier de session invalide') from exc
    for m in data['messages']:
        if (not isinstance(m, dict) or m.get('role') not in ('user', 'assistant', 'tool')
                or m.get('state') not in ('running', 'complete', 'cancelled', 'failed')
                or not all(isinstance(m.get(k), str) for k in ('id', 'turn_id', 'text', 'timestamp'))):
            raise CorruptSession('Message invalide')
    return data


class SessionManager:
    def __init__(self, root=None):
        self.storage = Storage(root)

    def create(self, name='Nouvelle session', workspace=None, history_enabled=True, *, case_id=None, case_created=None):
        if not isinstance(name, str) or not name.strip() or _SECRET.search(name):
            raise ValueError('Nom invalide ou sensible')
        if case_id is not None:
            from parcours import validate_case_id
            validate_case_id(case_id)
        if case_created is not None and (not isinstance(case_created, str) or not case_created or case_id is None):
            raise ValueError('Identite du dossier invalide')
        sid = uuid.uuid4().hex
        data = dict(version=VERSION, id=sid, revision=0, name=str(name), created=now(), updated=now(), case_id=case_id, case_created=case_created,
                    history_enabled=bool(history_enabled), messages=[], context_events=[], context={
                        'workspace': str(directory(workspace)) if workspace is not None else None,
                        'mode': None, 'scenario': None, 'model': None, 'provider': None,
                        'indicators': [], 'targets': [], 'parameters': {}, 'resources': [], 'reusable': {}})
        session = Session(self.storage, data, None)
        session.save()
        return session

    def open(self, sid, *, recover_interrupted=False, expected_case=_ANY_CASE, expected_case_created=_ANY_CASE):
        data = _validate(self.storage.read(sid))
        if expected_case is not _ANY_CASE and data.get('case_id') != expected_case:
            raise ValueError('Session associee a un autre dossier')
        if expected_case_created is not _ANY_CASE and data.get('case_created') != expected_case_created:
            raise ValueError('Session associee a une autre incarnation du dossier')
        # A running answer was not completed before the previous process stopped.
        changed = False
        for msg in data['messages']:
            if recover_interrupted and msg['state'] == 'running':
                msg['state'] = 'cancelled'
                changed = True
        session = Session(self.storage, data, data['revision'])
        if changed:
            session.save()
        return session

    resume = open

    def list_sessions(self):
        if not self.storage.sessions.exists():
            return []
        result = []
        for path in sorted(self.storage.sessions.glob('*.json')):
            try:
                data = _validate(self.storage.read(path.stem))
                result.append({'id': data['id'], 'name': data['name'], 'updated': data.get('updated'), 'corrupt': False})
            except (CorruptSession, ValueError, OSError):
                result.append({'id': path.stem, 'corrupt': True})
        return result

    def delete(self, sid, *, confirmation):
        if confirmation != sid:
            raise ValueError('La confirmation doit etre identique a l’identifiant')
        with self.storage.lock(sid):
            self.storage.path(sid).unlink()


class Session:
    def __init__(self, storage, data, revision):
        self._storage, self._data, self._revision = storage, data, revision
        self._closed = False
        # Les instructions temporaires et autorisations ne sont jamais persistees.
        self.temporary_instructions = []
        self.authorizations = []

    @property
    def data(self):
        return copy.deepcopy(self._data)

    def _check(self):
        if self._closed:
            raise RuntimeError('Session fermee')

    def save(self):
        self._check()
        data = copy.deepcopy(self._data)
        data['revision'] = 0 if self._revision is None else self._revision + 1
        data['updated'] = now()
        persisted = copy.deepcopy(data)
        if not data['history_enabled']:
            persisted['messages'] = []
        self._storage.write(data['id'], persisted, self._revision)
        self._data, self._revision = data, data['revision']

    def _change(self, operation):
        self._check()
        old = copy.deepcopy(self._data)
        try:
            operation(self._data)
            self.save()
        except Exception:
            self._data = old
            raise

    def rename(self, name):
        if not isinstance(name, str) or not name.strip() or _SECRET.search(name):
            raise ValueError('Nom invalide ou sensible')
        self._change(lambda d: d.update(name=name))

    def add_message(self, role, text, turn_id, state='complete', *, metadata=None, sensitive=False, allow_tool=False):
        if role not in ('user', 'assistant', 'tool') or state not in ('running', 'complete', 'cancelled', 'failed'):
            raise ValueError('Role ou etat invalide')
        if role == 'tool' and not allow_tool:
            raise ValueError('Conservation du resultat non autorisee')
        if not isinstance(text, str) or not isinstance(turn_id, str) or not turn_id:
            raise ValueError('Message invalide')
        if sensitive or _SECRET.search(text) or _SECRET.search(json.dumps(metadata or {}, ensure_ascii=False)):
            raise ValueError('Contenu sensible refuse : ne pas persister de secrets')
        msg = dict(id=uuid.uuid4().hex, turn_id=turn_id, role=role, text=text, timestamp=now(), state=state, metadata=copy.deepcopy(metadata or {}))
        self._change(lambda d: d['messages'].append(msg))
        return msg['id']

    def update_message(self, message_id, text, state):
        if state not in ('running', 'complete', 'cancelled', 'failed') or not isinstance(text, str) or _SECRET.search(text):
            raise ValueError('Contenu ou etat invalide')
        def change(d):
            msg = next(m for m in d['messages'] if m['id'] == message_id)
            if msg['state'] != 'running':
                raise ValueError('Message deja termine')
            msg.update(text=text, state=state)
        self._change(change)

    def set_context(self, **values):
        allowed = {'mode', 'scenario', 'model', 'provider', 'indicators', 'targets', 'parameters', 'reusable'}
        if set(values) - allowed or _SECRET.search(json.dumps(values, ensure_ascii=False)):
            raise ValueError('Contexte invalide ou sensible')
        reset = any(k in values and values[k] != self._data['context'].get(k) for k in ('mode', 'scenario'))
        def change(d):
            c = d['context']
            if reset:
                c.update(indicators=[], targets=[], parameters={}, reusable={})
                if 'mode' in values and values['mode'] != c.get('mode') and 'scenario' not in values:
                    c['scenario'] = None
            if reset:
                d.setdefault('context_events', []).append({'timestamp': now(), 'mode': values.get('mode', c.get('mode')), 'scenario': values.get('scenario', c.get('scenario'))})
            c.update(copy.deepcopy(values))
        self._change(change)
        if reset:
            self.temporary_instructions.clear()
            self.authorizations.clear()

    def set_workspace(self, path):
        p = str(directory(path))
        def change(d):
            d['context']['workspace'] = p
            d['context']['resources'] = []
        self._change(change)

    def add_resource(self, path):
        root = self._data['context'].get('workspace')
        if not root:
            raise ValueError('Aucun repertoire actif')
        p = str(resource(root, path))
        self._change(lambda d: d['context']['resources'].append(p))
        return p

    def validate_workspace(self):
        c = self._data['context']
        root = directory(c['workspace'])
        return [str(resource(root, p)) for p in c.get('resources', [])]

    def set_history(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Booleen attendu')
        def change(d):
            if enabled and not d['history_enabled']:
                d['messages'] = []
            d['history_enabled'] = enabled
        self._change(change)

    def snapshot(self):
        c = self._data['context']
        model = Model(c['provider'], c['model'], False) if c.get('provider') and c.get('model') else None
        messages = tuple(Message(m['id'], Role(m['role']), m['text']) for m in self._data['messages'] if m['role'] in ('user', 'assistant'))
        return SessionSnapshot(self._data['id'], messages, Settings(model=model, profile_id=c.get('mode')), c.get('scenario'))

    def export(self, path):
        self._check()
        # Creation exclusive pour ne jamais ecraser un fichier utilisateur.
        fd = os.open(Path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    def close(self):
        self._check()
        self.save()
        self.temporary_instructions.clear()
        self.authorizations.clear()
        self._closed = True
