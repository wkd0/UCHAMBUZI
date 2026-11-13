# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : tools_catalog.py
# Role          : Catalogue OSINT strict, inventaire local et rendu Rich
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Definitions declaratives : aucune installation et aucune commande externe."""
from pathlib import Path
import json
import re
import shutil
from dataclasses import dataclass
from focus_tool_registry import ToolRegistry
from focus_tool_process import run

SPECIALTIES = frozenset(('domain', 'infra', 'person', 'social', 'media', 'leaks', 'web_archive'))
INPUT_TYPES = frozenset(('ip', 'domain', 'url', 'email', 'username', 'phone', 'image', 'file', 'hash'))
CATALOG_PATH = Path(__file__).resolve().parent.parent / 'data/tools/catalog.json'
FIELDS = frozenset(('id', 'name', 'team', 'specialties', 'source', 'executable', 'version_cmd',
    'version_pin', 'input_types', 'activity', 'needs_network', 'license', 'upstream_url', 'artifact', 'notes'))
TRUSTED = {'whatsmyname': {'executable': 'whatsmyname', 'source': 'builtin',
    'upstream_url': 'https://github.com/WebBreacher/WhatsMyName', 'version_cmd': [],
    'license': 'GPL-3.0-or-later AND CC-BY-SA-4.0', 'activity': 'active', 'needs_network': True},
'blackbird': {'executable': 'blackbird', 'source': 'vendored', 'upstream_url': 'https://github.com/p1ngul1n0/blackbird', 'version_cmd': ['--help'], 'license': 'GPL-3.0', 'activity': 'active', 'needs_network': True},
'whois': {'executable': 'whois',
           'source': 'kali',
           'upstream_url': 'https://www.kali.org/tools/whois/',
           'version_cmd': ['--version'],
           'license': 'GPL-2.0-or-later',
           'activity': 'passive',
           'needs_network': True},
 'dig': {'executable': 'dig',
         'source': 'kali',
         'upstream_url': 'https://www.kali.org/tools/bind9/',
         'version_cmd': ['-v'],
         'license': 'MPL-2.0',
         'activity': 'passive',
         'needs_network': True},
 'dnsrecon': {'executable': 'dnsrecon',
              'source': 'kali',
              'upstream_url': 'https://www.kali.org/tools/dnsrecon/',
              'version_cmd': [],
              'license': 'GPL-2.0-only',
              'activity': 'active',
              'needs_network': True},
 'dnsenum': {'executable': 'dnsenum',
             'source': 'kali',
             'upstream_url': 'https://www.kali.org/tools/dnsenum/',
             'version_cmd': [],
             'license': 'GPL-2.0-only',
             'activity': 'active',
             'needs_network': True},
 'amass': {'executable': 'amass',
           'source': 'kali',
           'upstream_url': 'https://www.kali.org/tools/amass/',
           'version_cmd': [],
           'license': 'Apache-2.0',
           'activity': 'active',
           'needs_network': True},
 'sublist3r': {'executable': 'sublist3r',
               'source': 'kali',
               'upstream_url': 'https://www.kali.org/tools/sublist3r/',
               'version_cmd': [],
               'license': 'GPL-2.0-only',
               'activity': 'active',
               'needs_network': True},
 'fierce': {'executable': 'fierce',
            'source': 'kali',
            'upstream_url': 'https://www.kali.org/tools/fierce/',
            'version_cmd': [],
            'license': 'GPL-3.0-only',
            'activity': 'active',
            'needs_network': True},
 'theharvester': {'executable': 'theHarvester',
                  'source': 'kali',
                  'upstream_url': 'https://www.kali.org/tools/theharvester/',
                  'version_cmd': [],
                  'license': 'GPL-2.0-only',
                  'activity': 'active',
                  'needs_network': True},
 'dmitry': {'executable': 'dmitry',
            'source': 'kali',
            'upstream_url': 'https://www.kali.org/tools/dmitry/',
            'version_cmd': [],
            'license': 'GPL-2.0-only',
            'activity': 'active',
            'needs_network': True},
 'whatweb': {'executable': 'whatweb',
             'source': 'kali',
             'upstream_url': 'https://www.kali.org/tools/whatweb/',
             'version_cmd': [],
             'license': 'GPL-2.0-or-later',
             'activity': 'active',
             'needs_network': True},
 'wafw00f': {'executable': 'wafw00f',
             'source': 'kali',
             'upstream_url': 'https://www.kali.org/tools/wafw00f/',
             'version_cmd': [],
             'license': 'BSD-3-Clause',
             'activity': 'active',
             'needs_network': True},
 'sherlock': {'executable': 'sherlock',
              'source': 'kali',
              'upstream_url': 'https://www.kali.org/tools/sherlock/',
              'version_cmd': [],
              'license': 'MIT',
              'activity': 'active',
              'needs_network': True},
 'spiderfoot': {'executable': 'spiderfoot',
                'source': 'kali',
                'upstream_url': 'https://www.kali.org/tools/spiderfoot/',
                'version_cmd': [],
                'license': 'MIT',
                'activity': 'active',
                'needs_network': True},
 'recon-ng': {'executable': 'recon-ng',
              'source': 'kali',
              'upstream_url': 'https://www.kali.org/tools/recon-ng/',
              'version_cmd': [],
              'license': 'GPL-3.0-only',
              'activity': 'active',
              'needs_network': True},
 'exiftool': {'executable': 'exiftool',
              'source': 'kali',
              'upstream_url': 'https://www.kali.org/tools/exiftool/',
              'version_cmd': ['-ver'],
              'license': 'Artistic-1.0-Perl OR GPL-1.0-or-later',
              'activity': 'passive',
              'needs_network': False},
 'mat2': {'executable': 'mat2',
          'source': 'kali',
          'upstream_url': 'https://www.kali.org/tools/mat2/',
          'version_cmd': [],
          'license': 'LGPL-3.0-or-later',
          'activity': 'passive',
          'needs_network': False},
 'foremost': {'executable': 'foremost',
              'source': 'kali',
              'upstream_url': 'https://www.kali.org/tools/foremost/',
              'version_cmd': [],
              'license': 'Public-domain',
              'activity': 'passive',
              'needs_network': False},
 'binwalk': {'executable': 'binwalk',
             'source': 'kali',
             'upstream_url': 'https://www.kali.org/tools/binwalk/',
             'version_cmd': ['--help'],
             'license': 'MIT',
             'activity': 'passive',
             'needs_network': False},
 'strings': {'executable': 'strings',
             'source': 'kali',
             'upstream_url': 'https://www.kali.org/tools/binutils/',
             'version_cmd': ['--version'],
             'license': 'GPL-3.0-or-later',
             'activity': 'passive',
             'needs_network': False},
 'metagoofil': {'executable': 'metagoofil',
                'source': 'kali',
                'upstream_url': 'https://www.kali.org/tools/metagoofil/',
                'version_cmd': [],
                'license': 'GPL-2.0-only',
                'activity': 'active',
                'needs_network': True},
 'curl': {'executable': 'curl',
          'source': 'kali',
          'upstream_url': 'https://www.kali.org/tools/curl/',
          'version_cmd': [],
          'license': 'curl',
          'activity': 'active',
          'needs_network': True},
 'nmap': {'executable': 'nmap',
          'source': 'kali',
          'upstream_url': 'https://www.kali.org/tools/nmap/',
          'version_cmd': ['--version'],
          'license': 'NPSL-0.94',
          'activity': 'active',
          'needs_network': True},
 'maigret': {'executable': 'maigret',
             'source': 'vendored',
             'upstream_url': 'https://github.com/soxoj/maigret',
             'version_cmd': [],
             'license': 'MIT',
             'activity': 'active',
             'needs_network': True},
 'holehe': {'executable': 'holehe',
            'source': 'vendored',
            'upstream_url': 'https://github.com/megadose/holehe',
            'version_cmd': [],
            'license': 'GPL-3.0',
            'activity': 'active',
            'needs_network': True},
 'phoneinfoga': {'executable': 'phoneinfoga',
                 'source': 'vendored',
                 'upstream_url': 'https://github.com/sundowndev/phoneinfoga',
                 'version_cmd': [],
                 'license': 'GPL-3.0',
                 'activity': 'active',
                 'needs_network': True},
 'subfinder': {'executable': 'subfinder',
               'source': 'vendored',
               'upstream_url': 'https://github.com/projectdiscovery/subfinder',
               'version_cmd': [],
               'license': 'MIT',
               'activity': 'passive',
               'needs_network': True},
 'httpx': {'executable': 'httpx',
           'source': 'vendored',
           'upstream_url': 'https://github.com/projectdiscovery/httpx',
           'version_cmd': [],
           'license': 'MIT',
           'activity': 'active',
           'needs_network': True},
 'dnsx': {'executable': 'dnsx',
          'source': 'vendored',
          'upstream_url': 'https://github.com/projectdiscovery/dnsx',
          'version_cmd': [],
          'license': 'MIT',
          'activity': 'active',
          'needs_network': True},
 'gau': {'executable': 'gau',
         'source': 'vendored',
         'upstream_url': 'https://github.com/lc/gau',
         'version_cmd': [],
         'license': 'MIT',
         'activity': 'passive',
         'needs_network': True},
 'photon': {'executable': 'photon',
            'source': 'vendored',
            'upstream_url': 'https://github.com/s0md3v/Photon',
            'version_cmd': [],
            'license': 'GPL-3.0',
            'activity': 'active',
            'needs_network': True},
 'trufflehog': {'executable': 'trufflehog',
                'source': 'vendored',
                'upstream_url': 'https://github.com/trufflesecurity/trufflehog',
                'version_cmd': [],
                'license': 'AGPL-3.0',
                'activity': 'active',
                'needs_network': True},
 'gitleaks': {'executable': 'gitleaks',
              'source': 'vendored',
              'upstream_url': 'https://github.com/gitleaks/gitleaks',
              'version_cmd': [],
              'license': 'MIT',
              'activity': 'passive',
              'needs_network': False},
 'social-analyzer': {'executable': 'social-analyzer',
                     'source': 'vendored',
                     'upstream_url': 'https://github.com/qeeqbox/social-analyzer',
                     'version_cmd': [],
                     'license': 'AGPL-3.0',
                     'activity': 'active',
                     'needs_network': True}}


def _reject(message):
    raise ValueError('Catalogue invalide : ' + message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject('champ duplique')
        result[key] = value
    return result


def validate_catalog(document):
    """Valide sans effet de bord ; les ancrages executables restent dans le code."""
    if type(document) is not dict or set(document) != {'schema_version', 'tools'}:
        _reject('champs racine')
    if type(document['schema_version']) is not int or document['schema_version'] != 1:
        _reject('schema_version')
    rows = document['tools']
    if type(rows) is not list or not 0 < len(rows) <= 64:
        _reject('liste outils')
    seen = set()
    for row in rows:
        if type(row) is not dict or set(row) != FIELDS:
            _reject('champs outil inconnus ou manquants (cles API interdites)')
        key = row['id']
        if type(key) is not str or key not in TRUSTED or key in seen:
            _reject('identifiant non autorise ou duplique')
        seen.add(key)
        for field, expected in TRUSTED[key].items():
            if row[field] != expected or type(row[field]) is not type(expected):
                _reject('ancrage ' + field)
        if type(row['team']) is not str or type(row['activity']) is not str or row['team'] != 'osint' or row['activity'] not in ('passive', 'active'):
            _reject('team/activite')
        if type(row['needs_network']) is not bool:
            _reject('reseau')
        for field, choices in (('specialties', SPECIALTIES), ('input_types', INPUT_TYPES)):
            values = row[field]
            if (type(values) is not list or not values or
                any(type(v) is not str or v not in choices for v in values) or len(set(values)) != len(values)):
                _reject(field)
        for field in ('name', 'license', 'notes'):
            value = row[field]
            if type(value) is not str or not value or len(value) > 2048 or any(ord(c) < 32 or ord(c) == 127 for c in value):
                _reject(field)
        pin = row['version_pin']
        if pin is not None and (type(pin) is not str or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.+:~_-]{0,127}', pin)):
            _reject('version_pin')
        artifact = row['artifact']
        if artifact is not None:
            if (row['source'] != 'vendored' or type(artifact) is not dict or
                set(artifact) != {'file', 'sha256', 'install'} or pin is None or row['license'] == 'NOASSERTION'):
                _reject('artefact')
            if (type(artifact['file']) is not str or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,191}', artifact['file']) or
                '..' in artifact['file'] or type(artifact['sha256']) is not str or
                not re.fullmatch(r'[0-9a-f]{64}', artifact['sha256']) or
                type(artifact['install']) is not str or artifact['install'] not in ('pipx', 'binary', 'apt', 'venv')):
                _reject('artefact non borne')
    return tuple(rows)


def load_catalog(path=CATALOG_PATH):
    raw = Path(path).read_bytes()
    if len(raw) > 262144:
        _reject('taille')
    return validate_catalog(json.loads(raw, object_pairs_hook=_unique_object))


@dataclass(frozen=True)
class ToolState:
    state: str
    version: str | None = None
    diagnostic: str = ''


def discover_tools(tools, *, path=None):
    """Presence PATH et sondes historiques bornees ; jamais version_cmd du JSON."""
    tools = validate_catalog({'schema_version': 1, 'tools': list(tools)})
    registry = ToolRegistry()
    wanted = {row['executable'] for row in tools if row['source'] == 'kali'}
    registry.descriptions = {k: v for k, v in registry.descriptions.items() if k in wanted}
    # Explicit PATH override is discovery only, never executed (test or external PATH).
    system_path = '/usr/bin:/bin'
    inventory = registry.discover(search_path=system_path) if path is None else {}
    states = {}
    for row in tools:
        key, name = row['id'], row['executable']
        present = shutil.which(name, path=system_path if path is None else path)
        if row['source'] == 'builtin':
            states[key] = ToolState('installed', diagnostic='Moteur Python natif ; dataset local.')
        elif row['source'] == 'vendored':
            from tools_installer import ToolsInstaller
            installer = ToolsInstaller(tools)
            verified = row['artifact'] is not None and installer.executable(key) is not None
            diagnostic = ('Copie UCHAMBUZI vérifiée.' if verified else
                          'Copie UCHAMBUZI non verifiee ; aucun binaire PATH execute.')
            if row['artifact'] is None:
                diagnostic = 'Aucun artefact vérifié distribué ; installation et exécution indisponibles.'
                if row['license'] == 'NOASSERTION':
                    diagnostic += ' Licence amont non déclarée.'
            states[key] = ToolState('installed' if verified else 'unverified',
                row['version_pin'] if verified else None,
                diagnostic)
        elif not present:
            states[key] = ToolState('available', diagnostic='Paquet Kali disponible ; non installe.')
        else:
            probe = inventory.get(name)
            missing = bool(probe and probe.probe_status == 'spawn_error')
            diagnostic = ('Binaire présent ; moteur et base non vérifiés. Pour Amass v5, '
                          'enum -h peut démarrer le moteur et attendre le réseau. '
                          'Consulter la fiche Amass et docs/amass-v5.md.' if key == 'amass' else '')
            # A script can exist while its interpreter has been removed.
            try:
                with open(present, 'rb') as script:
                    prefix = script.read(4096)
                    header = prefix.split(b'\n', 1)[0]
                if header.startswith(b'#!'):
                    interpreter = header[2:].strip().split()[0].decode('utf-8')
                    missing = missing or not Path(interpreter).is_file()
                # Kali's Amass wrapper downloads data before handling even --help.
                # Recognize that wrapper without executing its downloader or sudo.
                if (key == 'amass' and b'libpostal_data' in prefix
                        and b'/usr/share/libpostal/transliteration' in prefix
                        and not Path('/usr/share/libpostal/transliteration').exists()):
                    missing = True
                    diagnostic = ('Données libpostal absentes ; le lanceur Kali demande un téléchargement '
                                  'amont avec privilèges. Aucun téléchargement automatique par UCHAMBUZI.')
            except (OSError, UnicodeError, IndexError):
                missing = True
            version = probe.version if probe else None
            if version is None and path is None:
                # Fixed local package query, independent of catalogue strings.
                package = {'dig': 'bind9-dnsutils', 'exiftool': 'libimage-exiftool-perl',
                           'strings': 'binutils', 'theHarvester': 'theharvester'}.get(name, name)
                dpkg = shutil.which('dpkg-query', path='/usr/bin:/bin')
                if dpkg:
                    result = run(dpkg, ('-W', '-f=${Version}', package), timeout=.7, output_limit=4096)
                    value = result.stdout.decode('utf-8', 'replace').strip()
                    if result.status == 'succeeded' and re.fullmatch(r'[a-zA-Z0-9.+:~_-]{1,128}', value):
                        version = value + ' (paquet)'
            states[key] = ToolState('missing_dependency' if missing else 'installed',
                version, diagnostic or ('Interpréteur ou dépendance locale manquant.' if missing else
                                       'Version non verifiee' if version is None else ''))
    return states


LABELS = {'installed': '✅ installe', 'available': '⬜ disponible',
          'missing_dependency': '⚠️ dependance manquante', 'unverified': '? non verifie'}


def render_tools(console, query='', *, tools=None, states=None):
    """Table responsive ou detail ; texte externe sans interpretation de balises."""
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from tool_guidance import integration_for
    rows = load_catalog() if tools is None else validate_catalog({'schema_version': 1, 'tools': list(tools)})
    query = query.strip().casefold()
    if query in ('list', 'all'):
        query = ''
    detail = next((r for r in rows if query in (r['id'], r['name'].casefold())), None) if query else None
    if query and not detail and query not in SPECIALTIES:
        console.print('Usage : /tools [domain|infra|person|social|media|leaks|web_archive|nom]', markup=False)
        return
    selected = [detail] if detail else [r for r in rows if not query or query in r['specialties']]
    states = discover_tools(selected) if states is None else states
    table = Table(title='OSINT Team — outils', box=box.ROUNDED, expand=True)
    for name in ('Nom', 'Specialite', 'Activite', 'Etat', 'Intégration'):
        table.add_column(name, overflow='fold', min_width=15 if name == 'Nom' else None)
    for row in selected:
        table.add_row(*(Text(x) for x in (row['name'], ', '.join(row['specialties']),
            'actif' if row['activity'] == 'active' else 'passif', '[À venir]' if row['source'] == 'vendored' and not row['artifact'] else LABELS[states[row['id']].state],
            integration_for(row['id'])['label'])))
    console.print(table)
    console.print('Préparer les copies embarquées : /tools setup · Détail : /tools <nom>', markup=False)
    console.print('Les slash pilotent UCHAMBUZI ; ! commande et /terminal donnent accès à Bash libre.', markup=False)
    if detail:
        from tool_guidance import guide_for
        guide = guide_for(detail['id'])
        integration = integration_for(detail['id'])
        console.print('Intégration : ' + integration['label'] + ' · ' + integration['detail'], markup=False)
        console.print('Parcours disponibles : ' + (' · '.join(integration['routes']) or 'aucun'), markup=False)
        for label, key in (('À quoi sert cet outil', 'purpose'), ('Pourquoi le choisir', 'why'),
                           ('Indice attendu', 'input_label'), ('Résultats attendus', 'outputs'),
                           ('Limites', 'limits'), ('Exemple natif', 'example')):
            console.print(label+' : '+guide[key], markup=False, highlight=False)
        if guide['guided']:
            console.print('Parcours accompagné : /tools run '+detail['id']+' <indice> (approbation avant exécution)', markup=False)
        else:
            console.print('Pas de préparation individuelle depuis cette fiche ; consulter les parcours indiqués dans l’aide.', markup=False)
        if detail.get('artifact'):

            console.print('Installer : /tools install '+detail['id']+' · Vérifier : /tools verify '+detail['id'], markup=False)
        elif detail['source'] == 'vendored':
            console.print('Indisponible : aucun artefact vérifié embarqué pour cette entrée.', markup=False)
        else:
            console.print('Outil système Kali ; la présence locale ne garantit pas une intégration de toutes ses options.', markup=False)
        state = states[detail['id']]
        for label, value in (('Source', detail['source']), ('Licence', detail['license']),
            ('Version detectee', state.version or 'non verifiee'), ('Version figee', detail['version_pin'] or 'non definie'),
            ('Reseau', 'oui' if detail['needs_network'] else 'non'), ('Amont (information)', detail['upstream_url']),
            ('Notes', detail['notes']), ('Diagnostic', state.diagnostic)):
            console.print(label + ' : ' + str(value), markup=False, highlight=False)
    console.print('Aucune installation ni investigation. Les outils mixtes sont classes actifs par precaution.', markup=False)


def handle_tools(console, argument=''):
    """Point de raccordement pour le REPL, conserve les erreurs dans le terminal."""
    try:
        if argument.strip() == 'setup':
            from tools_installer import ToolsInstaller
            from repl_approval import ask_approval
            return ToolsInstaller(load_catalog(),
                case_manager=getattr(console, '_uchambuzi_case_manager', None),
                confirm=ask_approval,
                output=lambda message: console.print(message, markup=False)).setup()
        render_tools(console, argument)
    except (ValueError, OSError) as exc:
        console.print('Catalogue indisponible : ' + str(exc), markup=False)


if __name__ == "__main__":
    import sys
    from rich.console import Console
    handle_tools(Console(), " ".join(sys.argv[1:]))
