# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : indices_outils.py
# Role          : Reconnaissance prudente des indices et inventaire local
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Prototype autonome : aucune commande d'investigation ni requête réseau."""
import ipaddress
import hashlib
import mimetypes
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit


def _domain(value):
    if value.endswith('..'):
        raise ValueError('point terminal répété')
    value = value.removesuffix('.')
    if not value or len(value) > 253 or '.' not in value:
        raise ValueError('domaine incomplet')
    labels = value.split('.')
    encoded = []
    for label in labels:
        if not label or any(ord(c) < 33 for c in label):
            raise ValueError('étiquette vide ou caractère interdit')
        part = label.encode('idna').decode('ascii').lower()
        if len(part) > 63 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', part):
            raise ValueError('étiquette DNS invalide')
        if part.startswith('xn--'):
            part.encode('ascii').decode('idna')
        encoded.append(part)
    if len('.'.join(encoded)) > 253 or encoded[-1].isdigit():
        raise ValueError('domaine invalide ou adresse numérique ambiguë')
    return '.'.join(encoded)


_INJECTION_HINT = re.compile(
    r'(?:ignore[rz]?[\s_-]+(?:all[\s_-]+|toutes?[\s_-]+|les[\s_-]+|previous[\s_-]+|prior[\s_-]+)*'
    r'(?:instructions?|rules?|règles?|consignes?|directives?|prompts?)'
    r'|<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>|\[/?INST\]|<<SYS>>|<</SYS>>'
    r'|(?:^|[\s/_-])(?:SYSTEM|INSTRUCTION)\s*:)',
    re.IGNORECASE,
)


def _result(kind, original, normalized, status, ambiguities, explanation):
    return dict(id=(hashlib.sha256((kind + '\0' + original).encode('utf-8', 'surrogatepass')).hexdigest()[:16]
                    if isinstance(kind, str) and isinstance(original, str) else None),
                type=kind, original=original, normalized=normalized,
                validation=status, ambiguities=ambiguities, warnings=ambiguities,
                explanation=explanation, metadata={}, relations=[],
                provenance={'origin': 'user_input'})


def classify(value, kind):
    """Valide un candidat explicite; ne vérifie ni existence réseau ni propriété."""
    try:
        ambiguities = ['La syntaxe ne prouve ni existence réseau ni autorisation d’utilisation.']
        if not isinstance(value, str) or not value:
            raise ValueError('une chaîne non vide est requise')
        if kind == 'ip':
            address = ipaddress.ip_address(value)
            normalized = str(address)
        elif kind == 'domain':
            normalized = _domain(value)
            if not value.isascii():
                ambiguities.append('Normalisation IDNA 2003 : confirmer la correspondance du domaine.')
            ambiguities.append('La syntaxe ne prouve ni existence ni enregistrement du domaine.')
        elif kind == 'email':
            if value.count('@') != 1:
                raise ValueError('séparateur @ invalide')
            local, domain = value.rsplit('@', 1)
            if len(local) > 64 or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*", local):
                raise ValueError('partie locale hors du sous-ensemble pris en charge')
            normalized = local + '@' + _domain(domain)
            if not domain.isascii():
                ambiguities.append('Normalisation IDNA 2003 : confirmer la correspondance du domaine.')
            if len(normalized) > 254:
                raise ValueError('adresse trop longue')
            ambiguities.append('La syntaxe ne prouve pas que la boîte existe; adresses citées et Unicode locales non prises en charge.')
        elif kind == 'url':
            parts = urlsplit(value)
            if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username is not None or parts.password is not None:
                raise ValueError('URL HTTP(S) avec hôte requise, sans identifiants')
            if any(ord(c) <= 32 or ord(c) == 127 for c in value) or re.search(r'%(?![0-9a-fA-F]{2})', value):
                raise ValueError('caractère ou encodage interdit')
            if any(c in value for c in '<>\\"{}|^`') or any(c.isspace() for c in value):
                raise ValueError('caractère interdit dans une URL HTTP(S)')
            if parts.netloc.endswith(':'):
                raise ValueError('port vide')
            port = parts.port
            try:
                host = str(ipaddress.ip_address(parts.hostname))
                if ':' in host:
                    host = '[' + host + ']'
            except ValueError:
                host = _domain(parts.hostname)
            suffix = value[len(parts.scheme) + 3 + len(parts.netloc):]
            normalized = parts.scheme.lower() + '://' + host + (':' + str(port) if port is not None else '') + suffix
            if not parts.hostname.isascii():
                ambiguities.append('Normalisation IDNA 2003 : confirmer la correspondance du domaine.')
            ambiguities.append('La syntaxe ne prouve ni accessibilité ni sûreté de l’URL.')
        elif kind == 'file':
            if '\x00' in value:
                raise ValueError('caractère nul interdit')
            normalized = None
            try:
                path = Path(value).expanduser()
                normalized = str(path) if path.is_absolute() else os.path.join(os.getcwd(), str(path))
                info = path.stat()
            except (OSError, RuntimeError) as exc:
                return _result(kind, value, normalized, 'unknown', ambiguities + [str(exc)], 'Chemin absent ou inaccessible; existence non établie.')
            if not stat.S_ISREG(info.st_mode):
                return _result(kind, value, normalized, 'invalid', ambiguities + ['Le chemin existe mais ne désigne pas un fichier ordinaire.'], 'Chemin local.')
            ambiguities.append('Existence observée au moment du contrôle; liens symboliques suivis, contenu non lu.')
            if _INJECTION_HINT.search(value):
                ambiguities.append('Alerte sécurité : motif d’injection de prompt détecté dans le chemin du fichier ; traité comme donnée non fiable.')
        elif kind == 'phone':
            clean = re.sub(r'[\s.-]', '', value)
            if not clean.startswith('+'):
                raise ValueError('format E.164 requis : doit débuter par le signe international +')
            digits_only = clean[1:]
            if not digits_only.isdigit():
                raise ValueError('format E.164 invalide : seuls les chiffres sont acceptés après +')
            if digits_only.startswith('0'):
                raise ValueError('format E.164 invalide : l’indicatif pays ne peut débuter par 0')
            if not (7 <= len(digits_only) <= 15):
                raise ValueError(f'longueur E.164 invalide ({len(digits_only)} chiffres, attendu entre 7 et 15)')
            normalized = clean
            ambiguities.append('La syntaxe E.164 ne prouve ni attribution ni activité effective de la ligne.')
            if clean != value:
                ambiguities.append('Séparateurs de lisibilité retirés pour la normalisation E.164.')
        elif kind == 'hash':
            clean = value.strip().lower()
            if not re.fullmatch(r'[0-9a-f]+', clean):
                raise ValueError('empreinte cryptographique invalide : caractères hexadécimaux requis')
            algo_map = {32: 'md5', 40: 'sha1', 64: 'sha256', 128: 'sha512'}
            if len(clean) not in algo_map:
                raise ValueError(f'longueur d’empreinte non reconnue : {len(clean)} caractères (attendu 32, 40, 64 ou 128)')
            normalized = clean
            algorithm = algo_map[len(clean)]
            ambiguities.append('Une empreinte cryptographique ne prouve pas à elle seule la disponibilité locale du fichier correspondant.')
        elif kind in ('username', 'pseudo'):
            clean = value.strip()
            had_prefix = clean.startswith('@')
            raw = clean[1:] if had_prefix else clean
            if not raw:
                raise ValueError('pseudonyme vide')
            if '\x00' in clean or any(c.isspace() for c in clean):
                raise ValueError('caractère d’espacement ou nul interdit dans un pseudonyme')
            if '@' in raw:
                raise ValueError('caractère @ interdit à l’intérieur du pseudonyme (adresse e-mail ?)')
            if not re.fullmatch(r'[a-zA-Z0-9._-]{1,64}', raw):
                raise ValueError('pseudonyme invalide : attendu 1 à 64 caractères alphanumériques, tirets, points ou soulignés')
            if not had_prefix and '.' in raw and re.search(r'\.[a-z]{2,10}$', raw, re.IGNORECASE):
                raise ValueError('ambiguïté domaine : le motif ressemble à un nom de domaine FQDN')
            normalized = raw
            ambiguities.append('La syntaxe ne prouve ni l’existence du profil ni l’unicité sur les plateformes.')
            if had_prefix:
                ambiguities.append('Préfixe @ retiré pour la normalisation du pseudonyme.')
        elif kind == 'image':
            if '\x00' in value:
                raise ValueError('caractère nul interdit')
            _IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.svg', '.raw', '.heic', '.ico'}
            normalized = None
            path = Path(value).expanduser()
            ext = path.suffix.lower()
            try:
                normalized = str(path) if path.is_absolute() else os.path.join(os.getcwd(), str(path))
                info = path.stat()
                exists = True
            except (OSError, RuntimeError) as exc:
                exists = False
                info = None
                stat_exc = str(exc)

            if exists:
                if not stat.S_ISREG(info.st_mode):
                    return _result(kind, value, normalized, 'invalid', ambiguities + ['Le chemin existe mais ne désigne pas un fichier ordinaire.'], 'Chemin local.')
                mime = mimetypes.guess_type(path.name)[0]
                is_img_ext = ext in _IMAGE_EXTS or bool(mime and mime.startswith('image/'))
                ambiguities.append('Existence observée au moment du contrôle; liens symboliques suivis, métadonnées non lues.')
                if not is_img_ext:
                    ambiguities.append('Avertissement : extension de fichier non standard pour une image.')
                if _INJECTION_HINT.search(value):
                    ambiguities.append('Alerte sécurité : motif d’injection de prompt détecté dans le chemin du fichier ; traité comme donnée non fiable.')
                res = _result(kind, value, normalized, 'valid', ambiguities, 'Chemin de fichier image validé.')
                res['metadata'] = {'exists': True, 'size': info.st_size, 'modified_ns': info.st_mtime_ns,
                                   'mode': stat.S_IMODE(info.st_mode), 'type': 'image_file',
                                   'extension': ext, 'mime_from_extension': mime, 'is_image_extension': is_img_ext}
                return res
            else:
                if ext in _IMAGE_EXTS:
                    return _result(kind, value, normalized, 'unknown', ambiguities + [f'Chemin absent ou inaccessible : {stat_exc}'], 'Chemin d’image syntaxiquement valide mais fichier non présent localement.')
                else:
                    return _result(kind, value, normalized, 'invalid', ambiguities + ['Extension non reconnue comme image et fichier absent.'], 'Fichier image absent et extension non image.')
        else:
            raise ValueError('type inconnu')
        result = _result(kind, value, normalized, 'valid', ambiguities,
                         'Syntaxe prise en charge et contrôles locaux applicables réussis.')
        if kind == 'ip':
            private_ranges = (('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
                              if address.version == 4 else ('fc00::/7',))
            private = any(address in ipaddress.ip_network(net) for net in private_ranges)
            result['metadata'] = {'version': address.version,
                                  'classification': ('loopback' if address.is_loopback else
                                                     'link_local' if address.is_link_local else
                                                     'multicast' if address.is_multicast else
                                                     'unspecified' if address.is_unspecified else
                                                     'private' if private else
                                                     'global' if address.is_global else 'reserved_or_special'),
                                  'is_global': address.is_global}
        elif kind == 'url':
            host_kind = 'ip' if _is_ip(parts.hostname) else 'domain'
            host_value = str(ipaddress.ip_address(parts.hostname)) if host_kind == 'ip' else _domain(parts.hostname)
            result['metadata'] = {'scheme': parts.scheme.lower(), 'host': host_value,
                                  'host_type': host_kind, 'port': port, 'path': parts.path,
                                  'query_parameter_names': [pair.split('=', 1)[0] for pair in parts.query.split('&') if pair],
                                  'query_present': bool(parts.query)}
            result['relations'] = [{'type': 'contains_host', 'indicator_type': host_kind,
                                    'value': host_value}]
        elif kind == 'email':
            result['metadata'] = {'local_part': local, 'domain': _domain(domain),
                                  'personal_data': True}
            result['relations'] = [{'type': 'contains_domain', 'indicator_type': 'domain',
                                    'value': _domain(domain)}]
        elif kind == 'file':
            result['metadata'] = {'exists': True, 'size': info.st_size,
                                  'modified_ns': info.st_mtime_ns, 'mode': stat.S_IMODE(info.st_mode),
                                  'type': 'regular_file', 'symlink_followed': any(part.is_symlink() for part in (path, *path.parents)),
                                  'mime_from_extension': mimetypes.guess_type(path.name)[0]}
            ambiguities.append('Type MIME proposé depuis l’extension uniquement; contenu non examiné.')
        elif kind == 'phone':
            result['metadata'] = {
                'e164': normalized,
                'digits_count': len(normalized) - 1,
                'personal_data': True,
            }
        elif kind == 'hash':
            result['metadata'] = {
                'algorithm': algorithm,
                'length': len(normalized),
                'hex': True,
            }
        elif kind in ('username', 'pseudo'):
            result['metadata'] = {
                'handle': f'@{normalized}',
                'username': normalized,
                'had_at_prefix': had_prefix,
                'personal_data': True,
            }
        return result
    except (ValueError, UnicodeError) as exc:
        return _result(kind, value, None, 'invalid', [], str(exc))


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False



def hash_file(value, algorithm='sha256', chunk_size=1024 * 1024):
    """Empreinte sur demande explicite ; lecture complète pouvant modifier l'atime."""
    if (algorithm not in ('sha256', 'sha512') or type(chunk_size) is not int
            or not 4096 <= chunk_size <= 4 * 1024 * 1024):
        raise ValueError('algorithme ou taille de bloc non pris en charge')
    path = Path(value).expanduser()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Lien symbolique refusé pour le calcul d’empreinte.')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('fichier ordinaire requis')
    digest = hashlib.new(algorithm)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (info.st_dev, info.st_ino) != (opened.st_dev, opened.st_ino)):
            raise ValueError('Fichier remplacé avant lecture.')
        count = 0
        for block in iter(lambda: stream.read(chunk_size), b''):
            digest.update(block)
            count += len(block)
        after = os.fstat(stream.fileno())
        if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Fichier modifié pendant le calcul d’empreinte.')
    return {'algorithm': algorithm, 'digest': digest.hexdigest(), 'path': str(path),
            'bytes_read': count,
            'warning': 'Lecture complète effectuée ; atime potentiellement modifié. '
                       'Contrôles ponctuels de stabilité, aucune signature ni chaîne de conservation.'}


# Ordre et recouvrement : une URL ou un courriel n'est pas découpé en domaines.
_CANDIDATE = re.compile(r'''(?P<quote>["'])(?P<quotedpath>(?:~?/|\.\.?/)[^\r\n"']+)(?P=quote)|https?://[^\s<>"“”]+|(?:~?/|\.\.?/)[^\s<>"“”]+|[^\s<>"“”,;()]+@[^\s<>"“”,;()]+|\[[0-9A-Fa-f:.]+\]|(?<![\w:])(?:[0-9A-Fa-f]*:[0-9A-Fa-f:.%]+)(?![\w:])|[\w\-]+(?:\.[\w\-]+)+(?:\.)?''', re.UNICODE | re.IGNORECASE)


def extract(text):
    """Extrait des candidats explicites sans inférer un indice depuis un nom commun."""
    results = []
    for match in _CANDIDATE.finditer(text):
        candidate = match.group('quotedpath') or match.group().rstrip('.,;!?')
        if not candidate:
            continue
        if candidate.lower().startswith(('http://', 'https://')):
            kind = 'url'
        elif candidate.startswith(('/', './', '../', '~/')):
            kind = 'file'
        elif '@' in candidate:
            kind = 'email'
        else:
            raw = candidate[1:-1] if candidate.startswith('[') and candidate.endswith(']') else candidate
            kind = 'ip' if ':' in raw or re.fullmatch(r'[0-9.]+', raw) else 'domain'
            if raw != candidate:
                result = classify(raw, kind)
                result['original'] = candidate
                result['position'] = {'start': match.start(), 'end': match.start() + len(candidate)}
                results.append(result)
                continue
        result = classify(candidate, kind)
        if match.group('quotedpath') is None and match.group() != candidate:
            result['ambiguities'].append('Ponctuation finale retirée : vérifier la valeur complète.')
        if kind == 'file' and match.group('quotedpath') is None:
            result['ambiguities'].append('Chemin non cité : la valeur peut se poursuivre après un espace.')
        start = match.start('quotedpath') if match.group('quotedpath') is not None else match.start()
        result['position'] = {'start': start, 'end': start + len(candidate)}
        results.append(result)
    return results


_CATEGORY_MENTIONS = re.compile(
    r"(?<![\w@])(?P<email>e[ -]?mail|courriel|adresse électronique)\b"
    r"|(?<!\w)(?P<ip>adresse\s+ip(?:v[46])?|ipv[46]|ip)\b"
    r"|(?<!\w)(?P<url>url)\b"
    r"|(?<!\w)(?P<file>fichiers?)\b"
    r"|(?<!\w)(?P<domain>domaines?)\b", re.IGNORECASE)


_IMAGE_EXTENSIONS = frozenset({
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
    '.tiff', '.tif', '.svg', '.raw', '.heic', '.ico',
})

_FORENSIC_FILE_EXTENSIONS = frozenset({
    '.pcap', '.pcapng', '.pdf', '.docx', '.xlsx', '.zip',
    '.tar', '.gz', '.7z', '.dump', '.dmp', '.mem', '.raw',
    '.txt', '.csv', '.log', '.json', '.xml', '.bin',
})


def detect_indice_type(value):
    """Détecte prudemment le type d'un indice textuel sans effet de bord réseau.

    Retourne l'un des types standard :
    'ip', 'domain', 'url', 'email', 'phone', 'username', 'hash', 'image', 'file'
    ou None si non identifiable.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    val = value.strip()

    # 1. URL HTTP(S)
    if val.lower().startswith(('http://', 'https://')):
        return 'url'

    # 2. Téléphone E.164 (doit commencer par + et chiffres)
    if val.startswith('+'):
        clean = re.sub(r'[\s.-]', '', val)
        if re.fullmatch(r'\+[1-9]\d{6,14}', clean):
            return 'phone'

    # 3. Courriel (contient @ et n'est pas un handle @user)
    if '@' in val and not val.startswith('@'):
        if classify(val, 'email')['validation'] == 'valid':
            return 'email'
        if re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', val):
            return 'email'

    # 4. Pseudonyme / handle explicite commençant par @
    if val.startswith('@') and len(val) > 1:
        if re.fullmatch(r'@[a-zA-Z0-9._-]{1,64}', val):
            return 'username'

    # 5. Empreinte cryptographique (hash) hexadécimale
    if re.fullmatch(r'[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64}|[0-9a-fA-F]{128}', val):
        return 'hash'

    # 6. Adresse IP (IPv4 ou IPv6)
    if _is_ip(val):
        return 'ip'

    # 7. Chemin d'accès explicite (commençant par /, ./, ../, ~/)
    if val.startswith(('/', './', '../', '~/')):
        ext = Path(val).suffix.lower()
        if ext in _IMAGE_EXTENSIONS:
            return 'image'
        return 'file'

    # 8. Fichier image par extension
    ext = Path(val).suffix.lower()
    if ext in _IMAGE_EXTENSIONS:
        return 'image'

    # 9. Fichier par extension connue ou existence locale
    if ext in _FORENSIC_FILE_EXTENSIONS:
        return 'file'
    try:
        if Path(val).is_file():
            return 'file'
    except OSError:
        pass

    # 10. Domaine FQDN
    if '.' in val and not val.endswith('..'):
        try:
            if classify(val, 'domain')['validation'] == 'valid':
                return 'domain'
        except Exception:
            pass

    # 11. Pseudonyme sans @ (identifiant alphanumérique simple)
    if re.fullmatch(r'[a-zA-Z0-9_-]{2,32}', val) and not val.isdigit():
        return 'username'

    return None


def classify_auto(value):
    """Détecte automatiquement le type d'un indice et le qualifie avec classify()."""
    kind = detect_indice_type(value)
    if not kind:
        return _result('unknown', value, None, 'invalid',
                       ['Type d’indice non reconnu ou syntaxe invalide.'],
                       'Aucun type d’indice supporté n’a pu être identifié.')
    return classify(value, kind)


def recognize(text):
    """Valeurs observées et mentions de catégories, sans inférer de valeur manquante.

    Les positions sont des indices Python de caractères, début inclus, fin exclue.
    """
    indicators = extract(text)
    mentions = []
    for match in _CATEGORY_MENTIONS.finditer(text):
        if any(match.start() < row['position']['end'] and match.end() > row['position']['start']
               for row in indicators):
            continue
        mentions.append(dict(type=match.lastgroup, original=match.group(),
                             position={'start': match.start(), 'end': match.end()},
                             value=None, validation='unknown',
                             explanation='Catégorie mentionnée sans valeur déduite.'))
    return dict(indicators=indicators, category_mentions=mentions)


# Catalogue provisoire, pas une liste des logiciels effectivement installés.
# Les sources sont des références officielles; elles ne sont pas consultées à l'exécution.
CATALOG = (
    ('dig', 'dig', ('domain', 'ip', 'email', 'url'), 'Interrogation DNS et recherche inverse IP', 'Réseau et résolveur autorisés nécessaires; pour e-mail ou URL, extraire et valider le domaine ou hôte.', 'https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility'),
    ('whois', 'whois', ('domain', 'ip'), 'Interrogation WHOIS', 'Connexion à un serveur WHOIS nécessaire.', 'https://www.kali.org/tools/whois/'),
    ('file', 'file', ('file',), 'Identification du type de fichier', 'Lecture du fichier; résultat heuristique.', 'https://www.darwinsys.com/file/'),
    ('exiftool', 'exiftool', ('file',), 'Lecture de métadonnées', 'Lecture du fichier; formats pris en charge variables.', 'https://exiftool.org/'),
    ('tshark', 'tshark', ('file',), 'Lecture et analyse de captures réseau', 'Capture compatible; interprétation dépend des protocoles.', 'https://www.wireshark.org/docs/man-pages/tshark.html'),
    ('strings', 'strings', ('file',), 'Extraction de chaînes imprimables', 'Lecture du fichier; ne constitue pas une analyse complète.', 'https://sourceware.org/binutils/docs/binutils/strings.html'),
    ('curl', 'curl', ('url',), 'Transfert et inspection de ressources URL', 'Une requête vers une URL nécessite généralement le réseau.', 'https://curl.se/docs/manpage.html'),
)


def capabilities_for(kind):
    """Déclarations du catalogue, sans contrôle local ni autorisation d'opération.

    Une association indirecte exige une transformation explicite et validation.
    """
    if kind not in ('domain', 'ip', 'email', 'url', 'file', 'image', 'phone', 'username', 'pseudo', 'hash'):
        raise ValueError('type d’indice inconnu')
    lookup_kind = 'file' if kind == 'image' else kind
    result = []
    for ident, name, types, capability, prerequisites, source in CATALOG:
        if lookup_kind not in types:
            continue
        derived = ident == 'dig' and kind in ('email', 'url')
        result.append(dict(tool_id=ident, indicator_type=kind,
                           capability=capability, prerequisites=prerequisites,
                           documentation=source, capability_status='declared',
                           observation_origin='catalogue provisoire',
                           requires_explicit_transformation=derived,
                           transformation=('extraire et valider le domaine ou hôte' if derived else None),
                           command_compatibility_verified=False))
    return result


# Extraction conservative du numéro; le bandeau public reste inchangé.
_VERSION_NUMBER_PATTERNS = {
    'dig': r'^DiG\s+(\d+(?:\.\d+)+)',
    'whois': r'^(?:Version\s+|whois(?:\s+version)?\s+)(\d+(?:\.\d+)+)',
    'file': r'^file-(\d+(?:\.\d+)+)',
    'exiftool': r'^(\d+(?:\.\d+)+)$',
    'tshark': r'^TShark\s+\(Wireshark\)\s+(\d+(?:\.\d+)+)',
    'strings': r'^(?:GNU strings .*?\s|(?:llvm-)?strings(?:\s+version)?\s+)(\d+(?:\.\d+)+)',
    'curl': r'^curl\s+(\d+(?:\.\d+)+)',
}


def _version_number(ident, banner):
    match = re.match(_VERSION_NUMBER_PATTERNS[ident], banner, re.IGNORECASE)
    if not match:
        return None
    suffix = banner[match.end():]
    if suffix and not (suffix[0] in ' -(' or suffix == '.'):
        return None
    return match.group(1)


def _version_output(path, argument, timeout):
    """Lit au plus 4096 octets; termine le groupe en cas de délai ou de débordement."""
    arguments = list(argument) if isinstance(argument, tuple) else [argument]
    process = subprocess.Popen([path, *arguments], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True)
    deadline = time.monotonic() + timeout
    data = bytearray()
    selector = selectors.DefaultSelector()
    finished = False
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise subprocess.TimeoutExpired(path, timeout)
            chunk = os.read(process.stdout.fileno(), 4097 - len(data))
            if not chunk:
                selector.unregister(process.stdout)
                break
            data.extend(chunk)
            if len(data) > 4096:
                raise ValueError('sortie de version trop volumineuse')
        returncode = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        finished = True
        return returncode, data.decode('utf-8', errors='replace').strip()
    finally:
        if not finished:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        selector.close()
        process.stdout.close()


# Les bandeaux non reconnus restent inconnus; ils ne prouvent pas l'intégrité du binaire.
_VERSION_PATTERNS = {
    'dig': r'DiG\s+\d',
    'whois': r'(?:Version\s+|whois(?:\s+version)?\s+)\d',
    'file': r'file-\d',
    'exiftool': r'\d+(?:\.\d+)+$',
    'tshark': r'TShark\s+\(Wireshark\)\s+\d',
    'strings': r'(?:GNU strings .*\s|(?:llvm-)?strings(?:\s+version)?\s+)\d',
    'curl': r'curl\s+\d',
}


def _known_version(ident, output):
    if not output or '\ufffd' in output:
        return None
    if ident == 'exiftool' and len(output.splitlines()) != 1:
        return None
    line = output.splitlines()[0]
    if len(line) > 300 or any(ord(c) < 32 or ord(c) == 127 for c in line):
        return None
    if not re.match(_VERSION_PATTERNS[ident], line, re.IGNORECASE):
        return None
    return line


def inventory(versions=False, timeout=2.0):
    """PATH uniquement; versions optionnelles par arguments fixes, aucune cible fournie.

    Les exécutables sur PATH sont des programmes locaux de confiance, pas un bac à sable.
    """
    if not 0 < timeout <= 10:
        raise ValueError('timeout doit être dans ]0, 10]')
    result = []
    for ident, executable, types, capability, prerequisites, source in CATALOG:
        path = shutil.which(executable)
        inaccessible = False
        if path is None:
            for directory in os.get_exec_path():
                candidate = os.path.join(directory, executable)
                if os.path.isfile(candidate) and not os.access(candidate, os.X_OK):
                    inaccessible = True
                    break
        item = dict(id=ident, name=executable, installed=bool(path), executable_path=path,
                    real_executable_path=str(Path(path).resolve()) if path else None,
                    detection_origin='PATH (shutil.which)', version=None,
                    version_origin='non demandée' if path and not versions else 'indisponible',
                    capabilities=[capability], indicator_types=list(types), prerequisites=[prerequisites],
                    documentation=source)
        if path and versions and not os.path.isabs(path):
            item['version_origin'] = 'contrôle refusé : chemin exécutable relatif non fiable'
        elif path and versions:
            try:
                code, output = _version_output(path, {'dig': '-v', 'exiftool': ('-config', '', '-ver')}.get(ident, '--version'), timeout)
                banner = _known_version(ident, output) if code == 0 else None
                if banner:
                    item['version'] = banner
                    item['version_origin'] = 'sortie du contrôle local de version'
                else:
                    item['version_origin'] = 'contrôle de version sans résultat exploitable'
            except (OSError, ValueError, subprocess.TimeoutExpired):
                item['version_origin'] = 'contrôle de version échoué ou délai dépassé'
        item['version_number'] = _version_number(ident, item['version']) if item['version'] else None
        if not path:
            item['version_status'] = 'unavailable'
        elif not versions:
            item['version_status'] = 'not_requested'
        elif item['version'] is None or item['version_number'] is None:
            item['version_status'] = 'unknown'
        else:
            item['version_status'] = 'detected'
        item['detection_status'] = ('inaccessible' if inaccessible else 'absent' if not path else
                                    'probe_failed' if versions and item['version_status'] == 'unknown' else 'present')
        item['inaccessible_candidate'] = inaccessible
        item['declared_capabilities'] = list(item['capabilities'])
        item['verified_capabilities'] = []
        item['capabilities_origin'] = 'catalogue provisoire; capacités non vérifiées par inventaire'
        result.append(item)
    return result
