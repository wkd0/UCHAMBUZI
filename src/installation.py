# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : installation.py
# Role          : Installation utilisateur complete avec verification des fichiers geres
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Liste explicite de fichiers; aucune copie de documents internes ou de données utilisateur."""
from contextlib import contextmanager
import ast
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

CORE_PAYLOAD = (
    'src/uchambuzi.py', 'src/conversation.py', 'src/indices_outils.py',
    'src/documentation_locale.py', 'src/commandes.py', 'src/parcours.py', 'src/installation.py',
    'data/documentation/catalog.json', 'data/documentation/file.md', 'data/documentation/dig.md',
    'data/commands/syntax.md',
)
PREVIOUS_PAYLOAD = CORE_PAYLOAD + ('data/documentation/dig-kali.md',)
BETA3_PAYLOAD = PREVIOUS_PAYLOAD + tuple('data/documentation/' + name + '-kali.md'
                                         for name in ('exiftool', 'strings', 'whois', 'tshark', 'curl'))
FOCUS_020405_PAYLOAD = BETA3_PAYLOAD + (
    'src/focus_contracts.py',
    'src/focus_legacy_adapter.py',
    'src/focus_ui.py',
    'src/focus_view.py',
    'src/focus_branding.py',
)
FOCUS_030405_PAYLOAD = FOCUS_020405_PAYLOAD + (
    'src/focus_editor.py',
)
FOCUS_06080911_PAYLOAD = FOCUS_030405_PAYLOAD + (
    'src/focus_modes.py',
    'src/focus_profiles.py',
    'src/focus_ai.py',
    'src/focus_providers.py',
    'src/focus_sessions.py',
    'src/focus_storage.py',
    'src/focus_workspace.py',
    'src/focus_settings.py',
    'src/focus_settings_ui.py',
    'src/focus_selectors.py',
    'src/focus_animations.py',
    'src/focus_theme.py',
)
FOCUS_ASSEMBLY_43_PAYLOAD = FOCUS_06080911_PAYLOAD + (
    'src/focus_scenarios.py',
    'src/focus_orchestrator.py',
    'src/focus_permissions.py',
    'src/focus_tool_audit.py',
    'src/focus_tool_process.py',
    'src/focus_tool_registry.py',
    'src/focus_tools.py',
    'src/focus_assembly.py',
)
FOCUS_COMPLETE_PAYLOAD = FOCUS_06080911_PAYLOAD + (
    'src/focus_scenarios.py',
    'src/focus_orchestrator.py',
    'src/focus_permissions.py',
    'src/focus_tool_audit.py',
    'src/focus_tool_process.py',
    'src/focus_tool_registry.py',
    'src/focus_tools.py',
    'src/focus_tool_conversation.py',
    'src/focus_assembly.py',
    'src/focus_settings_catalog.py',
    'src/focus_terminal_keys.py',
)
# Le presse-papiers et le REPL interactif moderne font partie de la distribution officielle.
FOCUS_44_PAYLOAD = FOCUS_COMPLETE_PAYLOAD + ('src/focus_clipboard.py',)
FOCUS_REPL_PAYLOAD = FOCUS_44_PAYLOAD + ('src/focus_repl.py',)
FOCUS_TRANSCRIPT_PAYLOAD = FOCUS_REPL_PAYLOAD + ('src/focus_repl_transcript.py',)
FOCUS_PRE_UX_PAYLOAD = FOCUS_TRANSCRIPT_PAYLOAD + ('src/focus_banner_logo.py',)
FOCUS_FINAL_PAYLOAD = FOCUS_PRE_UX_PAYLOAD + (
    'src/repl_theme.py',
    'src/repl_commands.py',
    'src/repl_welcome.py',
    'src/repl_render.py',
    'src/repl_render_cells.py',
    'src/repl_input.py',
    'src/repl_menu.py',
    'src/repl_approval.py',
    'src/repl_activity.py',
    'src/focus_textual.py',
)
OSINT_PAYLOAD = FOCUS_FINAL_PAYLOAD + (
    'src/focus_teams.py', 'src/tools_catalog.py', 'src/tools_installer.py',
    'src/osint_playbooks.py', 'src/osint_guardrails.py', 'src/osint_report.py',
    'src/osint_specialties.py', 'src/osint_wmn.py',
    'data/tools/catalog.json', 'data/tools/wmn-data.json', 'data/tools/wmn-LICENSE.md',
)
PRE_RAG_OSINT_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += tuple('data/documentation/' + name + '.md' for name in
                       ('subfinder', 'gau', 'maigret', 'blackbird', 'holehe', 'whatsmyname', 'phoneinfoga'))
PRE_PROMPT_OSINT_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/focus_textual_prompt.py', 'src/focus_textual_stream.py')
PRE_SHELL_OSINT_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/free_shell.py',)
PRE_MODEL_PROFILES_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/focus_model_profiles.py', 'src/focus_responses_runtime.py', 'src/focus_claude_runtime.py')
PRE_BROWSER_OSINT_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/tool_guidance.py', 'src/tools_browser.py')
PRE_RESUME_OSINT_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/focus_resume.py',)
PRE_PROVIDER_PROFILES_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('src/focus_provider_profiles.py',)
AI_CALIBRATION_FILES = (
    'src/ai_calibration/__init__.py',
    'src/ai_calibration/response_guides.py',
)
PRE_AI_CALIBRATION_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += AI_CALIBRATION_FILES
PRE_AI_PROVIDER_REFACTOR_PAYLOAD = OSINT_PAYLOAD
AI_CALIBRATION_FILES += ('src/ai_calibration/providers.py',)
OSINT_PAYLOAD += ('src/ai_calibration/providers.py',)
PRE_AMASS_GUIDE_PAYLOAD = OSINT_PAYLOAD
OSINT_PAYLOAD += ('data/documentation/amass.md', 'docs/amass-v5.md')
KNOWN_PAYLOAD_SETS = (
    frozenset(PRE_AMASS_GUIDE_PAYLOAD),
    frozenset(PRE_PROVIDER_PROFILES_PAYLOAD),
    frozenset(PRE_AI_CALIBRATION_PAYLOAD),
    frozenset(PRE_AI_PROVIDER_REFACTOR_PAYLOAD),
    frozenset(PRE_BROWSER_OSINT_PAYLOAD),
    frozenset(PRE_RESUME_OSINT_PAYLOAD),
    frozenset(PRE_BROWSER_OSINT_PAYLOAD + ('src/focus_resume.py',)),
    frozenset(PRE_SHELL_OSINT_PAYLOAD),
    frozenset(PRE_SHELL_OSINT_PAYLOAD + ('src/focus_resume.py',)),
    frozenset(PRE_MODEL_PROFILES_PAYLOAD),
    frozenset(PRE_SHELL_OSINT_PAYLOAD + ('src/focus_model_profiles.py', 'src/focus_responses_runtime.py', 'src/focus_claude_runtime.py')),
    frozenset(PRE_PROMPT_OSINT_PAYLOAD),
    frozenset(PRE_RAG_OSINT_PAYLOAD),
    frozenset(OSINT_PAYLOAD),
    frozenset(CORE_PAYLOAD),
    frozenset(PREVIOUS_PAYLOAD),
    frozenset(BETA3_PAYLOAD),
    frozenset(FOCUS_020405_PAYLOAD),
    frozenset(FOCUS_030405_PAYLOAD),
    frozenset(FOCUS_06080911_PAYLOAD),
    frozenset(FOCUS_ASSEMBLY_43_PAYLOAD),
    frozenset(FOCUS_COMPLETE_PAYLOAD),
    frozenset(FOCUS_44_PAYLOAD),
    frozenset(FOCUS_REPL_PAYLOAD),
    frozenset(FOCUS_TRANSCRIPT_PAYLOAD),
    frozenset(FOCUS_PRE_UX_PAYLOAD),
    frozenset(FOCUS_FINAL_PAYLOAD),
)

# Couverture explicite des 10 familles fonctionnelles Focus et du raccordement final.
FOCUS_COMPONENT_GROUPS = {
    'tui_and_editor': (
        'src/focus_contracts.py', 'src/focus_legacy_adapter.py',
        'src/focus_ui.py', 'src/focus_editor.py', 'src/focus_terminal_keys.py',
        'src/focus_clipboard.py', 'src/focus_repl.py', 'src/focus_repl_transcript.py',
        'src/repl_theme.py', 'src/repl_commands.py', 'src/repl_welcome.py',
        'src/repl_render.py', 'src/repl_render_cells.py', 'src/repl_input.py',
        'src/repl_menu.py', 'src/repl_approval.py', 'src/repl_activity.py',
        'src/focus_textual.py',
    ),
    'markdown_renderer': ('src/focus_view.py',),
    'branding': ('src/focus_branding.py',),
    'eight_modes': ('src/focus_modes.py', 'src/focus_profiles.py'),
    'scenarios': ('src/focus_scenarios.py', 'src/focus_orchestrator.py'),
    'ai_providers': ('src/focus_ai.py', 'src/focus_providers.py', 'src/focus_model_profiles.py',
                     'src/focus_responses_runtime.py', 'src/focus_claude_runtime.py',
                     *AI_CALIBRATION_FILES),
    'sessions_and_storage': ('src/focus_sessions.py', 'src/focus_storage.py', 'src/focus_workspace.py'),
    'kali_tools': (
        'src/focus_tools.py', 'src/focus_tool_conversation.py',
        'src/focus_tool_process.py', 'src/focus_tool_registry.py',
    ),
    'permissions_and_audits': ('src/focus_permissions.py', 'src/focus_tool_audit.py'),
    'settings_selectors_animations': (
        'src/focus_settings.py', 'src/focus_settings_catalog.py', 'src/focus_settings_ui.py',
        'src/focus_selectors.py', 'src/focus_animations.py', 'src/focus_theme.py',
    ),
    'final_assembly': ('src/focus_assembly.py',),
}

# Registre documentaire des modules Focus 03 et 06..11 pour compatibilité ascendante.
PENDING_FOCUS_MODULES = {
    'mission03_editor': ('src/focus_editor.py', 'src/focus_terminal_keys.py'),
    'mission06_modes': ('src/focus_modes.py', 'src/focus_profiles.py'),
    'mission07_scenarios': ('src/focus_scenarios.py', 'src/focus_orchestrator.py'),
    'mission08_ai_models': ('src/focus_ai.py', 'src/focus_providers.py'),
    'mission09_sessions': ('src/focus_sessions.py', 'src/focus_storage.py', 'src/focus_workspace.py'),
    'mission10_tools': (
        'src/focus_tools.py', 'src/focus_tool_conversation.py', 'src/focus_permissions.py',
        'src/focus_tool_audit.py', 'src/focus_tool_process.py', 'src/focus_tool_registry.py',
    ),
    'mission11_settings': (
        'src/focus_settings.py', 'src/focus_settings_catalog.py', 'src/focus_settings_ui.py',
        'src/focus_selectors.py', 'src/focus_animations.py', 'src/focus_theme.py',
    ),
}


def vendored_payload(root):
    """Include only pinned local artifacts and accompanying upstream licences."""
    catalog = root / 'data/tools/catalog.json'
    if not catalog.is_file():
        return ()
    result = []
    if (root / 'vendor/README.uchambuzi.md').is_file():
        result.append('vendor/README.uchambuzi.md')
    if (root / 'vendor/SHA256SUMS').is_file():
        result.append('vendor/SHA256SUMS')
    for tool in json.loads(catalog.read_text(encoding='utf-8'))['tools']:
        artifact = tool.get('artifact')
        if tool.get('source') != 'vendored' or not artifact:
            continue
        folder = root / 'vendor' / tool['id']
        candidates = (folder / 'bin' / artifact['file'], folder / artifact['file'])
        source = next((p for p in candidates if p.is_file()), None)
        if source is None:
            raise ValueError('Artefact vendor absent : ' + tool['id'])
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError('Lien vendor interdit.')
        if hashlib.sha256(source.read_bytes()).hexdigest() != artifact['sha256']:
            raise ValueError('Empreinte vendor incorrecte : ' + tool['id'])
        result.append(source.relative_to(root).as_posix())
        licences = [p for p in folder.iterdir()
                    if p.is_file() and p.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))]
        if tool['id'] == 'blackbird':
            # L'ancien payload utilisateur omettait cette licence. Sa présence
            # dans une source neuve l'ajoute, sans empêcher sa propre mise à jour.
            nested_licence = folder / 'docs/LICENSE'
            if nested_licence.exists() or nested_licence.is_symlink():
                licences.append(nested_licence)
        if any(not p.is_file() or p.is_symlink() or
               not p.resolve().is_relative_to(root.resolve()) for p in licences):
            raise ValueError('Licence vendor invalide : ' + tool['id'])
        result.extend(p.relative_to(root).as_posix() for p in licences)
    return tuple(result)


def debian_vendor_payload(root):
    """Package the vendor tree, excluding Git metadata and generated caches."""
    vendored_payload(root)  # Validate every artifact approved by the catalogue.
    vendor = root / 'vendor'
    catalog_path = root / 'data/tools/catalog.json'
    catalogue = json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.is_file() else {'tools': []}
    blocked = {tool['id'] for tool in catalogue['tools']
               if tool.get('license', 'NOASSERTION') in ('NOASSERTION', 'UNKNOWN', '')}
    result = []
    for path in sorted(vendor.rglob('*')):
        relative = path.relative_to(vendor)
        if any(part in ('.git', '__pycache__', '.pytest_cache') for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError('Lien vendor interdit.')
        if relative.parts[0] in blocked:
            continue
        if path.is_file() and path.suffix not in ('.pyc', '.pyo'):
            result.append(path.relative_to(root).as_posix())
    return tuple(result)


def resolve_payload(source=None):
    """Sélectionne l'inventaire explicite complet correspondant aux modules présents dans la source."""
    root = Path(source).resolve() if source is not None else Path(__file__).resolve().parent.parent
    # Une source OSINT partielle doit échouer, sans repli silencieux sur Focus.
    if any((root / rel).exists() for rel in OSINT_PAYLOAD if rel not in FOCUS_FINAL_PAYLOAD):
        return OSINT_PAYLOAD + vendored_payload(root)
    for candidate in (
        OSINT_PAYLOAD,        FOCUS_FINAL_PAYLOAD,
        FOCUS_PRE_UX_PAYLOAD,
        FOCUS_COMPLETE_PAYLOAD,
        FOCUS_ASSEMBLY_43_PAYLOAD,
        FOCUS_06080911_PAYLOAD,
        FOCUS_030405_PAYLOAD,
        FOCUS_020405_PAYLOAD,
    ):
        if all((root / rel).is_file() for rel in candidate):
            return candidate
    return globals().get('PAYLOAD', FOCUS_020405_PAYLOAD)


PAYLOAD = resolve_payload()
if 'src/focus_resume.py' in PAYLOAD:
    KNOWN_PAYLOAD_SETS += (frozenset(PAYLOAD) - {'src/focus_resume.py'},)
if 'vendor/blackbird/docs/LICENSE' in PAYLOAD:
    # Reconnaître les installations antérieures à l'ajout de la licence GPL
    # Blackbird au manifeste utilisateur.
    KNOWN_PAYLOAD_SETS += (frozenset(PAYLOAD) - {'vendor/blackbird/docs/LICENSE'},)
    if 'src/focus_resume.py' in PAYLOAD:
        KNOWN_PAYLOAD_SETS += (frozenset(PAYLOAD) - {'vendor/blackbird/docs/LICENSE', 'src/focus_resume.py'},)
KNOWN_PAYLOAD_SETS += tuple(
    payload - {'data/documentation/amass.md', 'docs/amass-v5.md'}
    for payload in (frozenset(PAYLOAD),) + KNOWN_PAYLOAD_SETS
    if 'data/documentation/amass.md' in payload
)


def inspect_component_coverage(source=None):
    """Vérifie quels groupes de composants Focus sont effectivement présents dans la source ou l'installation."""
    root = Path(source).resolve() if source is not None else Path(__file__).resolve().parent.parent
    present = {}
    missing = {}
    for group, files in FOCUS_COMPONENT_GROUPS.items():
        if all((root / rel).is_file() for rel in files):
            present[group] = files
        else:
            missing[group] = tuple(rel for rel in files if not (root / rel).is_file())
    return {
        'root': str(root),
        'complete': not missing,
        'present_groups': present,
        'missing_groups': missing,
    }


def check_system_prerequisites():
    """Vérifie les prérequis système obligatoires (D-025 : Python >= 3.10, stdlib, tzdata) sans imposer d'IA."""
    if sys.version_info < (3, 10):
        raise ValueError(f'Python 3.10+ requis ; version détectée : {sys.version.split()[0]}.')
    missing_stdlib = []
    for mod_name in ('argparse', 'asyncio', 'curses', 'fcntl', 'hashlib', 'http.client', 'json', 'pty', 'sqlite3', 'zoneinfo'):
        try:
            __import__(mod_name)
        except ImportError:
            if mod_name not in ('curses', 'pty', 'sqlite3'):
                missing_stdlib.append(mod_name)
    if missing_stdlib:
        raise ValueError('Modules standard Python obligatoires manquants : ' + ', '.join(missing_stdlib))
    try:
        zoneinfo.ZoneInfo('UTC')
    except Exception as exc:
        raise ValueError('Base système de fuseaux horaires (tzdata) absente ou invalide.') from exc
    return {
        'python_version': sys.version.split()[0],
        'platform': sys.platform,
        'tzdata': True,
        'pip_dependencies_required': 0,
        'ai_required': False,
    }


def paths():
    return Path.home() / '.local/share/uchambuzi', Path.home() / '.local/bin/uchambuzi'


def user_data_path():
    """Résolution XDG sans exécuter le contenu de user-dirs.dirs."""
    home = Path.home()
    configured = os.environ.get('XDG_DOCUMENTS_DIR')
    if configured is None:
        config = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
        if not config.is_absolute():
            raise ValueError('XDG_CONFIG_HOME doit être absolu.')
        file = config / 'user-dirs.dirs'
        if file.is_file():
            for line in file.read_text(encoding='utf-8').splitlines():
                match = re.fullmatch(r'\s*XDG_DOCUMENTS_DIR="(.*)"\s*', line)
                if match:
                    configured = match.group(1)
    if configured:
        configured = configured.replace('${HOME}', str(home)).replace('$HOME', str(home))
        documents = Path(configured)
        if not documents.is_absolute() or '$' in configured or '`' in configured:
            raise ValueError('Dossier Documents XDG non reconnu.')
    else:
        documents = home / 'Documents'
    # XDG utilise HOME pour désactiver un dossier standard.
    if documents == home:
        documents = home / 'Documents'
    return documents / 'uchambuzi-data'


@contextmanager
def user_files_lock():
    """Sérialise la maintenance et la migration pour ce compte Linux."""
    # Le répertoire existant évite de créer un fichier de verrou dans l'application.
    descriptor = os.open(Path.home(), os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def private_directory(path):
    no_links(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def prepare_user_data():
    root = user_data_path()
    private_directory(root)
    private_directory(root / 'config')
    return root


def migrate_user_data():
    """Copie vérifiée, sauvegarde préalable, sources anciennes conservées.

    Les données de format inconnu ne sont jamais interprétées comme préférences.
    Un conflit interrompt la copie avant toute écriture. Aucun secret n'est extrait.
    """
    app, _ = paths()
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    if not config_home.is_absolute():
        raise ValueError('XDG_CONFIG_HOME doit être absolu.')
    sources = [(config_home / 'uchambuzi', 'legacy-config')]
    if app.exists():
        managed = set(metadata(app)['files']) if (app / 'install.json').exists() else set()
        for item in app.rglob('*'):
            no_links(item)
            relative = item.relative_to(app).as_posix()
            if (relative not in managed and relative not in PAYLOAD and relative != 'install.json'
                    and '__pycache__' not in item.parts and not item.is_dir()
                    and not relative.startswith(('vendor/', 'tests/', 'docs/', 'debian/', 'packaging/', 'scripts/', 'assets/', 'releases/'))
                    and not item.name.startswith('.')):
                sources.append((item, 'legacy-app/' + relative))
    entries = []
    root = user_data_path()
    for source, prefix in sources:
        no_links(source)
        if not source.exists():
            continue
        files = source.rglob('*') if source.is_dir() else [source]
        for file in files:
            no_links(file)
            if file.is_dir():
                continue
            if not file.is_file():
                raise ValueError('Donnée ancienne non régulière : ' + str(file))
            suffix = file.relative_to(source).as_posix() if source.is_dir() else ''
            relative = Path(prefix) / suffix
            content = file.read_bytes()
            for base in (root / 'migration-backups', root):
                target = base / relative
                no_links(target)
                if target.exists() and (not target.is_file() or target.read_bytes() != content):
                    raise ValueError('Conflit de migration, aucun écrasement : ' + str(target))
            entries.append((relative, content))
    prepare_user_data()
    for relative, content in entries:
        for base in (root / 'migration-backups', root):
            target = base / relative
            for parent in reversed(target.parent.parents):
                if parent == root or root in parent.parents:
                    private_directory(parent)
            private_directory(target.parent)
            if not target.exists():
                atomic_write(target, content)
            target.chmod(0o600)
            if target.read_bytes() != content:
                raise ValueError('Échec de vérification de migration : ' + str(target))
    return root


CONFIG_KEYS = {'model', 'port', 'timeout', 'context_budget', 'provider', 'host', 'active_team'}


@user_files_lock()
def load_preferences():
    path = migrate_user_data() / 'config/settings.json'
    no_links(path)
    if not path.exists():
        return {}
    path.chmod(0o600)
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_preferences(data)
    return data


def validate_preferences(data):
    if type(data) is not dict or set(data) - CONFIG_KEYS:
        raise ValueError('Configuration inconnue ; clés autorisées : modèle local, port, délai, budget.')
    if 'model' in data and (data['model'] is not None and
            (type(data['model']) is not str or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}', data['model']))):
        raise ValueError('Modèle local invalide.')
    if 'provider' in data and (data['provider'] is not None and (type(data['provider']) is not str or data['provider'] not in ('ollama', 'openai'))):
        raise ValueError('Fournisseur local invalide.')
    if 'host' in data and (data['host'] is not None and (type(data['host']) is not str or not re.fullmatch(r'[A-Za-z0-9._:-]+', data['host']))):
        raise ValueError('Hôte local invalide.')
    if 'active_team' in data and (data['active_team'] is not None and (type(data['active_team']) is not str or data['active_team'] not in ('osint', 'red', 'blue', 'purple'))):
        raise ValueError('Team invalide.')
    for key, minimum, maximum in [('port', 1, 65535), ('timeout', 0.001, 600), ('context_budget', 1024, 128000)]:
        if key in data and (type(data[key]) not in (int, float) or not minimum <= data[key] <= maximum
                            or (key != 'timeout' and type(data[key]) is not int)):
            raise ValueError('Préférence invalide : ' + key)


@user_files_lock()
def save_preferences(data):
    validate_preferences(data)
    root = prepare_user_data()
    path = root / 'config/settings.json'
    no_links(path)
    # Sauvegarde avant modification explicite d'une configuration existante.
    if path.exists() and path.read_bytes() != (json.dumps(data, indent=2) + '\n').encode():
        backup = root / 'config' / ('settings-' + checksum(path.read_bytes()) + '.backup.json')
        no_links(backup)
        if backup.exists() and backup.read_bytes() != path.read_bytes():
            raise ValueError('Conflit de sauvegarde de configuration.')
        if not backup.exists():
            atomic_write(backup, path.read_bytes())
    atomic_write(path, (json.dumps(data, indent=2) + '\n').encode())


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def no_links(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Lien symbolique refusé dans le chemin d’installation : ' + str(part))


def wrapper(app):
    return f'#!/bin/sh\nexec python3 {shlex.quote(str(app / "src/uchambuzi.py"))} "$@"\n'.encode()


def metadata(app):
    path = app / 'install.json'
    no_links(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    if (type(data) is not dict or data.get('created_by') != 'uchambuzi-install'
            or data.get('schema_version') != 2 or type(data.get('files')) is not dict
            or (frozenset(data['files']) not in KNOWN_PAYLOAD_SETS and set(data['files']) != set(PAYLOAD))
            or any(type(v) is not str or not re.fullmatch('[0-9a-f]{64}', v) for v in data['files'].values())
            or data.get('launcher_sha256') != checksum(wrapper(app))):
        raise ValueError('Manifeste non reconnu. Migration ancienne installation non automatique.')
    return data


def verify_owned(app, launcher, data):
    # Préflight complet : aucun retrait/écrasement si un seul fichier géré a changé.
    for name, expected in data['files'].items():
        target = app / name
        no_links(target)
        if target.exists() and (not target.is_file() or checksum(target.read_bytes()) != expected):
            raise ValueError('Fichier géré modifié, à préserver : ' + str(target))
    no_links(launcher)
    if launcher.exists() and (not launcher.is_file() or checksum(launcher.read_bytes()) != data['launcher_sha256']):
        raise ValueError('Lanceur modifié, à préserver : ' + str(launcher))


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.uchambuzi-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_installation(files):
    """Restaure les fichiers gérés si une écriture échoue (hors arrêt brutal).

    Les copies de migration et sauvegardes ne sont jamais retirées au retour arrière.
    Les répertoires préexistants, notamment ceux des données résiduelles, sont conservés.
    """
    originals = {}
    directories = set()
    for path, content, mode in files:
        no_links(path)
        originals[path] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
        directories.update(parent for parent in path.parents if not parent.exists())
    attempted = []
    try:
        for path, content, mode in files:
            attempted.append(path)
            if not path.exists() or path.read_bytes() != content or path.stat().st_mode & 0o777 != mode:
                atomic_write(path, content, mode)
    except (OSError, KeyboardInterrupt) as error:
        failures = []
        for path in reversed(attempted):
            try:
                no_links(path)
                original = originals[path]
                if original is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or (path.read_bytes(), path.stat().st_mode & 0o777) != original:
                    atomic_write(path, *original)
            except OSError as rollback_error:
                failures.append(str(rollback_error))
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()  # Uniquement les nouveaux répertoires vides.
            except OSError:
                pass
        if failures:
            raise OSError('Retour arrière incomplet ; préserver les sauvegardes : ' + '; '.join(failures)) from error
        raise


def local_git(source, *args):
    try:
        result = subprocess.run(['git', '-C', str(source), *args], capture_output=True, text=True, timeout=3)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


RELEASE_REPOSITORY = 'https://github.com/wkd0/UCHAMBUZI.git'
RELEASE_API = 'https://api.github.com/repos/wkd0/UCHAMBUZI/releases/tags/'
RELEASE_DOWNLOAD = 'https://github.com/wkd0/UCHAMBUZI/releases/download/'
RELEASE_DOWNLOAD_HOSTS = frozenset((
    'api.github.com', 'github.com', 'release-assets.githubusercontent.com',
    'objects.githubusercontent.com', 'github-releases.githubusercontent.com',
))


def release_identity(tag):
    """N'accepte qu'un tag de version explicite, sans chemin ni requete."""
    match = re.fullmatch(r'v?([0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha|beta|rc)\.[0-9]+)?)', tag or '')
    if not match:
        raise ValueError('Tag de release invalide : exemple v0.3.0-beta.1.')
    return 'v' + match[1], match[1]


def _release_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in RELEASE_DOWNLOAD_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError('Destination de telechargement non autorisee.')
    return url


class _ReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, _release_url(newurl))


def _release_read(url, limit):
    """HTTPS verifie, redirections bornees aux hotes GitHub, taille et temps bornes."""
    request = urllib.request.Request(_release_url(url), headers={
        'User-Agent': 'UCHAMBUZI-release-updater',
        'Accept': 'application/vnd.github+json' if urllib.parse.urlsplit(url).hostname == 'api.github.com' else 'application/octet-stream',
    })
    opener = urllib.request.build_opener(_ReleaseRedirect())
    deadline = time.monotonic() + 120
    result = bytearray()
    try:
        with opener.open(request, timeout=30) as response:
            _release_url(response.geturl())
            if response.status != 200:
                raise ValueError('Reponse de telechargement inattendue.')
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdecimal() or int(length) > limit):
                raise ValueError('Artefact de release trop volumineux.')
            while True:
                if time.monotonic() > deadline:
                    raise ValueError('Delai total de telechargement depasse.')
                block = response.read(min(65536, limit - len(result) + 1))
                if not block:
                    break
                result.extend(block)
                if len(result) > limit:
                    raise ValueError('Artefact de release trop volumineux.')
    except urllib.error.URLError as exc:
        raise ValueError('Telechargement GitHub indisponible ; installation conservee.') from exc
    return bytes(result)


def _extract_release(archive, destination, version):
    """Extraction manuelle sans liens, fichiers speciaux, doublons ou traversee."""
    prefix = 'uchambuzi-' + version
    total = 0
    seen = set()
    try:
        # Borner aussi les en-tetes/PAX avant leur analyse par tarfile.
        with gzip.open(archive, 'rb') as compressed:
            unpacked = compressed.read(64 * 1024 * 1024 + 1)
        if len(unpacked) > 64 * 1024 * 1024:
            raise ValueError('Archive decompressee trop volumineuse.')
        with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as tar:
            for index, member in enumerate(tar):
                if index >= 2048:
                    raise ValueError('Archive de release trop complexe.')
                path = PurePosixPath(member.name)
                if (path.is_absolute() or '\\' in member.name or '..' in path.parts
                        or not path.parts or path.parts[0] != prefix
                        or path in seen or not (member.isdir() or member.isfile())):
                    raise ValueError('Entree interdite dans l’archive de release.')
                seen.add(path)
                if member.size < 0 or member.size > 16 * 1024 * 1024:
                    raise ValueError('Fichier de release trop volumineux.')
                total += member.size
                if total > 64 * 1024 * 1024:
                    raise ValueError('Archive decompressee trop volumineuse.')
                target = destination.joinpath(*path.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    content = tar.extractfile(member)
                    if content is None:
                        raise ValueError('Contenu de release absent.')
                    with content, target.open('xb') as output:
                        shutil.copyfileobj(content, output, length=65536)
                    target.chmod(0o700 if target.name == 'install.sh' else 0o600)
    except (tarfile.TarError, gzip.BadGzipFile, EOFError) as exc:
        raise ValueError('Archive de release invalide.') from exc
    root = destination / prefix
    if any(not (root / name).is_file() for name in FOCUS_FINAL_PAYLOAD):
        raise ValueError('Release incomplete : composants Focus manquants.')
    try:
        tree = ast.parse((root / 'src/uchambuzi.py').read_text(encoding='utf-8'))
        declarations = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in ('VERSION', 'REPOSITORY'):
                    declarations[node.targets[0].id] = ast.literal_eval(node.value)
    except (SyntaxError, UnicodeError, ValueError, TypeError) as exc:
        raise ValueError('Identite de la release illisible.') from exc
    if declarations != {'VERSION': version, 'REPOSITORY': RELEASE_REPOSITORY}:
        raise ValueError('Version ou depot de la release incoherent.')
    return root


@contextmanager
def verified_release_source(tag):
    """Recupere uniquement les assets d'une release explicite du depot officiel."""
    tag, version = release_identity(tag)
    archive_name = 'uchambuzi-' + version + '.tar.gz'
    try:
        metadata = json.loads(_release_read(RELEASE_API + tag, 2 * 1024 * 1024))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('Metadonnees GitHub de release invalides ou indisponibles.') from exc
    if (not isinstance(metadata, dict) or metadata.get('tag_name') != tag
            or metadata.get('draft') is not False
            or not isinstance(metadata.get('assets'), list)):
        raise ValueError('Release GitHub non reconnue.')
    assets = {}
    for item in metadata['assets']:
        if isinstance(item, dict) and item.get('name') in (archive_name, 'SHA256SUMS'):
            name = item['name']
            if name in assets or item.get('browser_download_url') != RELEASE_DOWNLOAD + tag + '/' + name:
                raise ValueError('Asset de release ambigu ou depot different.')
            assets[name] = item['browser_download_url']
    if set(assets) != {archive_name, 'SHA256SUMS'}:
        raise ValueError('Archive officielle ou SHA256SUMS absent de la release.')
    try:
        sums = _release_read(assets['SHA256SUMS'], 65536).decode('ascii')
    except UnicodeError as exc:
        raise ValueError('SHA256SUMS illisible.') from exc
    expected = []
    for line in sums.splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64}) [ *]([^\r\n]+)', line)
        if match and match[2] == archive_name:
            expected.append(match[1].lower())
    if len(expected) != 1:
        raise ValueError('Empreinte SHA-256 unique absente pour l’archive.')
    raw = _release_read(assets[archive_name], 32 * 1024 * 1024)
    if checksum(raw) != expected[0]:
        raise ValueError('Empreinte SHA-256 incorrecte ; installation conservee.')
    with tempfile.TemporaryDirectory(prefix='uchambuzi-release-') as tmp:
        directory = Path(tmp)
        archive = directory / archive_name
        archive.write_bytes(raw)
        source = _extract_release(archive, directory / 'source', version)
        yield source, version, tag


@user_files_lock()
def install(source, *, version, repository, branch, source_reference=None, release_tag=None):
    check_system_prerequisites()
    source = Path(source).resolve()
    app, launcher = paths()
    active_payload = resolve_payload(source)
    # Lire toutes les sources avant toute mutation de la destination.
    payload = {}
    for name in active_payload:
        path = source / name
        no_links(path)
        payload[name] = path.read_bytes()
    no_links(app)
    no_links(launcher)
    manifest = app / 'install.json'
    if manifest.exists():
        data = metadata(app)
        if data.get('repository') != repository:
            raise ValueError('Dépôt source différent du dépôt enregistré.')
        verify_owned(app, launcher, data)
        for name in set(active_payload) - data['files'].keys():
            no_links(app / name)
            if (app / name).exists():
                raise ValueError('Nouvelle ressource déjà présente et non gérée : ' + name)
    else:
        # Sans manifeste, aucun fichier existant ne peut être revendiqué par
        # l'installateur, même si ses octets sont identiques à la distribution.
        if launcher.exists():
            raise ValueError('Lanceur préexistant non reconnu ; aucun fichier écrasé.')
        for name in active_payload:
            if (app / name).exists():
                raise ValueError('Conflit avec un fichier applicatif non géré : ' + name)
    # Vérifie également les chemins à créer, notamment les liens de répertoires.
    for target in [app / name for name in active_payload] + [launcher, manifest]:
        no_links(target)
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise ValueError('Conflit avec un répertoire nécessaire : ' + str(parent))
    repo = local_git(source, 'remote', 'get-url', 'origin') or repository
    if repo != repository:
        raise ValueError('Dépôt source différent du dépôt déclaré.')
    data = dict(schema_version=2, created_by='uchambuzi-install', version=version,
                source=str(source_reference or source), repository=repo,
                branch=local_git(source, 'branch', '--show-current') or branch,
                files={name: checksum(content) for name, content in payload.items()},
                launcher_sha256=checksum(wrapper(app)))
    if release_tag is not None:
        data['release_tag'] = release_tag
    residuals = not manifest.exists() and app.is_dir() and any(app.iterdir())
    migrate_user_data()
    files = [(app / name, content, 0o600) for name, content in payload.items()]
    files += [(launcher, wrapper(app), 0o755),
              (manifest, (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode(), 0o600)]
    write_installation(files)
    if residuals:
        print('Fichiers résiduels hors manifeste conservés. '
              'Données historiques copiées et sauvegardées selon les règles de migration.')
    return launcher


def inspect_installation():
    """Vérifie l'état et l'intégrité des fichiers gérés, du lanceur et des données utilisateur."""
    app, launcher = paths()
    manifest = app / 'install.json'
    if not manifest.exists():
        return {'installed': False, 'app_dir': str(app), 'launcher': str(launcher), 'issues': ['Manifeste install.json absent.']}
    issues = []
    try:
        data = metadata(app)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'installed': True, 'app_dir': str(app), 'launcher': str(launcher), 'valid': False, 'issues': [str(exc)]}
    for name, expected in data['files'].items():
        target = app / name
        try:
            no_links(target)
            if not target.is_file():
                issues.append(f'Fichier géré absent : {target}')
            elif checksum(target.read_bytes()) != expected:
                issues.append(f'Fichier géré modifié : {target}')
        except ValueError as exc:
            issues.append(str(exc))
    try:
        no_links(launcher)
        if not launcher.is_file():
            issues.append(f'Lanceur absent : {launcher}')
        elif checksum(launcher.read_bytes()) != data['launcher_sha256']:
            issues.append(f'Lanceur modifié : {launcher}')
    except ValueError as exc:
        issues.append(str(exc))
    return {
        'installed': True,
        'valid': not issues,
        'version': data.get('version'),
        'source': data.get('source'),
        'repository': data.get('repository'),
        'app_dir': str(app),
        'launcher': str(launcher),
        'files_count': len(data['files']),
        'issues': issues,
    }


def _backup_modified_managed_files(app, launcher, data, data_root):
    """Sauvegarde dans uchambuzi-data/repair-backups/ tout fichier géré modifié avant réparation."""
    backup_root = None
    saved = []
    items = [(app / name, name, expected) for name, expected in data['files'].items()]
    items.append((launcher, 'launcher/uchambuzi', data['launcher_sha256']))
    for target, rel_name, expected in items:
        no_links(target)
        if target.exists() and target.is_file():
            raw = target.read_bytes()
            if checksum(raw) != expected:
                if backup_root is None:
                    backup_root = data_root / 'repair-backups'
                    private_directory(backup_root)
                dest = backup_root / f"{rel_name.replace('/', '_')}-{checksum(raw)[:16]}.bak"
                no_links(dest)
                if not dest.exists():
                    atomic_write(dest, raw, 0o600)
                saved.append(str(dest))
    return saved


@user_files_lock()
def repair(source=None, *, version, repository, branch, confirm=None):
    """Répare une installation corrompue ou incomplète en sauvegardant les fichiers modifiés."""
    check_system_prerequisites()
    app, launcher = paths()
    no_links(app)
    no_links(launcher)
    manifest = app / 'install.json'
    data = metadata(app) if manifest.exists() else None
    resolved_source = Path(source or (data['source'] if data else '')).expanduser().resolve()
    if resolved_source == app.resolve():
        raise ValueError('Reparation exige une source independante : utilisez repair --source '
                         'avec une archive officielle verifiee. Aucun telechargement implicite.')
    if not resolved_source.is_dir():
        raise ValueError('Source locale de réparation introuvable : ' + str(resolved_source))
    active_payload = resolve_payload(resolved_source)
    payload = {}
    for name in active_payload:
        path = resolved_source / name
        no_links(path)
        payload[name] = path.read_bytes()
    repo = local_git(resolved_source, 'remote', 'get-url', 'origin') or repository
    if repo != repository or (data and data.get('repository') != repository):
        raise ValueError('Dépôt source différent du dépôt déclaré.')
    if confirm is not None and not confirm():
        return {'repaired': False, 'backups': [], 'launcher': str(launcher)}
    data_root = migrate_user_data()
    backups = _backup_modified_managed_files(app, launcher, data, data_root) if data else []
    new_data = dict(
        schema_version=2,
        created_by='uchambuzi-install',
        version=version,
        source=str(resolved_source),
        repository=repo,
        branch=local_git(resolved_source, 'branch', '--show-current') or branch,
        files={name: checksum(content) for name, content in payload.items()},
        launcher_sha256=checksum(wrapper(app)),
    )
    files = [(app / name, content, 0o600) for name, content in payload.items()]
    files += [
        (launcher, wrapper(app), 0o755),
        (manifest, (json.dumps(new_data, indent=2, ensure_ascii=False) + '\n').encode(), 0o600),
    ]
    write_installation(files)
    return {'repaired': True, 'backups': backups, 'launcher': str(launcher), 'data_path': str(data_root)}


KNOWN_USER_DATA_DIRS = (
    'config', 'cases', 'sessions', 'audit', 'exports', 'methods', 'corpus-staging',
    'legacy-config', 'legacy-app', 'migration-backups',
    'update-backups', 'repair-backups', 'logs', 'cache',
)


def _remove_controlled_user_data(root):
    """Supprime de manière contrôlée le répertoire uchambuzi-data après vérification des sous-éléments."""
    no_links(root)
    if not root.exists():
        return False
    if root.name != 'uchambuzi-data':
        raise ValueError('Répertoire de données non reconnu pour la suppression : ' + str(root))
    for item in root.iterdir():
        no_links(item)
        if item.name not in KNOWN_USER_DATA_DIRS:
            raise ValueError('Élément inconnu dans uchambuzi-data ; suppression refusée : ' + str(item))
    for item in sorted(root.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        no_links(item)
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            item.rmdir()
    root.rmdir()
    return True


def inspect_local_ai_environment():
    """Examine les composants IA locaux (Ollama, service, modèles) et leurs impacts partagés."""
    home = Path.home()
    env_bin = os.environ.get('UCHAMBUZI_OLLAMA_BIN')
    ollama_bin = Path(env_bin) if env_bin else (
        Path(shutil.which('ollama')) if shutil.which('ollama') else None
    )
    user_ollama_bins = [
        p for p in (home / '.local/bin/ollama', home / 'bin/ollama')
        if p.exists() or p.is_symlink()
    ]
    ollama_dir = Path(os.environ.get('OLLAMA_MODELS', str(home / '.ollama')))
    models_present = []
    manifests_root = (ollama_dir if os.environ.get('OLLAMA_MODELS') else ollama_dir / 'models') / 'manifests'
    if manifests_root.is_dir():
        for p in sorted(manifests_root.rglob('*')):
            if p.is_file():
                rel = p.relative_to(manifests_root).as_posix()
                parts = rel.split('/')
                if len(parts) >= 2:
                    models_present.append(f'{parts[-2]}:{parts[-1]}')
    return {
        'ollama_binary': str(ollama_bin) if ollama_bin and ollama_bin.exists() else None,
        'user_ollama_binaries': [str(p) for p in user_ollama_bins],
        'ollama_data_dir': str(ollama_dir),
        'ollama_data_exists': ollama_dir.exists(),
        'detected_models': models_present,
        'shared_component_warning': (
            'Ollama et ses modèles peuvent être partagés avec d’autres outils du système. '
            'Une désinstallation ordinaire d’UCHAMBUZI les conserve intégralement.'
        ),
    }


def _validate_ollama_purge_path():
    """Ne jamais traiter un dossier arbitraire comme le stockage d'Ollama."""
    home = Path.home()
    target = Path(os.environ.get('OLLAMA_MODELS', str(home / '.ollama')))
    no_links(target)
    if not target.is_absolute() or target not in (home / '.ollama', home / '.ollama/models'):
        raise ValueError('Purge Ollama refusée pour un stockage personnalisé : ' + str(target)
                         + '. Retirez les modèles explicitement avec --remove-model.')
    return target


def _uninstall_local_ai(*, purge_ollama=False, remove_models=()):
    """Retire les modèles sélectionnés et, si expressément demandé, désinstalle Ollama."""
    report = {'models_removed': [], 'ollama_removed': False, 'actions': [], 'warnings': []}
    info = inspect_local_ai_environment()
    if purge_ollama:
        _validate_ollama_purge_path()
    ollama_bin = info['ollama_binary']
    for model_name in remove_models:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', model_name):
            raise ValueError('Nom de modèle invalide pour le retrait : ' + str(model_name))
        if ollama_bin:
            res = subprocess.run([ollama_bin, 'rm', model_name], capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                report['models_removed'].append(model_name)
                report['actions'].append(f'ollama rm {model_name}')
            else:
                report['warnings'].append(f"Échec de 'ollama rm {model_name}' : {(res.stderr or res.stdout).strip()}")
        else:
            report['warnings'].append(f"Exécutable ollama absent pour retirer le modèle {model_name}.")
    if purge_ollama:
        # 1. Arrêt ou retrait non fatal d'un éventuel service utilisateur systemd
        systemctl = shutil.which('systemctl')
        if systemctl and not os.environ.get('UCHAMBUZI_SKIP_SYSTEMCTL'):
            for cmd in ([systemctl, '--user', 'stop', 'ollama'], [systemctl, '--user', 'disable', 'ollama']):
                try:
                    subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        unit_file = Path.home() / '.config/systemd/user/ollama.service'
        if unit_file.is_file() and not unit_file.is_symlink():
            unit_file.unlink()
            report['actions'].append(f'Retrait unité utilisateur : {unit_file}')
        # 2. Retrait des binaires Ollama situés dans l'espace de l'utilisateur
        removed_any = False
        candidates = [Path(p) for p in info['user_ollama_binaries']]
        if ollama_bin:
            bin_path = Path(ollama_bin)
            if bin_path not in candidates:
                candidates.append(bin_path)
        for bin_path in candidates:
            try:
                no_links(bin_path)
            except ValueError:
                continue
            if bin_path.is_file():
                try:
                    bin_path.unlink()
                    report['actions'].append(f'Retrait binaire Ollama : {bin_path}')
                    removed_any = True
                except PermissionError:
                    report['warnings'].append(
                        f'Droits administrateur requis pour retirer le binaire système {bin_path} '
                        '(ex. sudo rm -f /usr/local/bin/ollama ou sudo apt purge ollama).'
                    )
        # 3. Retrait contrôlé du dossier de données Ollama (~/.ollama ou OLLAMA_MODELS dans HOME)
        ollama_dir = Path(info['ollama_data_dir'])
        no_links(ollama_dir)
        if ollama_dir.exists():
            for item in sorted(ollama_dir.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                no_links(item)
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    item.rmdir()
            ollama_dir.rmdir()
            report['actions'].append(f'Retrait répertoire Ollama : {ollama_dir}')
            removed_any = True
        report['ollama_removed'] = removed_any
    return report


@user_files_lock()
def uninstall(*, confirm, purge_data=False, purge_ai=False, remove_models=()):
    app, launcher = paths()
    data = metadata(app)
    verify_owned(app, launcher, data)
    if purge_ai:
        _validate_ollama_purge_path()
    data_root = user_data_path()
    if purge_data and data_root.exists():
        no_links(data_root)
        if data_root.name != 'uchambuzi-data':
            raise ValueError('Répertoire de données non reconnu pour la suppression : ' + str(data_root))
        for item in data_root.iterdir():
            no_links(item)
            if item.name not in KNOWN_USER_DATA_DIRS:
                raise ValueError('Élément inconnu dans uchambuzi-data ; suppression refusée : ' + str(item))
    if not confirm():
        return False
    for name in data['files']:
        (app / name).unlink(missing_ok=True)
    launcher.unlink(missing_ok=True)
    (app / 'install.json').unlink()
    # Ne retire que les répertoires vides de la liste connue; extras/données conservés.
    directories = {
        parent
        for name in set(FOCUS_COMPLETE_PAYLOAD) | set(PAYLOAD) | set(data['files'])
        for parent in (app / name).parents
        if parent.is_relative_to(app)
    }
    for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            pass
    if purge_data:
        _remove_controlled_user_data(data_root)
    if purge_ai or remove_models:
        _uninstall_local_ai(purge_ollama=purge_ai, remove_models=remove_models)
    return True


FORBIDDEN_PRIVATE_FILES = (
    'AGENTS.md', 'MANDAT.md', 'DECISIONS.md', 'PILOTAGE.md', 'PROMPTS-AGENTS.md',
    'CONTINUITE.md', 'CONTRIBUTING.md.local',
)


def build_deb_package(source, output_dir, *, version='2.0.0-1'):
    """Construit un paquet Debian natif (.deb) pour Kali Linux sans aucun document interne."""
    import gzip
    source = Path(source).resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    no_links(source)
    no_links(output_dir)
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+~:-]{0,63}', version):
        raise ValueError('Version Debian invalide.')
    active_payload = tuple(dict.fromkeys(resolve_payload(source) + debian_vendor_payload(source)))
    payload_bytes = {}
    for name in active_payload:
        src_file = source / name
        no_links(src_file)
        if not src_file.is_file():
            raise ValueError('Ressource manquante pour le paquet Debian : ' + name)
        payload_bytes[name] = src_file.read_bytes()
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    deb_path = output_dir / f'uchambuzi_{version}_amd64.deb'
    no_links(deb_path)
    with tempfile.TemporaryDirectory(prefix='uchambuzi-deb-') as tmp:
        stage = Path(tmp) / 'pkg'
        debian_dir = stage / 'DEBIAN'
        share_app = stage / 'usr/share/uchambuzi'
        bin_dir = stage / 'usr/bin'
        doc_dir = share_app / 'debian'
        for d in (debian_dir, share_app, bin_dir, doc_dir):
            d.mkdir(parents=True, exist_ok=True, mode=0o755)
        for name, content in payload_bytes.items():
            target = share_app / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.write_bytes(content)
            target.chmod(0o755 if name == 'src/uchambuzi.py' or '/bin/' in name and name.startswith('vendor/') else 0o644)
        launcher = bin_dir / 'uchambuzi'
        launcher.write_bytes(b'#!/bin/sh\nexec python3 /usr/share/uchambuzi/src/uchambuzi.py "$@"\n')
        launcher.chmod(0o755)
        copyright_src = source / 'debian/copyright'
        copyright_text = (copyright_src.read_bytes() if copyright_src.is_file() else (
            b'Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/\n'
            b'Upstream-Name: uchambuzi\n'
            b'Source: https://github.com/wkd0/UCHAMBUZI\n\n'
            b'Files: *\n'
            b'Copyright: 2026 Wakanda (WKD) et contributeurs respectifs\n'
            b'License: GPL-3.0+\n'
        ))
        (doc_dir / 'copyright').write_bytes(copyright_text)
        (doc_dir / 'copyright').chmod(0o644)
        changelog_src = source / 'debian/changelog'
        changelog_bytes = (changelog_src.read_bytes() if changelog_src.is_file() else (
            f'uchambuzi ({version}) kali-rolling; urgency=medium\n\n'
            f'  * Packaging natif Kali Linux et gestion des dossiers d\'enquete.\n\n'
            f' -- Wakanda (WKD) <wkd@uchambuzi.local>  Sun, 08 Nov 2026 10:30:00 +0100\n'
        ).encode('utf-8'))
        with (doc_dir / 'changelog.Debian.gz').open('wb') as raw_gz:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw_gz, mtime=0) as gz:
                gz.write(changelog_bytes)
        (doc_dir / 'changelog.Debian.gz').chmod(0o644)
        installed_files = sorted(p for p in (stage / 'usr').rglob('*') if p.is_file())
        for p in stage.rglob('*'):
            if p.name in FORBIDDEN_PRIVATE_FILES or p.name.endswith('.local') or '.local.' in p.name:
                raise ValueError('Document interne interdit détecté dans le paquet : ' + p.name)
            if p.is_dir():
                p.chmod(0o755)
        installed_kb = max(1, (sum(p.stat().st_size for p in installed_files) + 1023) // 1024)
        control_content = (
            f'Package: uchambuzi\n'
            f'Version: {version}\n'
            f'Section: utils\n'
            f'Priority: optional\n'
            f'Architecture: amd64\n'
            f'Installed-Size: {installed_kb}\n'
            f'Depends: python3 (>= 3.10), python3.13, python3.13-venv, tzdata, python3-rich, python3-prompt-toolkit, python3-textual, libc6 (>= 2.34)\n'
            f'Recommends: bind9-dnsutils, file, libimage-exiftool-perl, binutils, whois, tshark, curl, subfinder, httpx-toolkit, dnsx, gitleaks, photon, trufflehog, mat2, sherlock, spiderfoot, theharvester, amass\n'
            f'Maintainer: Wakanda (WKD) <wkd@uchambuzi.local>\n'
            f'Homepage: https://github.com/wkd0/UCHAMBUZI\n'
            f'Description: Assistant IA local pour l\'investigation numerique sous Kali Linux\n'
            f' UCHAMBUZI accompagne les enqueteurs numeriques et analystes en cybersecurite\n'
            f' dans la decouverte, la verification locale de version et la preparation bornee\n'
            f' de commandes d\'investigation sans aucune execution automatique.\n'
        )
        (debian_dir / 'control').write_text(control_content, encoding='utf-8')
        (debian_dir / 'control').chmod(0o644)
        md5_lines = [
            f"{hashlib.md5(p.read_bytes()).hexdigest()}  {p.relative_to(stage).as_posix()}\n"
            for p in installed_files
        ]
        (debian_dir / 'md5sums').write_text(''.join(md5_lines), encoding='utf-8')
        (debian_dir / 'md5sums').chmod(0o644)
        postinst = (
            '#!/bin/sh\nset -e\n'
            'if [ "$1" = "configure" ] && ! command -v python3 >/dev/null 2>&1; then\n'
            '    echo "uchambuzi: python3 requis." >&2\n'
            '    exit 1\n'
            'fi\nexit 0\n'
        )
        prerm = (
            '#!/bin/sh\nset -e\n'
            '# Les donnees utilisateur (~/Documents/uchambuzi-data) et moteurs IA locaux sont preserves.\n'
            'exit 0\n'
        )
        for script_name, script_body in (('postinst', postinst), ('prerm', prerm)):
            script_path = debian_dir / script_name
            script_path.write_text(script_body, encoding='utf-8')
            script_path.chmod(0o755)
        result = subprocess.run(
            ['dpkg-deb', '-Zgzip', '--build', '--root-owner-group', str(stage), str(deb_path)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise OSError('Échec de construction dpkg-deb : ' + (result.stderr or result.stdout).strip())
    return deb_path
