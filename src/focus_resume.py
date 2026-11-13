# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_resume.py
# Role          : Reprise explicite des sessions liees aux dossiers d'enquete
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Interface d'integration sans ouverture de dossier ni execution automatique.

L'hote construit ResumeSessions(SessionManager(root), case_manager), puis appelle
create() ou open(id, recover_interrupted=True) apres ouverture explicite du dossier.
Les conversations resident dans cases/<id>/sessions ; leur identifiant et leur
revision sont consignes dans le journal sans texte ni empreinte. Les anciennes
sessions globales et les conversations sans evenement correspondant ne sont pas
migrees automatiquement.
Le parametre de recuperation n'est utilisable que si aucun moteur ne travaille
encore sur cette session. Chaque modification de Session reste atomique et peut
lever ConflictError. list_sessions() ne liste que le dossier actif verifie.

Les fichiers snapshot et journal ne forment pas une transaction atomique : une
divergence de revision est refusee, sans reparation automatique. Une modification
du contenu a revision identique ou une restauration coherente des deux fichiers
peut rester indetectable : aucune verification cryptographique n'est declaree.

Pour afficher les fragments, utiliser session.data['messages']. Pour alimenter
un moteur conversation.Session neuf et vide, affecter conversation_messages(session)
à son attribut messages. Les tours incomplets ou suspects sont exclus ; l'hote
signale cette exclusion et conserve les fragments dans l'affichage. Il ne restaure
ni instructions temporaires, ni autorisations, ni resultats d'outils. L'hote doit
verifier a nouveau le dossier avant chaque operation et detacher la session lors
d'un changement de dossier. La persistance doit etre precedee du filtrage des
secrets par l'hote ; les detections automatiques ne sont pas exhaustives.
"""
import contextlib
import fcntl
import os

import installation
from conversation import detect_prompt_injection, sanitize_prompt_data
from focus_sessions import Session, SessionManager, _validate
from focus_storage import ConflictError, CorruptSession
from parcours import validate_case_id


class _AnchoredStorage:
    """Verrou dossier puis session ; divergence entre fichiers => refus explicite."""

    def __init__(self, storage, owner):
        self.base, self.owner = storage, owner

    def __getattr__(self, name):
        return getattr(self.base, name)

    @contextlib.contextmanager
    def transaction(self, sid):
        cases = self.owner.cases
        cid = validate_case_id(cases.active_case_id)
        directory = cases.case_dir(cid, create=False)
        if self.base.root != directory:
            raise ValueError('Session associee a un autre dossier')
        lock_path = directory.parent / ('.lock-' + cid)
        installation.no_links(lock_path)
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            case_id, created = self.owner._case()
            if case_id != cid or cases.state is None or cases.state.get('revision', 0) != cases.status(cid)['revision']:
                raise ConflictError('Dossier modifie par une autre session ; le rouvrir')
            installation.no_links(self.base.sessions)
            installation.no_links(self.base.path(sid))
            with self.base.lock(sid):
                yield directory, case_id, created
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _verified(self, sid, directory, cid, created):
        data = _validate(self.base.read(sid))
        if (data.get('case_id'), data.get('case_created')) != (cid, created):
            raise ValueError('Session associee a un autre dossier')
        entries = self.owner.cases._verify_and_load_journal(directory, cid)
        last = next((e['details'] for e in reversed(entries)
                     if e.get('event_type') == 'conversation_snapshot'
                     and e['details'].get('session_id') == sid), None)
        if last is None or last.get('revision') != data['revision']:
            raise CorruptSession('Conversation absente du journal ou révision incohérente')
        return data

    def write(self, sid, data, expected):
        with self.transaction(sid) as (directory, cid, created):
            if (data.get('case_id'), data.get('case_created')) != (cid, created):
                raise ValueError('Session associee a un autre dossier')
            path = self.base.path(sid)
            if path.exists():
                current = self._verified(sid, directory, cid, created)
                if current['revision'] != expected:
                    raise ConflictError('Session modifiee par un autre processus')
            elif expected is not None:
                raise ConflictError('Session absente ou supprimee')
            self.base.write_locked(sid, data, expected)
            self.owner.cases._append_journal(directory, cid, 'conversation_snapshot',
                'Conversation enregistrée.',
                {'session_id': sid, 'revision': data['revision']})
            journal_fd = os.open(directory / 'journal.jsonl', os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(journal_fd)
            finally:
                os.close(journal_fd)
            directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)


class ResumeSessions:
    """Raccordement explicite au CaseManager existant, sans mutation de celui-ci."""

    def __init__(self, sessions, cases):
        # L'argument historique reste accepte ; aucun contenu global n'est migre.
        self.cases = cases

    @property
    def sessions(self):
        return SessionManager(self.cases.case_dir(validate_case_id(self.cases.active_case_id), create=False))

    def _manager(self):
        manager = self.sessions
        manager.storage = _AnchoredStorage(manager.storage, self)
        return manager

    def _case(self):
        case_id = validate_case_id(self.cases.active_case_id)
        status = self.cases.status(case_id)
        if status['structure'] != 'valid' or status['closed_at'] or status['archived_at']:
            raise ValueError('Dossier actif indisponible ou non verifie')
        return case_id, status['created_at']

    def create(self, name='Nouvelle session', workspace=None, history_enabled=True):
        case_id, created = self._case()
        return self._manager().create(name, workspace, history_enabled, case_id=case_id, case_created=created)

    def open(self, sid, *, recover_interrupted=False):
        storage = self._manager().storage
        with storage.transaction(sid) as (directory, case_id, created):
            data = storage._verified(sid, directory, case_id, created)
        session = Session(storage, data, data['revision'])
        if recover_interrupted and any(m['state'] == 'running' for m in data['messages']):
            def cancel_interrupted(current):
                for message in current['messages']:
                    if message['state'] == 'running':
                        message['state'] = 'cancelled'
            session._change(cancel_interrupted)
        return session

    def list_sessions(self):
        case_id, created = self._case()
        result = []
        storage = self.sessions.storage
        installation.no_links(storage.sessions)
        for path in sorted(storage.sessions.glob('*.json')):
            sid = path.stem
            try:
                data = self.open(sid).data
                result.append({'id': sid, 'name': data['name'],
                               'updated': data.get('updated'), 'corrupt': False})
            except (ValueError, OSError):
                try:
                    installation.no_links(path)
                    data = storage.read(sid)
                    if (data.get('case_id'), data.get('case_created')) == (case_id, created):
                        result.append({'id': sid, 'name': 'Conversation non vérifiée',
                                       'updated': None, 'corrupt': True})
                except (ValueError, OSError):
                    pass
        return result

    def check(self, session):
        """A appeler avant chaque usage d'une session conservee par l'hote."""
        case_id, created = self._case()
        if (session.data.get('case_id'), session.data.get('case_created')) != (case_id, created):
            raise ValueError('Session associee a un autre dossier')


def conversation_messages(session):
    """Retourne (messages, nombre de tours exclus), sans modifier le runtime.

    Les paires strictement adjacentes user/assistant, completes et de meme tour
    sont seules reprises. Les donnees d'outil, textes incomplets et tours dont
    le texte contient des motifs d'injection ne sont jamais transmis au modele.
    """
    entries = session.data['messages']
    output = []
    excluded = 0
    index = 0
    while index < len(entries):
        first = entries[index]
        if first['role'] == 'user' and index + 1 < len(entries):
            second = entries[index + 1]
            if second['role'] == 'assistant' and first['turn_id'] == second['turn_id']:
                index += 2
                if (first['state'] == second['state'] == 'complete'
                        and not detect_prompt_injection(first['text'])
                        and not detect_prompt_injection(second['text'])):
                    output.extend({'role': item['role'], 'content': sanitize_prompt_data(item['text'])}
                                  for item in (first, second))
                else:
                    excluded += 1
                continue
        excluded += 1
        index += 1
    return output, excluded
