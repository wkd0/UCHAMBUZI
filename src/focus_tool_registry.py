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
OSINT_DOCUMENTED_TOOLS = ('whois', 'dig', 'exiftool', 'theharvester', 'amass', 'recon-ng', 'sublist3r', 'curl',
                          'subfinder', 'gau', 'maigret', 'blackbird', 'holehe',
                          'whatsmyname', 'phoneinfoga')
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
                text = _documentation_text(handle.read(8192))
            if text.strip():
                return text, 'fiche locale ' + filename + ' (version installée non vérifiée)'
        except OSError:
            continue
    return None, None

def osint_documentation(query):
    """Retrieve bounded local references; never execute investigation commands."""
    names = [name for name in OSINT_DOCUMENTED_TOOLS
             if re.search(r'(?<![\w-])' + re.escape(name) + r'(?![\w-])', query, re.IGNORECASE)][:2]
    if not names:
        text = query.casefold()
        if re.search(r'\b(domaine|domain|dns|sous-domaines?)\b', text):
            names = ['dig', 'whois']
        elif re.search(r'\b(métadonnées|metadonnees|exif|image|photo)\b', text):
            names = ['exiftool']
        elif re.search(r'\b(email|courriel|adresse électronique)\b', text):
            names = ['theharvester']
    if not names:
        return []
    man = shutil.which('man', path='/usr/bin:/bin')
    rows = []
    for name in names:
        executable = shutil.which(name)
        row = {'outil': name, 'presence': 'present' if executable else 'absent',
               'version': 'non verifiee'}
        documentation, source = None, None
        if executable and man:
            result = run(man, ('--', name), timeout=2, output_limit=16384)
            if result.status in ('succeeded', 'output_limit') and result.stdout.strip():
                documentation = _documentation_text(result.stdout)
                source = 'man local, extrait potentiellement tronque'
        if not documentation:
            documentation, source = _reference(name)
        if not documentation and executable and name != 'whatsmyname':
            result = run(executable, ('--help',), timeout=2, output_limit=8192)
            if result.status in ('succeeded', 'output_limit'):
                documentation = _documentation_text(result.stdout + result.stderr)
                source = 'aide locale --help, extrait potentiellement tronque'
        row['documentation'] = documentation or (
            'Aucune syntaxe locale vérifiée. Ne pas inventer de commande ni d’option ; '
            'demander une aide locale validée avant toute proposition.')
        row['source'] = source if documentation else 'diagnostic local : sources absentes ou illisibles'
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

    def discover(self, *, budget=12.0, per_probe=0.7):
        if not 0 < budget <= 60 or not 0 < per_probe <= 3:
            raise ValueError('Bornes de decouverte invalides')
        deadline = time.monotonic() + budget
        inventory = {}
        for name in self.descriptions:
            path = shutil.which(name)
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
