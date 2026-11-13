# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_settings.py
# Role          : Definitions, validation et preferences atomiques Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Préférences utilisateur distinctes des paramètres temporaires. Aucun secret."""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
import re
from focus_storage import default_data_dir
from focus_workspace import directory


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Definition:
    default: object
    scope: str
    choices: tuple = ()


DEFINITIONS = {
    'theme': Definition('dark', 'user', ('dark', 'light')),
    'colors': Definition('auto', 'user', ('auto', 'truecolor', '256', '16', 'mono')),
    'unicode': Definition('auto', 'user', ('auto', 'on', 'off')),
    'animations': Definition(True, 'user'),
    'reduced_motion': Definition(False, 'user'),
    'history': Definition(False, 'user'),
    'tips': Definition(True, 'user'),
    'network': Definition('local', 'user', ('deny', 'local', 'external_confirm')),
    'confirmations': Definition('always', 'user', ('always',)),
    'permissions': Definition('prepare_only', 'session', ('prepare_only',)),
    'mode': Definition('assist', 'session'),
    'scenario': Definition(None, 'session'),
    'provider': Definition(None, 'session'),
    'model': Definition(None, 'session'),
    'temperature': Definition(None, 'session'),
    'max_tokens': Definition(None, 'session'),
    'context_size': Definition(None, 'session'),
    'timeout': Definition(300.0, 'session'),
    'workspace': Definition(None, 'session'),
}


def validate(key, value):
    spec = DEFINITIONS.get(key)
    if spec is None:
        raise SettingsError('Paramètre inconnu')
    if spec.choices:
        if value not in spec.choices or type(value) is not str:
            raise SettingsError('Valeur non prise en charge')
    elif type(spec.default) is bool:
        if type(value) is not bool:
            raise SettingsError('Booléen attendu')
    elif key in ('temperature', 'max_tokens', 'context_size', 'timeout'):
        from focus_providers import Capabilities, GenerationSettings, ProviderError
        try:
            GenerationSettings(**{key: value}).validate(Capabilities(context_size=True))
        except (ProviderError, TypeError):
            raise SettingsError('Paramètre de génération invalide') from None
    elif key == 'workspace':
        if not isinstance(value, str):
            raise SettingsError('Répertoire explicite requis')
        value = str(directory(value))
    elif key == 'mode' and (not isinstance(value, str) or not value):
        raise SettingsError('Mode explicite requis')
    elif value is not None and (not isinstance(value, str) or not value or len(value) > 512
                               or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SettingsError('Identifiant invalide')
    return value


class Preferences:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_data_dir() / 'config' / 'focus-preferences.json'
        self.values = {k: d.default for k, d in DEFINITIONS.items() if d.scope == 'user'}
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(payload, dict) or set(payload) != {'version', 'preferences'} or type(payload['version']) is not int or payload['version'] != 1:
                    raise SettingsError('Format de préférences invalide')
                items = payload['preferences']
                if not isinstance(items, dict) or any(k not in self.values for k in items):
                    raise SettingsError('Préférence inconnue')
                candidate = {k: validate(k, v) for k, v in items.items()}
            except (ValueError, TypeError, OSError):
                raise SettingsError('Préférences illisibles ou invalides ; fichier conservé') from None
            self.values.update(candidate)

    def set(self, key, value):
        if key not in self.values:
            raise SettingsError('Ce paramètre est limité à la session')
        value = validate(key, value)
        candidate = dict(self.values, **{key: value})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.focus-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump({'version': 1, 'preferences': candidate}, f, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.values = candidate


def parse_value(key, raw):
    if key not in DEFINITIONS:
        raise SettingsError('Paramètre inconnu')
    if raw in ('null', 'none'):
        return None
    if type(DEFINITIONS[key].default) is bool:
        if raw not in ('true', 'false', 'on', 'off'):
            raise SettingsError('Utilisez true ou false')
        return raw in ('true', 'on')
    if key in ('temperature', 'timeout', 'max_tokens', 'context_size'):
        try:
            return float(raw) if key in ('temperature', 'timeout') else int(raw)
        except ValueError:
            raise SettingsError('Nombre attendu') from None
    return raw


# Durées internes de génération, choisies selon le fournisseur. Elles restent
# invisibles dans les réglages courants et peuvent évoluer après calibration.
PROVIDER_TIMEOUTS = {'ollama': 300.0, 'openai': 120.0, 'grok': 120.0, 'anthropic': 180.0}

IA_DEFAULTS = dict(provider='ollama', model='redsage-qwen3:8b-dpo', host='127.0.0.1',
                   port=11434, timeout=PROVIDER_TIMEOUTS['ollama'], active_team='assist',
                   api_base_url='', api_key_env='', connection_kind='direct')

REMOTE_DEFAULTS = {
    'openai': ('https://api.openai.com/v1', 'OPENAI_API_KEY', 'gpt-6-luna'),
    'grok': ('https://api.x.ai/v1', 'XAI_API_KEY', 'grok-4.3'),
    'anthropic': ('https://api.anthropic.com', 'ANTHROPIC_API_KEY', 'claude-sonnet-4-6'),
}


def validate_ia(values):
    """Valide la configuration avant toute écriture ou permutation du runtime."""
    from conversation import OllamaRuntime
    candidate = dict(IA_DEFAULTS, **values)
    if candidate['provider'] not in ('ollama', 'openai', 'grok', 'anthropic'):
        raise SettingsError('Fournisseur IA non pris en charge.')
    if candidate['connection_kind'] not in ('direct', 'external'):
        raise SettingsError('Type de connexion invalide.')
    host = candidate['host']
    if not isinstance(host, str) or not host or len(host) > 253 or not re.fullmatch(r'[A-Za-z0-9._:-]+', host):
        raise SettingsError('Hôte invalide : indiquez un nom ou une adresse sans URL.')
    if type(candidate['timeout']) not in (float, int) or not math.isfinite(candidate['timeout']):
        raise SettingsError('Délai invalide.')
    if not isinstance(candidate['api_base_url'], str) or not isinstance(candidate['api_key_env'], str):
        raise SettingsError('Adresse API et nom de variable doivent être du texte.')
    env_names = {candidate['api_key_env'], *(item[1] for item in REMOTE_DEFAULTS.values())}
    secret_values = [os.environ[name] for name in env_names if name and os.environ.get(name)]
    if (any(secret in value for secret in secret_values for value in candidate.values()
            if isinstance(value, str)) or
            any(re.search(r'(?i)\bsk-[A-Za-z0-9_-]{8,}', value)
                for value in candidate.values() if isinstance(value, str))):
        raise SettingsError('Les réglages ne doivent contenir aucune clé ; indiquez seulement son nom de variable.')
    try:
        OllamaRuntime(candidate['model'], candidate['port'], candidate['timeout'])
        if candidate['provider'] in REMOTE_DEFAULTS:
            # Les anciens réglages OpenAI n'avaient ni URL ni variable explicite.
            default_url, default_env, _ = REMOTE_DEFAULTS[candidate['provider']]
            candidate['api_base_url'] = candidate['api_base_url'] or default_url
            candidate['api_key_env'] = candidate['api_key_env'] or default_env
            if candidate['provider'] == 'anthropic':
                from focus_claude_runtime import ClaudeCodeRuntime
                ClaudeCodeRuntime(candidate['model'], candidate['api_base_url'],
                                  token_env=candidate['api_key_env'], timeout=candidate['timeout'])
            else:
                from focus_responses_runtime import ResponsesRuntime
                ResponsesRuntime(candidate['model'], candidate['api_base_url'],
                                 family=candidate['provider'], api_key_env=candidate['api_key_env'],
                                 timeout=candidate['timeout'])
        elif candidate['api_base_url'] or candidate['api_key_env']:
            raise ValueError('Effacez les paramètres distants avant de choisir Ollama.')
    except (TypeError, ValueError) as exc:
        raise SettingsError(str(exc)) from None
    if candidate['active_team'] not in ('assist', 'osint', 'red', 'blue', 'purple'):
        raise SettingsError('Team invalide.')
    return candidate


class IASettings:
    """Réglages du REPL ; fichier invalide conservé, remplacement atomique à 0600."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(
            os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
        ) / 'uchambuzi-data' / 'config' / 'settings.json'
        self.values = dict(IA_DEFAULTS)
        self.load_error = None
        self.loaded = False
        self._extra = {}
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(payload, dict):
                raise SettingsError('Objet JSON attendu.')
            # Les clés historiques ou futures restent intactes lors d'une édition.
            known = {k: v for k, v in payload.items() if k in IA_DEFAULTS}
            if 'connection_kind' not in known and known.get('provider') == 'anthropic':
                known['connection_kind'] = 'external'  # Anciennes configurations : Claude Code.
            self.values = validate_ia(known)
            self._extra = {k: v for k, v in payload.items() if k not in IA_DEFAULTS}
            self.loaded = True
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            self.load_error = 'Configuration IA illisible ou invalide ; fichier conservé : ' + str(exc)

    def update(self, **changes):
        if self.load_error:
            raise SettingsError(self.load_error)
        if changes.keys() - IA_DEFAULTS.keys():
            raise SettingsError('Paramètre IA inconnu.')
        candidate = validate_ia(dict(self.values, **changes))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.settings-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(dict(self._extra, **candidate), stream, ensure_ascii=False, allow_nan=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        self.values = candidate
        self.loaded = True


def initialize_ia(owner, model, port, timeout, runtime=None):
    """Charge les réglages sans effectuer de requête réseau au démarrage."""
    from conversation import DEFAULT_TIMEOUT, Session
    owner.settings = IASettings()
    values = dict(owner.settings.values)
    from focus_provider_profiles import ProviderProfiles
    try:
        ProviderProfiles(owner.settings).load_active_key(values.get('api_key_env', ''))
    except SettingsError:
        pass  # Conserver les fichiers ; le runtime signalera la clé absente.
    if model is not None:
        values['model'] = model
    if port != 11434:
        values['port'] = port
    if timeout != DEFAULT_TIMEOUT:
        values['timeout'] = timeout
    else:
        # Ignore les anciens délais personnalisés et applique la politique du fournisseur.
        values['timeout'] = PROVIDER_TIMEOUTS[values['provider']]
    values = validate_ia(values)
    owner.model, owner.host, owner.port, owner.timeout = (values[k] for k in ('model', 'host', 'port', 'timeout'))
    owner.adapter = runtime or create_ia_runtime(values)
    owner.session = Session(owner.adapter, owner.context_budget)


def create_ia_runtime(values):
    """Construit l'adaptateur configuré sans lire de clé ni contacter de service."""
    values = validate_ia(values)
    if values['provider'] == 'ollama':
        from focus_providers import ConfiguredOllamaRuntime
        return ConfiguredOllamaRuntime(values['model'], values['port'], values['timeout'], host=values['host'])
    if values['provider'] == 'anthropic':
        from focus_claude_runtime import ClaudeCodeRuntime, AnthropicAPIRuntime
        runtime = AnthropicAPIRuntime if values.get('connection_kind') == 'direct' else ClaudeCodeRuntime
        return runtime(values['model'], values['api_base_url'],
                                 token_env=values['api_key_env'], timeout=values['timeout'])
    from focus_responses_runtime import ResponsesRuntime
    return ResponsesRuntime(values['model'], values['api_base_url'], family=values['provider'],
                            api_key_env=values['api_key_env'], timeout=values['timeout'])


class IASettingsMenu:
    """Dialogue numéroté commun aux interfaces Textual et Prompt Toolkit."""

    def __init__(self, owner, emit):
        self.owner, self.emit = owner, emit
        self.state = None
        self.models = []

    def open(self):
        from rich.table import Table
        owner = self.owner
        table = Table(title='Configuration IA', show_header=False)
        for label, value in (
            ('AI Provider', owner.settings.values['provider']),
            ('Model', getattr(owner.adapter, 'model', None) or '—'),
            ('Hôte', getattr(owner, 'host', '127.0.0.1')), ('Port', owner.port),
            ('Adresse API', owner.settings.values.get('api_base_url') or '—'),
            ('Variable de clé', owner.settings.values.get('api_key_env') or '—'),
            ('Case', owner.case_manager.active_case_id or '—'),
        ):
            table.add_row(label, str(value))
        self.emit(table)
        if getattr(owner, 'settings', None) and owner.settings.load_error:
            self.emit(owner.settings.load_error)
        self.main()

    def main(self):
        self.state = 'main'
        self.emit('[1] Choisir ou saisir un modèle\n'
                  f'[2] Modifier l’hôte / port (actuel : {getattr(self.owner, "host", "127.0.0.1")}:{self.owner.port})\n'
                  '[3] Tester la connexion au serveur Ollama\n'
                  '[4] Choisir le fournisseur\n[5] Modifier l’adresse API HTTPS\n'
                  '[6] Modifier le nom de variable de clé\n[0] Fermer')

    def submit(self, answer):
        answer = answer.strip()
        if answer == '0':
            self.state = None
            return
        if self.state == 'main':
            if answer == '1' and self.owner.settings.values['provider'] != 'ollama':
                self.state = 'model'
                self.models = []
                self.emit('Nom du modèle distant (0 : fermer) :')
                return
            if answer in ('1', '3'):
                try:
                    self.models = self.owner._ollama_models()
                    self.emit(f'Connexion Ollama réussie : {len(self.models)} modèle(s).')
                except Exception as exc:
                    self.models = []
                    self.emit('Ollama indisponible. Vérifiez systemctl status ollama ou lancez ollama serve. ' + str(exc))
                if answer == '1':
                    for index, model in enumerate(self.models, 1):
                        name = getattr(model, 'id', model)
                        self.emit(f'[{index}] {name}')
                    self.emit('Numéro ou nom de modèle manuel (0 : fermer) :')
                    self.state = 'model'
            elif answer == '2':
                self.state = 'endpoint'
                self.emit('Hôte:port (ex. 127.0.0.1:11434 ; IPv6 [::1]:11434 ; 0 : fermer) :')
            elif answer == '4':
                self.state = 'provider'
                self.emit('Fournisseur : ollama, openai, grok ou anthropic :')
            elif answer == '5':
                self.state = 'base_url'
                self.emit('Adresse HTTPS du fournisseur :')
            elif answer == '6':
                self.state = 'key_env'
                self.emit('Nom de la variable d’environnement contenant la clé (pas la clé) :')
            else:
                self.emit('Choix invalide : 0 à 6.')
            return
        command = None
        if self.state == 'model':
            if answer.isdecimal():
                index = int(answer) - 1
                if not 0 <= index < len(self.models):
                    self.emit('Numéro de modèle invalide.')
                    return
                m = self.models[index]
                answer = str(getattr(m, 'id', m))
            command = 'model ' + answer
        elif self.state == 'endpoint':
            command = 'endpoint ' + answer
        elif self.state == 'provider':
            command = 'ai ' + answer
        elif self.state in ('base_url', 'key_env'):
            command = self.state + ' ' + answer
        if command and self.owner.handle_settings(command, ollama=self.state == 'model' and
                                                   self.owner.settings.values['provider'] == 'ollama'):
            self.main()
