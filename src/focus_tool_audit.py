# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_tool_audit.py
# Role          : Audit technique prive et raccordement stockage
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Pas de nouvelle infrastructure de sessions ni de sortie brute persistee.

Les cibles/arguments/identites sont correles par empreinte HMAC locale pour ne
pas journaliser de secrets. La presentation integrale reste en memoire humaine.
"""
import datetime
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import uuid
import re

class ToolAudit:
    def __init__(self, root=None, *, session=None, case_manager=None):
        if root is None:
            try:
                from focus_storage import default_data_dir
                root = default_data_dir()
            except ImportError:
                root = Path.home() / 'Documents' / 'uchambuzi-data'
        self.root = Path(root) / 'audit' / 'tools'
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if self.root.is_symlink():
            raise ValueError('Repertoire audit symbolique refuse')
        os.chmod(self.root, 0o700)
        self.session = session
        self.case_manager = case_manager
        keypath = self.root / '.correlation-key'
        try:
            fd = os.open(keypath, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            fd = os.open(keypath, os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as f:
                self.key = f.read(33)
            if len(self.key) != 32:
                raise ValueError('Cle audit invalide')
        else:
            self.key = secrets.token_bytes(32)
            with os.fdopen(fd, 'wb') as f:
                f.write(self.key)
                f.flush()
                os.fsync(f.fileno())
        self.path = self.root / 'events.jsonl'

    def digest(self, value):
        return hmac.new(self.key, str(value).encode(), hashlib.sha256).hexdigest()

    def record(self, operation, event, *, approval=None, result=None):
        if event not in ('prepared','requested','approved','denied','started','finished','invalidated','revoked'):
            raise ValueError('Evenement invalide')
        row = dict(event_id=uuid.uuid4().hex, operation_id=operation.id,
            session_id=self.session.data['id'] if self.session is not None else None,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=event,
            mode=operation.mode, scenario=self.digest(operation.scenario),
            tool=operation.tool_id, version=operation.version,
            command={'program': operation.tool_id, 'arguments_hmac': self.digest(operation.args)},
            target_hmac=self.digest(operation.target), scope_hmac=self.digest(operation.scope),
            risk=operation.risk.value, approval=event if event in ('denied','revoked','invalidated') else 'approved' if approval else 'pending',
            authorization_id=approval.id if approval else None,
            actor_hmac=self.digest(approval.actor) if approval else None,
            status=result.status if result else event,
            returncode=result.returncode if result else None,
            result_refs=[], artifacts=[])
        if result:
            row['effective_start'] = result.started_at
            row['effective_end'] = result.finished_at
            row['pid'] = result.pid
            row['artifacts'] = [dict(kind=kind, sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data), retained=False) for kind, data in
                (('stdout',result.stdout),('stderr',result.stderr))]
            row['result_refs'] = [operation.id+':stdout', operation.id+':stderr']
        fd = os.open(self.path, os.O_APPEND|os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(row, ensure_ascii=False)+'\n')
            f.flush()
            os.fsync(f.fileno())
        if event == 'finished' and result is not None and self.case_manager is not None:
            self.case_manager.record_execution({
                'tool': operation.tool_id, 'operation_id': operation.id,
                'command': row['command'], 'exit_code': result.returncode,
                'artifacts': row['artifacts'],
                'model_evidence': self.model_result(result),
            })
        if self.session is not None:
            self.attach_to_session(operation.id, event=row)
        return row

    @staticmethod
    def model_result(result):
        """Seul extrait proposé au modèle ; sorties brutes jamais dans la session."""
        from osint_guardrails import model_evidence
        content = result.stdout.decode('utf-8', 'replace') + '\n' + result.stderr.decode('utf-8', 'replace')
        return model_evidence(content, source='sortie outil', kind='tool')

    def events_for(self, operation_id, *, max_bytes=4*1024*1024):
        """Read expurgated technical events; never reconstruct an authorization."""
        if not re.fullmatch(r'[a-f0-9]{32}', operation_id):
            raise ValueError('Identifiant operation invalide')
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return ()
        with os.fdopen(fd, 'rb') as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            if os.fstat(f.fileno()).st_size > max_bytes:
                raise ValueError('Audit volumineux : lecture externe necessaire')
            rows = [json.loads(line) for line in f if line.strip()]
        sid = self.session.data['id'] if self.session is not None else None
        return tuple(row for row in rows if row.get('operation_id') == operation_id
                     and row.get('session_id') == sid)

    def attach_to_session(self, operation_id, *, event=None):
        """Explicit metadata only; investigation output requires separate human retention."""
        if self.session is None:
            raise ValueError('Session mission 09 non raccordee')
        metadata = {'audit': 'audit/tools/events.jsonl', 'operation_id': operation_id}
        if event:
            metadata.update({key: event[key] for key in
                ('event_id', 'timestamp', 'event', 'status', 'authorization_id', 'result_refs', 'artifacts')})
        self.session.add_message('tool', 'Tool audit reference: '+operation_id, operation_id,
            metadata=metadata, allow_tool=True)
