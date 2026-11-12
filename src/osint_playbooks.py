# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : osint_playbooks.py
# Role          : Playbooks et scénarios guidés OSINT pas-à-pas avec approbations
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Moteur de Playbooks guidés pour l'OSINT Team d'UCHAMBUZI (D-037).

Fournit 6 parcours d'investigation structurés, pas à pas, où chaque commande
est préparée de manière bornée, vérifiée contre le catalogue en liste blanche
et soumise à l'approbation humaine explicite [o/N] avant exécution.

Playbooks natifs :
1. Domaine suspect : whois -> dig -> crt.sh (curl) -> subfinder/amass -> whatweb -> archives Wayback
2. Image forensique : sha256 -> exiftool -> mat2 -> indices géolocalisation & horodatage
3. Email / Pseudonyme : holehe/maigret/sherlock -> corrélation -> niveau de certitude
4. Surface d'exposition d'une organisation : theHarvester -> subfinder -> httpx -> trufflehog/gitleaks
5. Renseignement téléphonique : phoneinfoga (sans clé) -> scans et dorks
6. Archives web : waybackurls -> gau -> curl snapshot API

Zéro clé API, zéro compte requis. Traçabilité SHA-256 dans le dossier d'enquête.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import time
import unicodedata
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote, urlsplit

# Validation stricte des entrées pour interdire toute injection de commande
_DOMAIN_PATTERN = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')
_PHONE_PATTERN = re.compile(r'^\+[1-9]\d{6,14}$')
_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]{2,64}$')


class PlaybookError(Exception):
    """Erreur de base du moteur de playbooks OSINT."""


class InvalidTargetError(PlaybookError):
    """Cible fournie non conforme au type attendu par le playbook."""


class MissingToolError(PlaybookError):
    """Outil requis absent du système local et du catalogue."""


@dataclass(frozen=True)
class PlaybookStep:
    """Étape individuelle d'un playbook OSINT."""
    step_number: int
    title: str
    tool_id: str
    activity: str  # "passive" | "active"
    prerequisites: str
    command_template: str
    looking_for: str  # Ce qu'on cherche
    next_pivot: str   # Pivot suivant
    alternative_tool_ids: tuple[str, ...] = ()
    notes: str = ""

    def prepare_argv(self, target: str, **kwargs: Any) -> list[str]:
        """Génère la liste d'arguments sans shell pour exécution sécurisée."""
        value = str(target)
        if not _safe_argument(value):
            raise InvalidTargetError('Cible contenant des caractères de contrôle refusée.')
        if kwargs:
            raise PlaybookError('Paramètres de commande non pris en charge.')
        try:
            return [token.format(target=value, target_encoded=quote(value, safe=''))
                    for token in shlex.split(self.command_template)]
        except (KeyError, ValueError) as err:
            raise PlaybookError(f"Template invalide pour l'étape {self.step_number}.") from err

    def format_command(self, target: str, **kwargs: Any) -> str:
        """Affiche la même argv que l'appelant peut examiner, sans shell implicite."""
        return shlex.join(self.prepare_argv(target, **kwargs))


@dataclass(frozen=True)
class OSINTPlaybook:
    """Définition complète d'un Playbook OSINT guidé."""
    id: str
    slug: str
    title: str
    description: str
    specialty: str
    input_type: str
    steps: tuple[PlaybookStep, ...]

    def get_step(self, step_number: int) -> PlaybookStep | None:
        """Récupère une étape par son numéro ordinal (1-indexed)."""
        for step in self.steps:
            if step.step_number == step_number:
                return step
        return None

    def validate_target(self, target: str) -> bool:
        """Valide la cible selon le type d'entrée requis par le playbook."""
        raw = str(target)
        if not raw or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') for c in raw):
            return False
        if self.input_type == 'domain':
            return bool(_DOMAIN_PATTERN.match(raw))
        elif self.input_type == 'phone':
            return bool(_PHONE_PATTERN.match(raw))
        elif self.input_type == 'email':
            return bool(_EMAIL_PATTERN.match(raw))
        elif self.input_type == 'username':
            return bool(_USERNAME_PATTERN.match(raw))
        elif self.input_type in ('image', 'file'):
            return _safe_argument(raw)
        elif self.input_type == 'url':
            if (not _safe_argument(raw) or any(c.isspace() for c in raw)
                    or not raw.startswith(('http://', 'https://'))):
                return False
            try:
                parts = urlsplit(raw)
                return bool(parts.hostname and not parts.username and not parts.password and parts.port != 0)
            except ValueError:
                return False
        return True


def _safe_argument(value: str) -> bool:
    """Allow ordinary paths/URLs as one argv item; reject control characters."""
    return bool(value and not value.startswith('-')
                and not any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp')
                            for c in value))


# ============================================================================
# 1. Playbook : Domaine suspect
# whois -> dig -> crt.sh (curl) -> subfinder/amass -> whatweb -> archives Wayback
# ============================================================================

PLAYBOOK_DOMAIN = OSINTPlaybook(
    id="domain_investigation",
    slug="domaine",
    title="Domaine suspect",
    description="Qualification méthodique d'un nom de domaine : enregistrement, DNS, certificats, sous-domaines, technologies et archives.",
    specialty="domain",
    input_type="domain",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Enregistrement WHOIS & Registrar",
            tool_id="whois",
            activity="passive",
            prerequisites="Nom de domaine syntaxiquement valide.",
            command_template="whois {target}",
            looking_for="Registrar, date de création/mise à jour/expiration, serveurs de noms (NS), statut DNSSEC, contacts administratifs ou masquage WHOIS privacy.",
            next_pivot="Serveurs de noms autoritaires (NS), adresse du registrant ou plage IP de l'hébergeur.",
            notes="Consultation passive des registres officiels ICANN / TLD.",
        ),
        PlaybookStep(
            step_number=2,
            title="Cartographie DNS complète",
            tool_id="dig",
            activity="passive",
            prerequisites="Résolution DNS opérationnelle.",
            command_template="dig {target} ANY +noall +answer",
            looking_for="Enregistrements DNS principaux (A, AAAA, MX, TXT/SPF/DMARC, NS, SOA).",
            next_pivot="Adresses IP des serveurs cibles, passerelles de messagerie (MX) et sous-domaines mentionnés.",
            notes="dig interroge les résolveurs sans solliciter le serveur web de la cible.",
        ),
        PlaybookStep(
            step_number=3,
            title="Certificats SSL/TLS & Transparence (crt.sh)",
            tool_id="curl",
            activity="passive",
            prerequisites="Accès réseau HTTPS vers le journal public crt.sh.",
            command_template='curl -s "https://crt.sh/?q=%25.{target}&output=json"',
            looking_for="Historique exhaustif des certificats SSL/TLS émis, domaines SAN (Subject Alternative Names), sous-domaines historiques et actifs.",
            next_pivot="Liste consolidée des sous-domaines découverts dans les certificats.",
            notes="Lecture passive des journaux de transparence de certificats (CT Logs).",
        ),
        PlaybookStep(
            step_number=4,
            title="Énumération passive des sous-domaines",
            tool_id="subfinder",
            activity="passive",
            prerequisites="Nom de domaine cible.",
            command_template="subfinder -d {target} -silent",
            looking_for="Noms de sous-domaines actifs et résolus sans émission de trafic vers la cible.",
            next_pivot="Sous-domaines critiques exposant des interfaces web, staging, VPN ou API.",
            alternative_tool_ids=("amass",),
            notes="subfinder s'appuie uniquement sur des sources passives ouvertes sans clé.",
        ),
        PlaybookStep(
            step_number=5,
            title="Empreinte technologique HTTP",
            tool_id="whatweb",
            activity="active",
            prerequisites="Service HTTP/HTTPS joignable sur le domaine.",
            command_template="whatweb -a 1 https://{target}",
            looking_for="Serveur web (Apache/Nginx/IIS), CMS (WordPress/Drupal), frameworks, versions logicielles exactes, modules et en-têtes HTTP.",
            next_pivot="Technologies obsolètes, vulnérabilités connues ou points d'entrée d'administration.",
            alternative_tool_ids=("httpx",),
            notes="ATTENTION : action active émettant des requêtes HTTP vers l'hôte cible.",
        ),
        PlaybookStep(
            step_number=6,
            title="Recherche d'URLs archivées sur Wayback Machine",
            tool_id="waybackurls",
            activity="passive",
            prerequisites="Nom de domaine cible.",
            command_template="waybackurls {target}",
            looking_for="Historique des URLs indexées au fil des années, anciens endpoints, paramètres sensibles, fichiers oubliés (.bak, .json, .env).",
            next_pivot="Endpoints d'anciennes API dépréciées ou fichiers sensibles archivés.",
            alternative_tool_ids=("gau",),
            notes="Consultation passive des archives publiques du Web sans contact avec la cible.",
        ),
    ),
)


# ============================================================================
# 2. Playbook : Image forensique
# sha256 -> exiftool -> mat2 -> géolocalisation & horodatage
# ============================================================================

PLAYBOOK_IMAGE = OSINTPlaybook(
    id="image_forensics",
    slug="image",
    title="Analyse d'image forensique",
    description="Inspection d'une image : scellage d'intégrité SHA-256, extraction des métadonnées EXIF, audit de nettoyage et analyse spatio-temporelle.",
    specialty="media",
    input_type="image",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Scellage probatoire SHA-256 de l'image",
            tool_id="exiftool",
            activity="passive",
            prerequisites="Fichier image accessible localement en lecture seule.",
            command_template="sha256sum {target}",
            looking_for="Empreinte cryptographique SHA-256 scellant l'intégrité de la pièce à conviction avant manipulation.",
            next_pivot="Format de fichier précis et extraction des métadonnées du conteneur.",
            notes="Action strictement locale. Calcule l'empreinte probatoire consignée au dossier.",
        ),
        PlaybookStep(
            step_number=2,
            title="Extraction exhaustive des métadonnées EXIF",
            tool_id="exiftool",
            activity="passive",
            prerequisites="Fichier image lisible.",
            command_template="exiftool {target}",
            looking_for="Modèle de l'appareil (Camera Model), constructeur, logiciel de retouche (Photoshop/GIMP), date et heure originale, profils ICC et miniatures.",
            next_pivot="Balises GPS précises et horodatages temporels.",
            notes="Lecture exhaustive sans altération du fichier original.",
        ),
        PlaybookStep(
            step_number=3,
            title="Audit de métadonnées résiduelles et masquage (mat2)",
            tool_id="mat2",
            activity="passive",
            prerequisites="Outil mat2 disponible.",
            command_template="mat2 --show {target}",
            looking_for="Détection des données masquées, champs de métadonnées non standard et éléments résiduels supprimables.",
            next_pivot="Validation de l'authenticité de l'image et détection de retouches.",
            alternative_tool_ids=("exiftool",),
            notes="Inspection passive uniquement (--show) sans modification du fichier source.",
        ),
        PlaybookStep(
            step_number=4,
            title="Extraction des coordonnées GPS et horodatage",
            tool_id="exiftool",
            activity="passive",
            prerequisites="Balises EXIF GPS ou horodatages présents dans l'image.",
            command_template="exiftool -GPSPosition -GPSLatitude -GPSLongitude -DateTimeOriginal -CreateDate {target}",
            looking_for="Latitude et longitude décimales, altitude, horodatage de capture d'origine et fuseau horaire.",
            next_pivot="Localisation géographique sur carte open source (OpenStreetMap) ou chronologie de l'enquête.",
            notes="Isole les informations spatio-temporelles probantes de la prise de vue.",
        ),
    ),
)


# ============================================================================
# 3. Playbook : Email / Pseudonyme
# holehe / maigret / sherlock -> corrélation -> niveau de certitude
# ============================================================================

PLAYBOOK_IDENTITY = OSINTPlaybook(
    id="identity_correlation",
    slug="email-pseudo",
    title="Investigation Email & Pseudonyme",
    description="Vérification de présence de comptes en ligne, énumération multi-plateformes, corrélation d'identités et qualification de certitude.",
    specialty="person",
    input_type="username",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Énumération de comptes et présence de profil",
            tool_id="maigret",
            activity="passive",
            prerequisites="Pseudonyme ou adresse email de la cible.",
            command_template="maigret {target} --timeout 10",
            looking_for="Plateformes où le compte existe (réseaux sociaux, forums, plateformes de développement, blogs), IDs numériques et avatars.",
            next_pivot="Liste des URLs confirmées et comptes actifs pour recoupement croisé.",
            alternative_tool_ids=("sherlock", "holehe"),
            notes="maigret interroge publiquement plus de 2000 sites sans clé API ni authentification.",
        ),
        PlaybookStep(
            step_number=2,
            title="Validation croisée multi-sources (Sherlock)",
            tool_id="sherlock",
            activity="passive",
            prerequisites="Pseudonyme validé lors de l'étape 1.",
            command_template="sherlock {target} --print-found --timeout 10",
            looking_for="Confirmation indépendante des comptes publics actifs et détection de faux positifs.",
            next_pivot="Analyse comparative des photos de profil, biographies et dates d'enregistrement.",
            alternative_tool_ids=("social-analyzer",),
            notes="Double vérification déterministe pour qualifier la certitude de l'attribution.",
        ),
        PlaybookStep(
            step_number=3,
            title="Recoupement de profils avec Social Analyzer",
            tool_id="social-analyzer",
            activity="active",
            prerequisites="Pseudonyme public dans le périmètre autorisé.",
            command_template="social-analyzer --mode fast --output json --username {target}",
            looking_for="Profils publics associés au pseudonyme ; résultats à recouper.",
            next_pivot="Établissement du score de certitude par compte (observé / source unique / recoupé).",
            alternative_tool_ids=("maigret",),
            notes="Pour une adresse email, utiliser séparément /email <adresse> avec une nouvelle approbation.",
        ),
    ),
)


# ============================================================================
# 4. Playbook : Surface d'exposition d'une organisation
# theHarvester -> subfinder -> httpx -> trufflehog / gitleaks
# ============================================================================

PLAYBOOK_ORG_EXPOSURE = OSINTPlaybook(
    id="org_exposure",
    slug="exposition",
    title="Surface d'exposition d'une organisation",
    description="Cartographie passive et active de l'exposition d'une organisation : emails d'employés, sous-domaines, technologies en ligne et détection de secrets.",
    specialty="infra",
    input_type="domain",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Collecte OSINT globale d'organisation (theHarvester)",
            tool_id="theharvester",
            activity="passive",
            prerequisites="Nom de domaine de l'organisation.",
            command_template="theHarvester -d {target} -b duckduckgo,crtsh,certspotter",
            looking_for="Adresses emails d'employés, sous-domaines publics, hôtes de messagerie, employés cités dans les sources ouvertes.",
            next_pivot="Liste des sous-domaines de l'organisation et format des adresses emails d'employés.",
            alternative_tool_ids=("metagoofil",),
            notes="Agrégation passive de sources ouvertes sans solliciter les serveurs de la cible.",
        ),
        PlaybookStep(
            step_number=2,
            title="Cartographie exhaustive des sous-domaines exposés",
            tool_id="subfinder",
            activity="passive",
            prerequisites="Nom de domaine de l'organisation.",
            command_template="subfinder -d {target} -silent",
            looking_for="Sous-domaines sensibles : VPN d'entreprise, portails d'administration, environnements de test/staging, messagerie et webmails.",
            next_pivot="Sous-domaines actifs hébergeant des interfaces web.",
            alternative_tool_ids=("amass", "dnsrecon"),
            notes="Énumération passive rapide et sans empreinte active sur l'organisation.",
        ),
        PlaybookStep(
            step_number=3,
            title="Identification des technologies et serveurs exposés",
            tool_id="httpx",
            activity="active",
            prerequisites="Domaine ou sous-domaines cibles.",
            command_template="httpx -u https://{target} -title -tech-detect -status-code",
            looking_for="Codes HTTP retournés, titres des pages web, serveurs d'application, CMS et composants d'infrastructure exposés.",
            next_pivot="Services d'administration exposés sur Internet et dépôts de code publics associés.",
            alternative_tool_ids=("whatweb",),
            notes="ATTENTION : vérification active avec émission de requêtes HTTP vers les cibles.",
        ),
        PlaybookStep(
            step_number=4,
            title="Recherche de fuites de secrets dans le code public",
            tool_id="trufflehog",
            activity="passive",
            prerequisites="URL d'un dépôt Git public fourni par l'enquêteur.",
            command_template="trufflehog git {target} --only-verified",
            looking_for="Clés API fuitées, tokens d'accès cloud (AWS, GCP, Azure), certificats privés ou mots de passe oubliés dans l'historique Git.",
            next_pivot="Alerte de sécurité d'urgence et procédure de révocation immédiate des identifiants compromis.",
            alternative_tool_ids=("gitleaks",),
            notes="Audit passif de dépôts de code publics sans contact avec le système interne de l'organisation.",
        ),
    ),
)


# ============================================================================
# 5. Playbook : Renseignement téléphonique
# phoneinfoga (sans clé) -> scans et dorks
# ============================================================================

PLAYBOOK_PHONE = OSINTPlaybook(
    id="phone_intel",
    slug="telephone",
    title="Renseignement téléphonique",
    description="Investigation sur un numéro de téléphone international : validation du format E.164, identification de l'opérateur et détection de traces web.",
    specialty="person",
    input_type="phone",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Analyse du numéro et identification de l'opérateur",
            tool_id="phoneinfoga",
            activity="passive",
            prerequisites="Numéro au format international E.164 (ex: +33601020304).",
            command_template="phoneinfoga scan -n {target} --env-file /dev/null -D numverify -D googlecse -D ovh -D googlesearch",
            looking_for="Pays d'origine, indicatif régional, opérateur de télécommunication (Carrier), type de ligne (mobile, fixe, VoIP) et validité.",
            next_pivot="Dénomination de l'opérateur et recherches ciblées en sources ouvertes.",
            notes="Analyse locale du format et du pays ; scanners réseau et scanners à clé désactivés.",
        ),
        PlaybookStep(
            step_number=2,
            title="Recherche passive de mentions publiques et dorks",
            tool_id="phoneinfoga",
            activity="passive",
            prerequisites="Numéro E.164 validé à l'étape 1.",
            command_template="phoneinfoga scan -n {target} --env-file /dev/null -D numverify -D googlecse -D ovh -D local",
            looking_for="Mentions publiques du numéro dans des annuaires en ligne, profils de réseaux sociaux, forums, annonces de vente ou registres d'entreprises.",
            next_pivot="Rapprochement avec une identité physique, organisationnelle ou profil en ligne.",
            notes="Génération de requêtes Google dorks passives sans interaction avec la ligne téléphonique.",
        ),
    ),
)


# ============================================================================
# 6. Playbook : Archives web
# waybackurls -> gau -> curl snapshot API
# ============================================================================

PLAYBOOK_WEB_ARCHIVES = OSINTPlaybook(
    id="web_archives",
    slug="archives",
    title="Exploration d'archives web",
    description="Exploration chronologique de la mémoire du Web : extraction d'URLs historiques, recoupement multi-archives et extraction d'instantanés.",
    specialty="web_archive",
    input_type="domain",
    steps=(
        PlaybookStep(
            step_number=1,
            title="Extraction des URLs archivées sur Wayback Machine",
            tool_id="waybackurls",
            activity="passive",
            prerequisites="Nom de domaine ou URL cible.",
            command_template="waybackurls {target}",
            looking_for="Index complet des pages, ressources et paramètres enregistrés par la Wayback Machine au fil des années.",
            next_pivot="Endpoints d'anciennes versions, documents téléchargeables (.pdf, .docx) et fichiers sensibles (.sql, .env, .json).",
            alternative_tool_ids=("gau",),
            notes="Extraction passive auprès de l'Internet Archive sans contacter le serveur cible.",
        ),
        PlaybookStep(
            step_number=2,
            title="Recoupement multi-fournisseurs d'archives (gau)",
            tool_id="gau",
            activity="passive",
            prerequisites="Nom de domaine cible.",
            command_template="gau --providers wayback,commoncrawl {target}",
            looking_for="Corrélation croisée des URLs archivées via Wayback Machine et Common Crawl pour maximiser l'exhaustivité de l'historique.",
            next_pivot="Fichiers de sauvegarde ou endpoints d'administration disparus de la version actuelle.",
            alternative_tool_ids=("waybackurls",),
            notes="Agrégation de plusieurs dépôts mondiaux d'archives publiques du Web.",
        ),
        PlaybookStep(
            step_number=3,
            title="Disponibilité et métadonnées du snapshot le plus récent",
            tool_id="curl",
            activity="passive",
            prerequisites="URL spécifique identifiée dans les archives.",
            command_template='curl -s "https://archive.org/wayback/available?url={target_encoded}"',
            looking_for="Date et horodatage de l'instantané le plus proche, statut HTTP archivé et lien d'accès direct au contenu conservé.",
            next_pivot="Consultation et scellage probatoire du contenu archivé de la page.",
            notes="Interrogation de l'API JSON officielle de la Wayback Machine.",
        ),
    ),
)


# ============================================================================
# Registre des 6 Playbooks officiels UCHAMBUZI
# ============================================================================

BUILTIN_PLAYBOOKS: tuple[OSINTPlaybook, ...] = (
    PLAYBOOK_DOMAIN,
    PLAYBOOK_IMAGE,
    PLAYBOOK_IDENTITY,
    PLAYBOOK_ORG_EXPOSURE,
    PLAYBOOK_PHONE,
    PLAYBOOK_WEB_ARCHIVES,
)

PLAYBOOK_INDEX: dict[str, OSINTPlaybook] = {}
for _pb in BUILTIN_PLAYBOOKS:
    PLAYBOOK_INDEX[_pb.id] = _pb
    PLAYBOOK_INDEX[_pb.slug] = _pb
    PLAYBOOK_INDEX[_pb.title.lower()] = _pb


def list_playbooks() -> tuple[OSINTPlaybook, ...]:
    """Retourne la liste ordonnée des 6 playbooks OSINT officiels."""
    return BUILTIN_PLAYBOOKS


def get_playbook(key: str) -> OSINTPlaybook | None:
    """Résout un playbook par son identifiant, slug ou titre."""
    norm = str(key).strip().lower()
    return PLAYBOOK_INDEX.get(norm)


# ============================================================================
# Vérification d'Outils et de Disponibilité
# ============================================================================

def check_step_tool_status(step: PlaybookStep, catalog_tools: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Vérifie la présence locale de l'outil principal de l'étape et de ses alternatives.

    Retourne un dictionnaire structuré :
    - tool_id : identifiant de l'outil principal
    - installed : booléen indiquant si l'outil principal est présent sur le PATH
    - executable_path : chemin absolu de l'outil ou None
    - install_command : suggestion pour installer l'outil via UCHAMBUZI
    - available_alternative : nom d'une alternative installée ou None
    """
    main_tool = step.tool_id
    main_path = shutil.which(main_tool)

    installed = main_path is not None
    install_hint = f"/tools install {main_tool}"

    available_alt = None
    for alt in step.alternative_tool_ids:
        if shutil.which(alt):
            available_alt = alt
            break

    return {
        "tool_id": main_tool,
        "installed": installed,
        "executable_path": main_path,
        "install_command": install_hint,
        "available_alternative": available_alt,
        "activity": step.activity,
    }


def format_step_banner(step: PlaybookStep, target: str) -> dict[str, Any]:
    """Génère la fiche descriptive d'une étape pour l'affichage Rich et l'approbation."""
    tool_status = check_step_tool_status(step)
    prepared_cmd = step.format_command(target)

    # Libellé du niveau passif / actif avec couleur correspondante
    if step.activity == "passive":
        activity_label = "PASSIF (lecture seule / sources ouvertes)"
        activity_badge = "[bold green][PASSIF][/bold green]"
    else:
        activity_label = "ACTIF (émission de requêtes réseau vers la cible)"
        activity_badge = "[bold yellow][ACTIF][/bold yellow]"

    warning = ""
    if not tool_status["installed"]:
        if tool_status["available_alternative"]:
            warning = (
                f"Outil '{step.tool_id}' non installé. Alternative disponible : "
                f"'{tool_status['available_alternative']}'. "
                f"Pour installer l'outil principal : {tool_status['install_command']}"
            )
        else:
            warning = (
                f"Outil '{step.tool_id}' non installé. "
                f"Pour l'installer : {tool_status['install_command']}"
            )

    return {
        "step_number": step.step_number,
        "title": step.title,
        "tool_id": step.tool_id,
        "activity": step.activity,
        "activity_label": activity_label,
        "activity_badge": activity_badge,
        "prerequisites": step.prerequisites,
        "command": prepared_cmd,
        "argv": step.prepare_argv(target),
        "looking_for": step.looking_for,
        "next_pivot": step.next_pivot,
        "installed": tool_status["installed"],
        "available_alternative": tool_status["available_alternative"],
        "warning": warning,
    }


# ============================================================================
# Session de suivi d'exécution d'un Playbook pas-à-pas
# ============================================================================

@dataclass
class PlaybookSession:
    """Session d'exécution active d'un playbook guidé."""
    playbook: OSINTPlaybook
    target: str
    current_step_number: int = 1
    completed_steps: list[dict[str, Any]] = field(default_factory=list)
    results: list[dict[str, Any]] = field(default_factory=list)
    status: str = "in_progress"  # "in_progress" | "completed" | "aborted"
    case_id: str | None = None

    def current_step(self) -> PlaybookStep | None:
        """Retourne l'étape courante à exécuter."""
        if self.status != "in_progress":
            return None
        return self.playbook.get_step(self.current_step_number)

    def advance_step(self) -> PlaybookStep | None:
        """Passe à l'étape suivante après exécution ou saut."""
        self.current_step_number += 1
        next_step = self.current_step()
        if next_step is None:
            self.status = "completed"
        return next_step

    def record_step_result(
        self,
        step: PlaybookStep,
        command: str,
        approved: bool,
        output: str = "",
        exit_code: int = 0,
        duration: float = 0.0,
        case_manager: Any = None,
    ) -> dict[str, Any]:
        """Consigne le résultat de l'étape et trace dans le CaseManager avec SHA-256."""
        record = {
            "step_number": step.step_number,
            "step_title": step.title,
            "tool_id": step.tool_id,
            "activity": step.activity,
            "command": command,
            "approved": approved,
            "output_preview": output[:500] if output else "",
            "exit_code": exit_code,
            "duration": duration,
            "timestamp": time.time(),
        }
        self.completed_steps.append(record)

        # Inscription dans le dossier d'enquête actif
        if case_manager is not None and getattr(case_manager, 'active_case_id', None) and approved:
            case_manager.record_execution({
                "playbook_id": self.playbook.id,
                "step_number": step.step_number,
                "step_title": step.title,
                "tool": step.tool_id,
                "activity": step.activity,
                "command": command,
                "stdout": output if exit_code == 0 else "",
                "stderr": output if exit_code != 0 else "",
                "exit_code": exit_code,
                "duration": duration,
            })

        return record
