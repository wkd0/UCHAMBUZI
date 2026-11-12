# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_provider_profiles.py
# Role          : Profils de fournisseurs distants et catalogue explicite
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Profils sans secrets ; clés stockées séparément avec accès propriétaire."""
import http.client
import json
import os
import re
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from focus_settings import SettingsError, validate_ia


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.provider-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class ProviderProfiles:
    def __init__(self, settings):
        self.path = settings.path.parent / 'providers.json'
        self.secrets_path = settings.path.parent / 'provider-secrets.json'

    def _read(self, path):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return {}
        except (ValueError, OSError) as exc:
            raise SettingsError('Fichier de fournisseurs illisible ; conservé.') from exc
        if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, dict if path == self.path else str) for k, v in data.items()):
            raise SettingsError('Fichier de fournisseurs invalide ; conservé.')
        return data

    def list(self):
        return self._read(self.path)

    def save(self, name, values, key=''):
        if not isinstance(name, str) or not re.fullmatch(r'[^\x00-\x1f\x7f]{1,80}', name) or not name.strip():
            raise SettingsError('Nom de profil invalide.')
        if values.get('provider') not in ('openai', 'grok', 'anthropic'):
            raise SettingsError('Choisissez une famille distante.')
        if re.search(r'(?i)\bsk-[A-Za-z0-9_-]{8,}', name) or (key and key in name):
            raise SettingsError('Le nom du profil ne doit pas contenir de clé.')
        profiles = self.list()
        previous = profiles.get(name, {})
        env = previous.get('api_key_env') or 'UCHAMBUZI_KEY_' + secrets.token_hex(12).upper()
        if not isinstance(env, str) or not re.fullmatch(r'UCHAMBUZI_KEY_[0-9A-F]{24}', env):
            raise SettingsError('Identifiant de clé du profil invalide.')
        candidate = validate_ia(dict(values, api_key_env=env))
        if key and (len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key)):
            raise SettingsError('Clé API invalide.')
        credentials = self._read(self.secrets_path)
        if key:
            credentials[env] = key
            _write(self.secrets_path, credentials)
        if env not in credentials:
            raise SettingsError('Une clé API est nécessaire pour ce profil.')
        profiles[name] = {k: candidate[k] for k in ('provider', 'model', 'api_base_url', 'api_key_env', 'timeout')}
        _write(self.path, profiles)
        os.environ[env] = credentials[env]
        return candidate

    def activate(self, name, values):
        profile = self.list().get(name)
        if not isinstance(profile, dict) or set(profile) != {'provider', 'model', 'api_base_url', 'api_key_env', 'timeout'}:
            raise SettingsError('Profil inconnu ou invalide.')
        if not isinstance(profile['api_key_env'], str) or not re.fullmatch(r'UCHAMBUZI_KEY_[0-9A-F]{24}', profile['api_key_env']):
            raise SettingsError('Identifiant de clé du profil invalide.')
        candidate = validate_ia(dict(values, **profile))
        credentials = self._read(self.secrets_path)
        key = credentials.get(candidate['api_key_env'])
        if not key:
            raise SettingsError('Clé du profil introuvable.')
        os.environ[candidate['api_key_env']] = key
        return candidate

    def load_active_key(self, env):
        if isinstance(env, str) and re.fullmatch(r'UCHAMBUZI_KEY_[0-9A-F]{24}', env):
            key = self._read(self.secrets_path).get(env)
            if key:
                os.environ[env] = key


def discover_models(values, key):
    """Catalogue Responses compatible OpenAI ; jamais de redirection ni proxy."""
    values = validate_ia(values)
    if values['provider'] not in ('openai', 'grok'):
        raise SettingsError('Catalogue non pris en charge pour Claude Code ; saisissez le modèle.')
    if not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise SettingsError('Clé API absente ou invalide.')
    url = urlsplit(values['api_base_url'])
    conn = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=15)
    try:
        conn.request('GET', url.path.rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'})
        response = conn.getresponse()
        raw = response.read(2_000_001)
        if response.status != 200 or len(raw) > 2_000_000:
            raise SettingsError('Catalogue indisponible (HTTP %s).' % response.status)
        data = json.loads(raw)
        rows = data.get('data') if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) > 10000:
            raise SettingsError('Catalogue invalide.')
        return sorted({row['id'] for row in rows if isinstance(row, dict) and isinstance(row.get('id'), str)
                       and key not in row['id'] and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', row['id'])})
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise SettingsError('Impossible de lire le catalogue du fournisseur.') from exc
    finally:
        conn.close()
