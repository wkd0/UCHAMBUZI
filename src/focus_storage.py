# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_storage.py
# Role          : Stockage local atomique et verrouillage des sessions
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Stockage JSON local, avec revision optimiste et verrou interprocessus."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile


class CorruptSession(ValueError):
    pass


class ConflictError(RuntimeError):
    pass


def default_data_dir():
    # user-dirs.dirs est une configuration, pas un script shell a executer.
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'user-dirs.dirs'
    documents = Path.home() / 'Documents'
    try:
        for line in config.read_text(encoding='utf-8').splitlines():
            match = re.fullmatch(r'\s*XDG_DOCUMENTS_DIR="([^"`\\]*)"\s*', line)
            if match:
                value = match.group(1).replace('$HOME', str(Path.home()))
                if '$' not in value and Path(value).is_absolute():
                    documents = Path(value)
    except FileNotFoundError:
        pass
    return documents / 'uchambuzi-data'


class Storage:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else default_data_dir()
        self.sessions = self.root / 'sessions'

    def _prepare(self):
        self.sessions.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.sessions, 0o700)

    def path(self, sid):
        if not re.fullmatch(r'[0-9a-f]{32}', sid):
            raise ValueError('Identifiant invalide')
        return self.sessions / (sid + '.json')

    @contextlib.contextmanager
    def lock(self, sid):
        self._prepare()
        path = self.path(sid).with_suffix('.lock')
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def read(self, sid):
        try:
            with self.path(sid).open(encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict) or data.get('id') != sid or type(data.get('version')) is not int:
                raise ValueError('structure invalide')
            return data
        except (ValueError, UnicodeError, KeyError) as exc:
            raise CorruptSession('Session illisible ou invalide') from exc

    def write(self, sid, data, expected):
        with self.lock(sid):
            self.write_locked(sid, data, expected)

    def write_locked(self, sid, data, expected):
        """Ecrit sous un verrou de session deja acquis par l'appelant."""
        path = self.path(sid)
        current = self.read(sid) if path.exists() else None
        if (current.get('revision', 0) if current else None) != expected:
            raise ConflictError('Session modifiee par un autre processus')
        payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
        fd, temp = tempfile.mkstemp(prefix='.session-', dir=self.sessions)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, path)
            dfd = os.open(self.sessions, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
