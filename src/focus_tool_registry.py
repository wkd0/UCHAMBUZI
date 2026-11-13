# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_tool_registry.py
# Role          : Catalogue descriptif et decouverte locale
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Les extensions sont descriptives ; seules les sondes integrees sont executables."""
from dataclasses import dataclass, replace
import os
import json
from pathlib import Path
import re
import shutil
import time
from focus_tool_process import run

@dataclass(frozen=True)
class ToolDescription:
    id: str
    categories: tuple[str, ...]
    capabilities: tuple[str, ...]
    limits: str
    prerequisites: str = 'Acces utilisateur et autorisation sur la ressource.'

@dataclass(frozen=True)
class InstalledTool:
    id: str
    executable: str | None
    version: str | None
    version_status: str
    verified_capabilities: tuple[str, ...] = ()
    help_options: tuple[str, ...] = ()
    identity: tuple = ()
    probe_status: str = 'unprobed'
    probe_returncode: int | None = None
    probe_diagnostic: str | None = None

# No executable/probe/format string accepted from external definitions.
_DATA = (
 ('ip', ('network_administration','network_discovery'), ('interfaces',), 'Etat local uniquement.'),
 ('ss', ('network_monitoring','system_diagnostics'), ('sockets',), 'Visibilite limitee aux droits utilisateur.'),
 ('dig', ('passive_dns',), ('dns',), 'Interroge un resolveur ; ne prouve pas la propriete.'),
 ('whois', ('whois_lookup','osint_reconnaissance'), ('registration',), 'Donnees parfois masquees, limites de requetes.'),
 ('nmap', ('port_scanning','service_enumeration'), ('ports',), 'Scan actif detectable ; autorisation du proprietaire requise.'),
 ('exiftool', ('metadata_extraction',), ('metadata',), 'Metadonnees declaratives, pas preuve de provenance.'),
 ('tshark', ('network_monitoring','telemetry_validation'), ('pcap',), 'Lecture de capture seulement ; aucune capture vive.'),
 ('file', ('disk_forensics','malware_triage'), ('identify',), 'Identification heuristique.'),
 ('sha256sum', ('disk_forensics',), ('hash',), 'Empreinte sans signature ni chaine de conservation.'),
 ('strings', ('malware_triage',), ('strings',), 'Chaines imprimables sans interpretation semantique.'),
 ('binwalk', ('file_carving',), ('signatures',), 'Signatures heuristiques ; extraction desactivee.'),
 ('journalctl', ('log_analysis','host_telemetry'), ('logs',), 'Journaux visibles selon les droits ; sorties sensibles possibles.'),
 ('nft', ('firewall_configuration','configuration_audit'), ('ruleset',), 'Lecture souvent privilegiee ; execution bloquee ici.'),
 ('man', ('documentation_tools','command_reference'), ('manual',), 'Documentation locale parfois absente.'),
 ('systemctl', ('service_management',), ('services',), 'Liste uniquement, aucun changement de service.'),
)
PROBES = {name: ('--version',) for name, *_ in _DATA}
PROBES.update(ip=('-Version',), ss=('-V',), dig=('-v',), exiftool=('-ver',),
              tshark=('-v',), binwalk=('--help',))
# Optional options must be seen in help, not inferred from a version number.
HELP_OPTIONS = {'nmap': ('--reason',), 'journalctl': ('--since',), 'strings': ('--all',)}

# Fixed allowlist: queries never become executable names or arguments.
OSINT_DOCUMENTED_TOOLS = (
    'whois', 'dig', 'dnsrecon', 'dnsenum', 'amass', 'sublist3r', 'fierce',
    'theharvester', 'dmitry', 'whatweb', 'wafw00f', 'sherlock', 'spiderfoot',
    'recon-ng', 'exiftool', 'mat2', 'foremost', 'binwalk', 'strings', 'metagoofil',
    'curl', 'nmap', 'subfinder', 'gau', 'maigret', 'blackbird', 'social-analyzer',
    'holehe', 'whatsmyname', 'phoneinfoga',
    'httpx', 'dnsx', 'photon', 'trufflehog', 'gitleaks',
)
DOCUMENTED_EXECUTABLES = {'theharvester': 'theHarvester'}
DOCUMENTATION_DIR = Path(__file__).resolve().parents[1] / 'data' / 'documentation'

def _documentation_text(raw, limit=2000):
    text = raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else raw
    text = re.sub(r'.\x08', '', text)  # man overstrike formatting
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    return ''.join(c for c in text if c in '\n\t' or ord(c) >= 32)[:limit]

def _reference(name):
    for filename in (name + '.md', name + '-kali.md'):
        try:
            with (DOCUMENTATION_DIR / filename).open('rb') as handle:
                text = _documentation_text(handle.read(8192), limit=2001)
            if text.strip():
                return text, 'fiche locale ' + filename + ' (version installée non vérifiée)'
        except OSError:
            continue
    return None, None

def _osint_documentation_names(query):
    """Relie les indices aux outils du catalogue, sans dériver de pseudonyme."""
    matches = []
    for name in OSINT_DOCUMENTED_TOOLS:
        match = re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', query, re.IGNORECASE)
        if match:
            matches.append((match.start(), name))
    names = [name for _, name in sorted(matches)[:2]]
    if not names:
        text = query.casefold()
        if re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(email|courriel|adresse électronique)\b', text):
            names = ['holehe']
        elif re.search(r'\b(domaine|domain|dns|sous-domaines?)\b', text):
            names = ['dig', 'whois']
        elif re.search(r'\b(métadonnées|metadonnees|exif|image|photo)\b', text):
            names = ['exiftool']
        elif re.search(r'\b(pseudo(?:nyme)?s?|username)\b', text):
            names = ['whatsmyname', 'maigret']
        elif re.search(r'\b(téléphone|telephone|numéro|numero)\b', text):
            names = ['phoneinfoga']
    return names


def osint_catalog_context(query):
    """Inventaire compact et rôles réels, sans commande, sonde ni réseau."""
    from tools_catalog import load_catalog
    from tools_installer import ToolsInstaller
    from tool_guidance import guide_for, integration_for

    tools = load_catalog()
    installer = ToolsInstaller(tools)
    relevant = set(_osint_documentation_names(query))
    inventory, details = [], []
    for tool in tools:
        key = tool['id']
        if relevant and key not in relevant:
            continue
        integration = integration_for(key)
        if tool['source'] == 'builtin':
            state = 'intégré'
        elif tool['source'] == 'vendored':
            if not tool.get('artifact'):
                state = 'indisponible'
            else:
                try:
                    state = 'copie vérifiée' if installer.executable(key) else 'copie non préparée ou non vérifiée'
                except (OSError, ValueError):
                    state = 'copie non vérifiée'
        else:
            state = ('chemin système présent' if shutil.which(tool['executable'], path='/usr/bin:/bin')
                     else 'absent')
        inventory.append([key, state, ','.join(tool['input_types']), integration['level']])
        if key in relevant:
            guide = guide_for(key)
            preparation_possible = state in ('intégré', 'copie vérifiée', 'chemin système présent')
            details.append(dict(outil=key, etat=state, role=guide['purpose'],
                                preparation_possible=preparation_possible,
                                controle_local=('intégrité de la copie contrôlée, sans essai de démarrage'
                                                if state == 'copie vérifiée' else
                                                'chemin présent, version et dépendances non contrôlées'
                                                if state == 'chemin système présent' else state),
                                limites=guide['limits'], entrees=tool['input_types'],
                                parcours=integration['routes'] if preparation_possible else [],
                                activite=tool['activity'],
                                reseau=tool['needs_network'],
                                fiche='/tools ' + key,
                                sens_parcours=('Les parcours préparent une recherche et demandent une approbation ; '
                                                'ils ne sont pas des commandes de documentation.')))
    return dict(outils_pertinents=details,
                outils_repertories=[tool['id'] for tool in tools],
                portee_inventaire='Outils pertinents pour cette demande seulement.' if relevant else 'Catalogue complet.',
                colonnes_inventaire=['outil', 'presence_locale', 'types_indices', 'integration'],
                inventaire=inventory,
                limite_verification=('Présence système = chemin trouvé seulement ; version et dépendances non sondées. '
                                     'guided = action accompagnée ; builtin = moteur natif ; '
                                     'workflow = parcours intégré ; shell = shell et aide ; planned = indisponible. '
                                     'La présence au catalogue ne prouve pas que l’outil peut être exécuté.'))


def osint_availability_notice(context):
    """État factuel issu du contrôle local, affiché séparément du texte du modèle."""
    catalogue = context.get('catalogue_outils') if isinstance(context, dict) else None
    if not isinstance(catalogue, dict):
        return None
    lines = []
    for tool in catalogue.get('outils_pertinents', ()):
        state = tool['etat']
        if tool['preparation_possible']:
            outcome = 'Préparation possible ; exécution soumise à approbation.'
        else:
            outcome = 'Disponibilité non confirmée ; consulter ' + tool['fiche'] + '.'
        lines.append('État local — ' + tool['outil'] + ' : ' + state + '. ' + outcome)
    return '\n'.join(lines) if lines else None


def osint_documentation(query):
    """Retrieve bounded local references; never execute investigation commands."""
    from tools_catalog import load_catalog
    from tools_installer import ToolsInstaller

    names = _osint_documentation_names(query)
    if not names:
        return []
    man = shutil.which('man', path='/usr/bin:/bin')
    tools = {tool['id']: tool for tool in load_catalog()}
    installer = ToolsInstaller(tools.values())
    rows = []
    for name in names:
        tool = tools[name]
        if tool['source'] == 'kali':
            executable = shutil.which(tool['executable'], path='/usr/bin:/bin')
        elif tool['source'] == 'vendored' and tool.get('artifact'):
            executable = installer.executable(name)
        else:
            executable = None
        native = tool['source'] == 'builtin'
        row = {'outil': name, 'presence': 'present' if executable or native else 'absent',
               'version': 'non verifiee',
               'portee_presence': ('Moteur Python intégré ; aucun exécutable shell requis.' if native else
                                   'PATH système uniquement ; dépendances non sondées.' if tool['source'] == 'kali'
                                   else 'Copies embarquées vérifiées uniquement ; aucun homonyme PATH exécuté.')}
        documentation, source = None, None
        source_kind, truncated = 'absente', False
        # Amass v5 starts its network-dependent engine even for enum -h.
        # Prefer the qualified reference, and never use help as a readiness probe.
        if name == 'amass':
            if executable:
                from tools_catalog import discover_tools
                state = discover_tools([tool])[name]
                if state.state == 'missing_dependency':
                    documentation, source = state.diagnostic, 'diagnostic des prérequis locaux'
                    source_kind = 'diagnostic'
            if not documentation:
                documentation, source = _reference(name)
                if documentation:
                    source_kind = 'fiche'
            if not documentation and executable:
                documentation = state.diagnostic or 'Moteur Amass non vérifié ; consulter docs/amass-v5.md.'
                source, source_kind = 'diagnostic local Amass', 'diagnostic'
        if not documentation and executable and man and tool['source'] == 'kali':
            result = run(man, ('--', name), timeout=2, output_limit=16384)
            if result.status in ('succeeded', 'output_limit') and result.stdout.strip():
                documentation = _documentation_text(result.stdout, limit=2001)
                source = 'man local, extrait potentiellement tronque'
                source_kind = 'man'
                truncated = result.status == 'output_limit'
        if not documentation:
            documentation, source = _reference(name)
            if documentation:
                source_kind = 'fiche'
        if not documentation and executable and name not in ('whatsmyname', 'amass'):
            result = run(executable, ('--help',), timeout=2, output_limit=8192)
            if result.status in ('succeeded', 'output_limit'):
                documentation = _documentation_text(result.stdout + result.stderr, limit=2001)
                source = 'aide locale --help, extrait potentiellement tronque'
                source_kind = 'help'
                truncated = result.status == 'output_limit'
        row['documentation'] = documentation[:2000] if documentation else (
            'Aucune syntaxe locale vérifiée. Ne pas inventer de commande ni d’option ; '
            'demander une aide locale validée avant toute proposition.')
        row['source'] = source if documentation else 'diagnostic local : sources absentes ou illisibles'
        row['type_source'] = source_kind
        row['documentation_tronquee'] = bool(documentation and (truncated or len(documentation) > 2000))
        from tool_guidance import integration_for
        integration = integration_for(name)
        row['integration'] = integration['label']
        row['parcours'] = integration['routes']
        rows.append(row)
    return rows

def identity(path):
    st = os.stat(path)
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

class ToolRegistry:
    def __init__(self):
        self.descriptions = {x[0]: ToolDescription(*x) for x in _DATA}

    def register_description(self, description):
        if (not isinstance(description, ToolDescription) or
            type(description.id) is not str or
            not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', description.id) or
            description.id in self.descriptions or
            type(description.categories) is not tuple or type(description.capabilities) is not tuple or
            not all(type(x) is str and len(x)<=256 for x in (*description.categories,*description.capabilities)) or
            type(description.limits) is not str or type(description.prerequisites) is not str or
            len(description.limits)>4096 or len(description.prerequisites)>4096):
            raise ValueError('Description invalide ou deja enregistree')
        self.descriptions[description.id] = description

    def load_descriptions(self, text):
        if not isinstance(text, str) or len(text)>65536:
            raise ValueError('Registre trop volumineux')
        values = json.loads(text)
        if not isinstance(values, list) or len(values)>64:
            raise ValueError('Liste de descriptions requise')
        staged = ToolRegistry()
        staged.descriptions = dict(self.descriptions)
        for item in values:
            if not isinstance(item, dict) or set(item) != {'id','categories','capabilities','limits'}:
                raise ValueError('Champs descriptifs uniquement')
            if not isinstance(item['categories'], list) or not isinstance(item['capabilities'], list):
                raise ValueError('Categories/capacites doivent etre des listes')
            staged.register_description(ToolDescription(item['id'],tuple(item['categories']),
                tuple(item['capabilities']),item['limits']))
        self.descriptions = staged.descriptions

    def discover(self, *, budget=12.0, per_probe=0.7, search_path=None):
        if not 0 < budget <= 60 or not 0 < per_probe <= 3:
            raise ValueError('Bornes de decouverte invalides')
        deadline = time.monotonic() + budget
        inventory = {}
        for name in self.descriptions:
            path = (shutil.which(name, path=search_path) if search_path is not None
                    else shutil.which(name))
            if not path:
                inventory[name] = InstalledTool(name, None, None, 'absent')
                continue
            try:
                path = str(Path(path).resolve())
                executable_identity = identity(path)
            except OSError:
                inventory[name] = InstalledTool(name, None, None, 'unavailable')
                continue
            item = InstalledTool(name, path, None, 'unprobed', identity=executable_identity)
            remaining = deadline - time.monotonic()
            if name in PROBES and remaining > 0:
                result = run(path, PROBES[name], timeout=min(per_probe, remaining), output_limit=16384)
                output = (result.stdout + result.stderr).decode('utf-8', 'replace')
                match = re.search(r'(?<![\d.])\d+(?:\.\d+)+(?:[a-zA-Z0-9.+~-]*)', output)
                if name in ('journalctl', 'systemctl'):
                    match = re.search(r'^systemd (\d+(?:[.-]\d+)*)', output, re.MULTILINE)
                    detected = match[1] if match else None
                else:
                    detected = match[0].rstrip('.') if match else None
                good = result.status == 'succeeded' and detected is not None
                item = replace(item, version=detected if good else None,
                    probe_status=result.status, probe_returncode=result.returncode,
                    probe_diagnostic=('dissector_error' if name == 'tshark' and 'Dissector bug' in output else
                                      'empty_output' if not output.strip() else None),
                    version_status='detected' if good else result.status if result.status != 'succeeded' else 'unknown')
                remaining = deadline - time.monotonic()
                if name in HELP_OPTIONS and remaining > 0:
                    help_result = run(path, ('--help',), timeout=min(per_probe, remaining), output_limit=32768)
                    help_text = (help_result.stdout + help_result.stderr).decode('utf-8','replace')
                    if help_result.status == 'succeeded':
                        item = replace(item, help_options=tuple(o for o in HELP_OPTIONS[name] if re.search(r'(?<![\w-])'+re.escape(o)+r'(?=[\s=,\[\]]|$)', help_text)))
            inventory[name] = item
        return inventory
