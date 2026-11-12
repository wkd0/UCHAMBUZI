# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : commandes.py
# Role          : Preparation bornee de commandes sans aucune execution
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Prototype réversible. Les dictionnaires reçus ne sont jamais des autorisations.

Aucun exécuteur ni API d'approbation : même un appelant hostile ne peut déclencher
une commande par ce module. Inventaire et périmètre doivent venir de producteurs
locaux contrôlés, jamais directement de la sortie d'un modèle.
"""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import shlex
import stat
import unicodedata

SCHEMA_VERSION = 1
SYNTAX = Path(__file__).resolve().parents[1] / 'data/commands/syntax.md'
SYNTAX_SHA256 = '54655e0e4ab614d77b1107ead40b7fc111a2d2ef9bb7945b1b3db4e8e0a3c33c'
VERSIONS = {'file': 'file-5.46', 'dig': 'DiG 9.20.24-1ubuntu0.5-Ubuntu'}
KALI_DIG = 'DiG 9.20.11-4+b1-Debian'
EXACT_VERSIONS = {'file': (VERSIONS['file'],), 'dig': (VERSIONS['dig'], KALI_DIG),
                  'exiftool': ('13.25',), 'strings': ('GNU strings (GNU Binutils for Debian) 2.45',)}
MANUALS = {
    VERSIONS['file']: ('Ubuntu et Kali 2025.3', '7cef83cc744a8af5342336922d90ad0fdc3f103422b74f1a1475739090db8104'),
    VERSIONS['dig']: ('Ubuntu', 'ea0bc673a6a04335495eff79f36019677aeed04c56642177687b693c42f08b94'),
    KALI_DIG: ('Kali GNU/Linux Rolling 2025.3', 'faaf11b7648a35d0df5b2fb87d0e4c7889e6a1e25e70b2f6037a1020097815c4'),
    '13.25': ('Kali GNU/Linux Rolling 2025.3', 'bd0ebd668ff69c1eb79a006d85612fd2e2c54baaa3e897d977f43b07fa68a150'),
    'GNU strings (GNU Binutils for Debian) 2.45': ('Kali GNU/Linux Rolling 2025.3', '22693da2dc372b7516af0c3f9e60621316e887c028af8f02998806ad7c928ffd'),
}
ORIGINS = {'file': 'https://www.darwinsys.com/file/',
           'dig': 'https://bind9.readthedocs.io/en/latest/manpages.html',
           'exiftool': 'https://exiftool.org/exiftool_pod.html',
           'strings': 'https://sourceware.org/binutils/docs/binutils/strings.html'}
LOCAL_OPERATIONS = {'file': 'identify_file', 'exiftool': 'read_metadata', 'strings': 'extract_strings'}


class Invalid(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def require(condition, code, message):
    if not condition:
        raise Invalid(code, message)


def text(value):
    require(type(value) is str and 0 < len(value) <= 4096
            and not any(unicodedata.category(c).startswith('C') for c in value),
            'invalid_text', 'Texte absent, trop long ou contenant un caractère de contrôle.')
    return value


def strings(value):
    require(type(value) is list and len(value) <= 100, 'invalid_list', 'Liste bornée requise.')
    return [text(v) for v in value]


def mapping(value, required, optional=()):
    require(type(value) is dict and set(required) <= value.keys()
            and value.keys() <= set(required) | set(optional),
            'invalid_contract', 'Champs manquants ou non autorisés dans le contrat.')


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def _absolute(value):
    value = text(value)
    require(value.startswith('/') and not value.startswith('//')
            and all(p not in ('.', '..', '') for p in value.split('/')[1:]),
            'unsafe_path', 'Chemin absolu canonique sans traversée requis.')
    return Path(value)


def _file(value, roots):
    path = _absolute(value)
    require(bool(roots), 'scope_required', 'Racine de travail autorisée requise.')
    allowed = [_absolute(root) for root in roots]
    require(any(path.is_relative_to(root) and path != root for root in allowed),
            'outside_scope', 'Fichier hors du périmètre déclaré.')
    # lstat n'ouvre pas le contenu. Refus des liens dans chaque parent également.
    for part in reversed((path, *path.parents)):
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode), 'unsafe_path', 'Lien symbolique refusé.')
    require(stat.S_ISREG(info.st_mode), 'unsafe_path', 'Fichier ordinaire requis.')
    return str(path)


def _ip(value):
    value = text(value)
    require('%' not in value, 'invalid_target', 'Identifiant de zone IP non pris en charge.')
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise Invalid('invalid_target', 'Adresse IP littérale requise.') from None
    require(not address.is_unspecified and not address.is_multicast,
            'invalid_target', 'Adresse non spécifiée ou multicast refusée.')
    return str(address)


def _domain(value):
    value = text(value).removesuffix('.')
    require(len(value) <= 253 and '.' in value and not value.split('.')[-1].isdigit()
            and all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', p)
                    for p in value.split('.')),
            'invalid_target', 'Domaine ASCII normalisé requis; aucune option ou URL acceptée.')
    return value


def _refusal(code, message):
    return dict(schema_version=1, status='refused', error={'code': code, 'message': message},
                argv=None, display=None, execution='disabled', executed=False,
                approval={'required': True, 'status': 'not_requested', 'scope': 'manual_execution'},
                technical_result={'status': 'not_run', 'exit_code': None, 'stdout': None, 'stderr': None})


def prepare(request, tool):
    """Retourne un plan JSON ou un refus explicite; ne lance rien et ne résout aucun DNS.

    Les contraintes sont déclaratives. Elles limitent la préparation mais ne prouvent
    ni l'identité d'un humain, ni la propriété d'une cible, ni une autorisation réelle.
    """
    try:
        return _prepare(request, tool)
    except Invalid as exc:
        return _refusal(exc.code, str(exc))
    except OSError:
        return _refusal('local_state_unavailable', 'Fichier ou source absent/inaccessible; revérifier localement.')


def _prepare(request, tool):
    mapping(request, ('tool_id', 'operation', 'parameters', 'indicator', 'prerequisites', 'constraints'))
    tool_id = text(request['tool_id'])
    require(tool_id in EXACT_VERSIONS, 'unsupported_tool', 'Outil hors des règles documentées.')
    require(type(tool) is dict and tool.get('id') == tool_id,
            'invalid_inventory', 'Inventaire incohérent avec l’outil demandé.')
    require(tool.get('installed') is True, 'tool_absent', 'Présence locale de l’outil non établie.')
    require(tool.get('executable_path') in ('/usr/bin/' + tool_id, '/bin/' + tool_id),
            'unsafe_executable', 'Chemin exécutable hors de la liste système prise en charge.')
    require(type(tool.get('version')) is str and tool['version'] in EXACT_VERSIONS[tool_id], 'unverified_version',
            'Version inconnue ou sans règle exacte; consulter le manuel correspondant.')
    text(tool.get('detection_origin'))
    text(tool.get('version_origin'))
    require(hashlib.sha256(SYNTAX.read_bytes()).hexdigest() == SYNTAX_SHA256,
            'source_integrity', 'Note syntaxique modifiée; revue de la règle requise.')
    indicator = request['indicator']
    require(type(indicator) is dict and indicator.get('validation') == 'valid',
            'invalid_indicator', 'Indice validé requis.')
    target = text(indicator.get('normalized'))
    kind = indicator.get('type')
    operation = text(request['operation'])
    params = request['parameters']
    constraints = request['constraints']
    mapping(constraints, (), ('allow_network', 'authorized_targets', 'authorized_resolvers', 'file_roots'))
    network = constraints.get('allow_network', False)
    require(type(network) is bool, 'invalid_constraints', 'allow_network doit être booléen.')
    targets = strings(constraints.get('authorized_targets', []))
    resolvers = strings(constraints.get('authorized_resolvers', []))
    roots = strings(constraints.get('file_roots', []))
    prerequisites = strings(request['prerequisites'])
    argv = [tool['executable_path']]
    explanations = []
    limits = ['Préparation seulement; aucun résultat technique observé.',
              'Inventaire déclaratif reçu du producteur local; exécutable non authentifié ici.',
              'Observations susceptibles de changer; refaire les contrôles avant action manuelle.']
    if tool_id == 'file':
        require(operation == 'identify_file' and kind == 'file', 'unsupported_operation',
                'Seule l’identification locale d’un fichier est prise en charge.')
        mapping(params, ())
        target = _file(target, roots)
        argv += ['-b', '-h', target]
        explanations = [('-b', 'Description sans préfixe de nom.'),
                        ('-h', 'Ne suit pas le lien symbolique final.'),
                        (target, 'Fichier ordinaire absolu dans la racine déclarée.')]
        prerequisites += ['Copie de travail lisible et montage adapté au contexte forensic.',
                          'Examiner MAGIC, la base magic et l’environnement avant action manuelle.']
        limits += ['La lecture peut modifier l’atime; résultat heuristique.',
                   'Les contrôles de chemins ne verrouillent ni fichiers ni montages (course possible).',
                   'Aucun contrôle des montages réseau; une lecture peut mobiliser un FS distant.']
        expected = 'Description du type probable si l’utilisateur exécute séparément la commande.'
        operation_type, risk = 'local', 'moderate'
    elif tool_id in ('exiftool', 'strings'):
        require(operation == LOCAL_OPERATIONS[tool_id] and kind == 'file', 'unsupported_operation',
                'Seule la lecture locale du fichier explicitement sélectionné est prise en charge.')
        require(not network, 'invalid_constraints', 'Cette opération ne prend aucun périmètre réseau.')
        target = _file(target, roots)
        if tool_id == 'exiftool':
            require(not any(c in target for c in '*?[]'), 'unsafe_path',
                    'Motifs de fichiers refusés pour cette lecture; choisir un nom sans caractère générique.')
            mapping(params, ())
            argv += ['-config', '', '-j', '-G1', '-s', '--', target]
            explanations = [('-config ""', 'Désactive la configuration personnelle; placé avant toute autre option.'),
                            ('-j', 'Métadonnées au format JSON, sans fichier JSON à importer.'),
                            ('-G1', 'Qualifie les noms des tags avec leur groupe famille 1.'),
                            ('-s', 'Noms courts des tags.'), ('--', 'Fin des options.'),
                            (target, 'Un seul fichier ordinaire explicitement sélectionné.')]
            expected = 'Métadonnées disponibles au format JSON ou erreur; aucune authenticité déduite.'
            limits += ['Les métadonnées peuvent être absentes ou modifiées; elles ne prouvent ni auteur ni date.',
                       'Des noms JSON identiques peuvent masquer des tags; extraction non exhaustive.',
                       'Aucune affectation de tag, écriture, récursion ou commande Perl fournie par l’utilisateur.']
        else:
            mapping(params, ('min_length',))
            minimum = params['min_length']
            require(type(minimum) is int and 4 <= minimum <= 64, 'unsafe_option',
                    'min_length doit être un entier entre 4 et 64.')
            argv += ['-a', '-n', str(minimum), '-e', 's', target]
            explanations = [('-a', 'Parcourt tout le fichier sans sélection des sections par BFD.'),
                            ('-n ' + str(minimum), 'Nombre minimal de caractères imprimables.'),
                            ('-e s', 'Caractères sur un octet de 7 bits; pas de décodage Unicode implicite.'),
                            (target, 'Un seul chemin absolu, jamais une option ni un fichier d’arguments.')]
            expected = 'Séquences imprimables ou sortie vide; aucune preuve d’exécution ou de comportement.'
            limits += ['Des chaînes peuvent être fortuites; absence de décodage, décompression ou analyse sémantique.',
                       'La sortie peut être volumineuse; aucune borne de durée ou de sortie à l’exécution manuelle.']
        prerequisites += ['Copie de travail lisible et environnement isolé adapté au contenu non fiable.',
                          'Examiner les montages et l’environnement avant une action manuelle distincte.']
        limits += ['Lecture susceptible de modifier l’atime; aucune garantie de chaîne de conservation.',
                   'Les chemins et montages peuvent changer après préparation; aucune protection contre une course.',
                   'Un chemin local peut désigner un montage distant; sa lecture peut alors provoquer du réseau.',
                   'Les données éventuellement extraites restent non fiables, même sous forme JSON.']
        operation_type, risk = 'local', 'moderate'
    else:
        require(operation in ('dns_query', 'dns_reverse'), 'unsupported_operation', 'Opération DNS inconnue.')
        mapping(params, ('resolver', 'record_type') if operation == 'dns_query' else ('resolver',))
        require(network, 'network_forbidden', 'Préparation réseau désactivée par défaut.')
        resolver = _ip(params['resolver'])
        require(resolver in resolvers, 'outside_scope', 'Résolveur hors du périmètre déclaré.')
        if operation == 'dns_query':
            require(kind == 'domain', 'invalid_indicator', 'Domaine explicite requis; aucune extraction implicite.')
            target = _domain(target)
            require(type(params['record_type']) is str and params['record_type'] in ('A', 'AAAA', 'MX', 'TXT'),
                    'unsafe_option', 'Type DNS hors de la liste autorisée.')
            query = ['-q', target + '.', '-t', params['record_type']]
        else:
            require(kind == 'ip', 'invalid_indicator', 'Indice IP explicite requis.')
            target = _ip(target)
            query = ['-x', target]
        require(target in targets, 'outside_scope', 'Cible hors du périmètre déclaré.')
        argv += ['-r', '@' + resolver] + query + ['+nosearch', '+timeout=2', '+tries=1']
        explanations = [('-r', 'Ignore le fichier personnel .digrc.'),
                        ('@' + resolver, 'Résolveur IP explicitement déclaré.'),
                        (' '.join(query), 'Question DNS unique et type autorisé.'),
                        ('+nosearch', 'Aucun suffixe de recherche ajouté.'),
                        ('+timeout=2', 'Délai par requête; pas un délai global garanti.'),
                        ('+tries=1', 'Nombre de tentatives configuré à un.')]
        prerequisites += ['Autorisation humaine distincte pour cible, résolveur et effets de récursion.',
                          'Réseau requis seulement lors d’une éventuelle exécution manuelle.']
        limits += ['Requête active journalisable; récursion possible vers des serveurs tiers.',
                   'Reprise TCP possible; ne prouve ni propriété ni existence d’une boîte ou page.']
        expected = 'Réponse DNS ou erreur/absence; rien n’est présumé avant une action séparée.'
        operation_type, risk = 'active', 'moderate'
    result = dict(schema_version=1, status='prepared', tool_id=tool_id, operation=operation,
                  detected_version=tool['version'], argv=argv, display=shlex.join(argv),
                  parameter_explanations=[dict(argument=a, explanation=e) for a, e in explanations],
                  prerequisites=prerequisites, risk=risk, operation_type=operation_type,
                  network_required=tool_id == 'dig', expected_result=expected, limitations=limits,
                  compatibility={'status': 'documented_exact_version', 'tested_on_kali': False},
                  sources=[{'title': 'Notes syntaxiques des manuels locaux', 'path': str(SYNTAX),
                            'sha256': SYNTAX_SHA256, 'origin': ORIGINS[tool_id],
                            'consulted_at': '2026-11-08' if tool_id in ('exiftool', 'strings') else '2026-11-07',
                            'documented_version': tool['version'], 'environment': MANUALS[tool['version']][0],
                            'original_local_path': '/usr/share/man/man1/' + tool_id + ('.1p.gz' if tool_id == 'exiftool' else '.1.gz'),
                            'original_sha256': MANUALS[tool['version']][1]}],
                  approval={'required': True, 'status': 'pending_human_review', 'scope': 'manual_execution'},
                  execution='disabled', executed=False,
                  technical_result={'status': 'not_run', 'exit_code': None, 'stdout': None, 'stderr': None})
    result['id'] = identity(result)
    return result


def prepare_from_recommendation(recommendation, indicator, inventory, *, operation, parameters, constraints):
    """Adaptateur Agent 3 → Agent 4; aucun import des autres composants.

    Une revue documentaire, même « approved », n'autorise jamais une exécution.
    Les empreintes contrôlent la cohérence, pas l'identité du producteur.
    """
    try:
        require(type(recommendation) is dict, 'invalid_recommendation', 'Recommandation requise.')
        r = dict(recommendation)
        ident = r.pop('id', None)
        require(r.get('schema_version') == 1 and r.get('status') == 'proposed'
                and ident == identity(r), 'invalid_recommendation', 'Révision de recommandation incohérente.')
        require(type(inventory) is list and all(type(t) is dict for t in inventory),
                'invalid_inventory', 'Liste d’outils requise.')
        matches = [t for t in inventory if t.get('id') == r.get('tool')]
        require(len(matches) == 1, 'invalid_inventory', 'Observation unique de l’outil requise.')
        tool = matches[0]
        require(type(indicator) is dict and r.get('indicator_type') == indicator.get('type')
                and r.get('local_version') == tool.get('version'),
                'stale_recommendation', 'Indice ou version différent de la recommandation.')
        refs = r.get('references')
        require(r.get('preparation_status') == 'documented_basis' and type(refs) is list and bool(refs)
                and all(type(ref) is dict and ref.get('availability') == 'local'
                        and ref.get('compatibility') == 'documented'
                        and ref.get('freshness') == 'current'
                        and ref.get('verification') == 'consulted_local'
                        and ref.get('authority') in ('official', 'upstream_manual') for ref in refs),
                'undocumented_recommendation', 'Références actuelles et version documentée requises.')
        if r.get('tool') in ('exiftool', 'strings'):
            manual = MANUALS.get(tool.get('version'))
            require(manual is not None and any(ref.get('original_sha256') == manual[1] for ref in refs),
                    'undocumented_recommendation', 'Référence du manuel exact de cet outil requise.')
        result = prepare(dict(tool_id=r.get('tool'), operation=operation, parameters=parameters,
                              indicator=indicator, prerequisites=r.get('prerequisites'), constraints=constraints), tool)
        if result['status'] == 'prepared':
            result.pop('id')
            result['recommendation_id'] = ident
            result['id'] = identity(result)
        return result
    except Invalid as exc:
        return _refusal(exc.code, str(exc))
    except (TypeError, ValueError):
        return _refusal('invalid_recommendation', 'Données non sérialisables dans la recommandation.')
