# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_scenarios.py
# Role          : Catalogue et registre des 24 scénarios professionnels Focus
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Moteur de scénarios professionnels pour UCHAMBUZI Focus.

Dote l'assistant d'un catalogue de 24 scénarios spécialisés répartis sur les
huit modes professionnels existants (Assist, Trace, Intel, Defend, Assess,
Validate, Engineer, Coordinate).

Chaque scénario structure la méthode, les questions préalables, les paramètres,
les catégories d'outils, les limites forensiques et les critères de résultat.
Le scénario reste facultatif : la conversation libre dans chaque mode est
toujours permise.

Ce module respecte D-025 (Python standard exclusif) et les contrats v1 Focus.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Sequence

from focus_contracts import Scenario
from focus_modes import (
    MODE_ASSESS,
    MODE_ASSIST,
    MODE_COORDINATE,
    MODE_DEFEND,
    MODE_ENGINEER,
    MODE_INTEL,
    MODE_TRACE,
    MODE_VALIDATE,
    ORDERED_BUILTIN_MODE_IDS,
)

# ============================================================================
# Identifiants stables des 24 scénarios obligatoires
# ============================================================================

# ASSIST
SCENARIO_TECHNICAL_GUIDANCE = 'technical_guidance'
SCENARIO_TROUBLESHOOTING = 'troubleshooting'
SCENARIO_SCRIPT_ASSISTANCE = 'script_assistance'

# TRACE
SCENARIO_DIGITAL_EVIDENCE = 'digital_evidence'
SCENARIO_TIMELINE_ANALYSIS = 'timeline_analysis'
SCENARIO_MEMORY_FORENSICS = 'memory_forensics'

# INTEL
SCENARIO_INFRASTRUCTURE_INTELLIGENCE = 'infrastructure_intelligence'
SCENARIO_INDICATOR_ENRICHMENT = 'indicator_enrichment'
SCENARIO_THREAT_RESEARCH = 'threat_research'

# DEFEND
SCENARIO_INCIDENT_TRIAGE = 'incident_triage'
SCENARIO_LOG_INVESTIGATION = 'log_investigation'
SCENARIO_THREAT_HUNTING = 'threat_hunting'

# ASSESS
SCENARIO_SECURITY_ASSESSMENT = 'security_assessment'
SCENARIO_VULNERABILITY_REVIEW = 'vulnerability_review'
SCENARIO_AUTHORIZED_PENETRATION_TEST = 'authorized_penetration_test'

# VALIDATE
SCENARIO_ATTCK_MAPPING = 'attck_mapping'
SCENARIO_DETECTION_VALIDATION = 'detection_validation'
SCENARIO_PURPLE_TEAM_EXERCISE = 'purple_team_exercise'

# ENGINEER
SCENARIO_SYSTEM_HARDENING = 'system_hardening'
SCENARIO_NETWORK_SECURITY = 'network_security'
SCENARIO_SECURITY_AUTOMATION = 'security_automation'

# COORDINATE
SCENARIO_EXERCISE_PLANNING = 'exercise_planning'
SCENARIO_RULES_OF_ENGAGEMENT = 'rules_of_engagement'
SCENARIO_AFTER_ACTION_REVIEW = 'after_action_review'

# ============================================================================
# Identifiants stables des Playbooks OSINT (D-037)
# ============================================================================
SCENARIO_DOMAIN_INVESTIGATION = 'domain_investigation'
SCENARIO_IMAGE_FORENSICS = 'image_forensics'
SCENARIO_IDENTITY_CORRELATION = 'identity_correlation'
SCENARIO_ORG_EXPOSURE = 'org_exposure'
SCENARIO_PHONE_INTEL = 'phone_intel'
SCENARIO_WEB_ARCHIVES = 'web_archives'

ORDERED_OSINT_PLAYBOOK_IDS: tuple[str, ...] = (
    SCENARIO_DOMAIN_INVESTIGATION,
    SCENARIO_IMAGE_FORENSICS,
    SCENARIO_IDENTITY_CORRELATION,
    SCENARIO_ORG_EXPOSURE,
    SCENARIO_PHONE_INTEL,
    SCENARIO_WEB_ARCHIVES,
)

# Table de compatibilité et masquage D-037 : seule l'OSINT Team (intel) est active
ACTIVE_SCENARIO_MODES: frozenset[str] = frozenset((MODE_INTEL,))
WITHDRAWN_SCENARIO_MODES: frozenset[str] = frozenset((
    MODE_ASSIST,
    MODE_TRACE,
    MODE_DEFEND,
    MODE_ASSESS,
    MODE_VALIDATE,
    MODE_ENGINEER,
    MODE_COORDINATE,
))

ORDERED_BUILTIN_SCENARIO_IDS: tuple[str, ...] = (
    # Assist (1..3)
    SCENARIO_TECHNICAL_GUIDANCE,
    SCENARIO_TROUBLESHOOTING,
    SCENARIO_SCRIPT_ASSISTANCE,
    # Trace (4..6)
    SCENARIO_DIGITAL_EVIDENCE,
    SCENARIO_TIMELINE_ANALYSIS,
    SCENARIO_MEMORY_FORENSICS,
    # Intel (7..9)
    SCENARIO_INFRASTRUCTURE_INTELLIGENCE,
    SCENARIO_INDICATOR_ENRICHMENT,
    SCENARIO_THREAT_RESEARCH,
    # Defend (10..12)
    SCENARIO_INCIDENT_TRIAGE,
    SCENARIO_LOG_INVESTIGATION,
    SCENARIO_THREAT_HUNTING,
    # Assess (13..15)
    SCENARIO_SECURITY_ASSESSMENT,
    SCENARIO_VULNERABILITY_REVIEW,
    SCENARIO_AUTHORIZED_PENETRATION_TEST,
    # Validate (16..18)
    SCENARIO_ATTCK_MAPPING,
    SCENARIO_DETECTION_VALIDATION,
    SCENARIO_PURPLE_TEAM_EXERCISE,
    # Engineer (19..21)
    SCENARIO_SYSTEM_HARDENING,
    SCENARIO_NETWORK_SECURITY,
    SCENARIO_SECURITY_AUTOMATION,
    # Coordinate (22..24)
    SCENARIO_EXERCISE_PLANNING,
    SCENARIO_RULES_OF_ENGAGEMENT,
    SCENARIO_AFTER_ACTION_REVIEW,
)

# Pattern de validation strict des identifiants de scénarios (slug)
_SCENARIO_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]{1,47}$')

# Correspondance des alias historiques de la Mission 06 vers les identifiants canoniques
SCENARIO_ALIASES: dict[str, str] = {
    # Assist
    'general_troubleshooting': SCENARIO_TROUBLESHOOTING,
    'tool_discovery': SCENARIO_TECHNICAL_GUIDANCE,
    'network_basics': SCENARIO_TECHNICAL_GUIDANCE,
    # Trace
    'forensic_timeline': SCENARIO_TIMELINE_ANALYSIS,
    'memory_dump_analysis': SCENARIO_MEMORY_FORENSICS,
    'disk_triage': SCENARIO_DIGITAL_EVIDENCE,
    'malware_unpacking': SCENARIO_DIGITAL_EVIDENCE,
    # Intel
    'infrastructure_pivot': SCENARIO_INFRASTRUCTURE_INTELLIGENCE,
    'threat_actor_profiling': SCENARIO_THREAT_RESEARCH,
    'osint_investigation': SCENARIO_INFRASTRUCTURE_INTELLIGENCE,
    # Defend
    'incident_response': SCENARIO_INCIDENT_TRIAGE,
    'log_threat_hunting': SCENARIO_LOG_INVESTIGATION,
    'alert_triage': SCENARIO_INCIDENT_TRIAGE,
    'compromise_containment': SCENARIO_INCIDENT_TRIAGE,
    # Assess
    'authorized_pentest': SCENARIO_AUTHORIZED_PENETRATION_TEST,
    'vulnerability_audit': SCENARIO_VULNERABILITY_REVIEW,
    'surface_mapping': SCENARIO_SECURITY_ASSESSMENT,
    'remediation_review': SCENARIO_VULNERABILITY_REVIEW,
    # Validate
    'detection_gap_analysis': SCENARIO_DETECTION_VALIDATION,
    'mitre_coverage_mapping': SCENARIO_ATTCK_MAPPING,
    'atomic_test_run': SCENARIO_DETECTION_VALIDATION,
    # Engineer
    'firewall_deployment': SCENARIO_NETWORK_SECURITY,
    'secure_baseline_audit': SCENARIO_SYSTEM_HARDENING,
    'service_resilience': SCENARIO_SECURITY_AUTOMATION,
    # Coordinate
    'crisis_simulation': SCENARIO_EXERCISE_PLANNING,
    'white_team_governance': SCENARIO_RULES_OF_ENGAGEMENT,
    'retex_after_action': SCENARIO_AFTER_ACTION_REVIEW,
    'risk_mitigation_plan': SCENARIO_RULES_OF_ENGAGEMENT,
    # OSINT Playbooks (D-037)
    'domaine': SCENARIO_DOMAIN_INVESTIGATION,
    'domaine_suspect': SCENARIO_DOMAIN_INVESTIGATION,
    'domain': SCENARIO_DOMAIN_INVESTIGATION,
    'image': SCENARIO_IMAGE_FORENSICS,
    'image_forensique': SCENARIO_IMAGE_FORENSICS,
    'photo': SCENARIO_IMAGE_FORENSICS,
    'email_pseudo': SCENARIO_IDENTITY_CORRELATION,
    'email-pseudo': SCENARIO_IDENTITY_CORRELATION,
    'identite': SCENARIO_IDENTITY_CORRELATION,
    'pseudo': SCENARIO_IDENTITY_CORRELATION,
    'exposition': SCENARIO_ORG_EXPOSURE,
    'surface_exposition': SCENARIO_ORG_EXPOSURE,
    'organisation': SCENARIO_ORG_EXPOSURE,
    'telephone': SCENARIO_PHONE_INTEL,
    'phone': SCENARIO_PHONE_INTEL,
    'archives': SCENARIO_WEB_ARCHIVES,
    'archives_web': SCENARIO_WEB_ARCHIVES,
    'wayback': SCENARIO_WEB_ARCHIVES,
}

# ============================================================================
# Exceptions du moteur de scénarios
# ============================================================================

class ScenarioError(Exception):
    """Erreur de base du moteur de scénarios."""


class UnknownScenarioError(ScenarioError):
    """Signale un identifiant de scénario non reconnu."""


class IncompatibleScenarioError(ScenarioError):
    """Signale une incompatibilité entre un scénario et le mode actif."""


class InvalidScenarioDefinitionError(ScenarioError):
    """Signale une définition de scénario invalide ou non conforme."""


class MissingParameterError(ScenarioError):
    """Signale l'absence d'un paramètre obligatoire pour le scénario."""


class InvalidParameterError(ScenarioError):
    """Signale un paramètre non conforme au schéma attendu."""


# ============================================================================
# Modèles de données pour les paramètres et métadonnées
# ============================================================================

@dataclass(frozen=True)
class ScenarioParameter:
    """Définition d'un paramètre de scénario avec contraintes et validation."""
    name: str
    description: str
    param_type: str = 'string'  # 'string', 'integer', 'boolean', 'choice', 'path', 'ip_or_domain', 'list'
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] | None = None

    def validate_value(self, raw_value: Any) -> Any:
        """Valide et convertit la valeur selon le type spécifié."""
        if raw_value is None:
            if self.required and self.default is None:
                raise MissingParameterError(
                    f"Le paramètre obligatoire '{self.name}' est manquant pour ce scénario."
                )
            return self.default

        if self.param_type == 'string':
            val_str = str(raw_value).strip()
            if self.required and not val_str:
                raise MissingParameterError(
                    f"Le paramètre '{self.name}' ne peut pas être une chaîne vide."
                )
            return val_str

        elif self.param_type == 'integer':
            try:
                return int(raw_value)
            except (ValueError, TypeError):
                raise InvalidParameterError(
                    f"Valeur invalide pour '{self.name}' : entier attendu, reçu '{raw_value}'."
                )

        elif self.param_type == 'boolean':
            if isinstance(raw_value, bool):
                return raw_value
            norm = str(raw_value).strip().lower()
            if norm in ('true', '1', 'yes', 'oui', 'vrai', 'y'):
                return True
            if norm in ('false', '0', 'no', 'non', 'faux', 'n'):
                return False
            raise InvalidParameterError(
                f"Valeur booléenne invalide pour '{self.name}' : reçu '{raw_value}'."
            )

        elif self.param_type == 'choice':
            val_str = str(raw_value).strip()
            if self.choices and val_str not in self.choices:
                raise InvalidParameterError(
                    f"Option invalide pour '{self.name}' : '{val_str}'. "
                    f"Choix possibles : {', '.join(self.choices)}"
                )
            return val_str

        elif self.param_type == 'path':
            path_str = str(raw_value).strip()
            if self.required and not path_str:
                raise MissingParameterError(f"Chemin de fichier requis pour '{self.name}'.")
            return path_str

        elif self.param_type == 'ip_or_domain':
            raw_str = str(raw_value).strip()
            if not raw_str and not self.required:
                return ''
            try:
                ipaddress.ip_address(raw_str)
                return raw_str
            except ValueError:
                # Vérifier syntaxe minimale nom de domaine
                if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', raw_str):
                    return raw_str
                raise InvalidParameterError(
                    f"Valeur '{raw_value}' invalide pour '{self.name}' (IP ou domaine attendu)."
                )

        elif self.param_type == 'list':
            if isinstance(raw_value, (list, tuple)):
                return tuple(str(x).strip() for x in raw_value if str(x).strip())
            if isinstance(raw_value, str):
                return tuple(x.strip() for x in raw_value.split(',') if x.strip())
            raise InvalidParameterError(
                f"Liste ou séquence attendue pour '{self.name}', reçu : {type(raw_value).__name__}."
            )

        return raw_value


@dataclass(frozen=True)
class ScenarioTUIMetadata:
    """Métadonnées de présentation du scénario pour l'interface TUI."""
    index: int
    badge: str
    glyph: str
    shortcut_hint: str
    category: str


# ============================================================================
# Définition complète d'un scénario professionnel
# ============================================================================

@dataclass(frozen=True)
class FocusScenario:
    """Modèle structuré et complet d'un scénario professionnel Focus."""
    id: str
    name: str
    description: str
    compatible_modes: tuple[str, ...]
    objective: str
    required_information: tuple[str, ...]
    parameters: tuple[ScenarioParameter, ...]
    methodology: tuple[str, ...]
    ai_instructions: str
    expected_response_structure: tuple[str, ...]
    recommended_tool_categories: tuple[str, ...]
    recommended_tools: tuple[str, ...]
    prerequisites: tuple[str, ...]
    limits_and_precautions: tuple[str, ...]
    completion_criteria: tuple[str, ...]
    tui_metadata: ScenarioTUIMetadata
    custom: bool = False

    def to_contract_scenario(self) -> Scenario:
        """Exporte le scénario sous forme conforme au contrat Scenario v1."""
        return Scenario(
            id=self.id,
            title=self.name,
            description=self.description,
        )

    def validate_parameters(self, raw_params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Valide et normalise les paramètres fournis contre le schéma."""
        raw = dict(raw_params or {})
        validated: dict[str, Any] = {}

        # Vérifier chaque paramètre défini
        for param in self.parameters:
            val = raw.get(param.name)
            validated[param.name] = param.validate_value(val)

        # Copier les paramètres additionnels non déclarés comme chaînes nettoyées
        declared_names = {p.name for p in self.parameters}
        for k, v in raw.items():
            if k not in declared_names and isinstance(k, str) and k.isidentifier():
                if isinstance(v, (str, int, float, bool)):
                    validated[k] = v

        return validated


@dataclass(frozen=True)
class ScenarioTransitionEvent:
    """Événement émis lors du changement, sélection ou désélection d'un scénario."""
    previous_scenario_id: str | None
    new_scenario_id: str | None
    mode_id: str
    parameters: Mapping[str, Any]
    timestamp: float
    tui_metadata: ScenarioTUIMetadata | None
    reason: str = ''
    animation_hints: Mapping[str, Any] = field(default_factory=dict)


# ============================================================================
# Les 24 scénarios professionnels natifs
# ============================================================================

BUILTIN_SCENARIOS: dict[str, FocusScenario] = {

    # ------------------------------------------------------------------------
    # 01 - ASSIST : 1. Technical Guidance
    # ------------------------------------------------------------------------
    SCENARIO_TECHNICAL_GUIDANCE: FocusScenario(
        id=SCENARIO_TECHNICAL_GUIDANCE,
        name='Technical Guidance',
        description="Expliquer une technologie, une commande ou un fonctionnement technique sous Linux/Kali.",
        compatible_modes=(MODE_ASSIST,),
        objective="Fournir une explication technique pédagogique, décomposée et documentée d'un composant, protocole ou commande.",
        required_information=(
            "Nom de la commande, de la technologie ou du composant à expliquer.",
            "Niveau de détail ou aspect technique recherché (syntaxe, architecture, sécurité).",
        ),
        parameters=(
            ScenarioParameter('technology', "Technologie ou commande concernée (ex: iptables, volatility, btrfs)", 'string', False, ''),
            ScenarioParameter('expertise_level', "Niveau d'approfondissement souhaité", 'choice', False, 'intermediate', ('beginner', 'intermediate', 'advanced')),
            ScenarioParameter('focus_aspect', "Aspect technique prioritaire", 'choice', False, 'syntax', ('overview', 'syntax', 'internals', 'security')),
        ),
        methodology=(
            "1. Identification de la commande ou technologie cible et contexte d'usage.",
            "2. Explication pédagogique des mécanismes internes et protocoles sous-jacents.",
            "3. Détail de la syntaxe, des arguments critiques et des options recommandées.",
            "4. Présentation d'exemples concrets annotés avec leurs cas d'usage typiques.",
            "5. Formulation des bonnes pratiques, pièges courants et commandes de vérification.",
        ),
        ai_instructions=(
            "Tu guides l'utilisateur dans la compréhension approfondie d'une technologie ou commande. "
            "Décompose systématiquement les drapeaux et options mentionnés. Explique la logique sous-jacente "
            "sans raccourci. Propose des commandes de test sans risque (lecture seule, --help, dry-run). "
            "Si la technologie dispose d'une page man officielle, cite-la comme référence."
        ),
        expected_response_structure=(
            "[Synthèse conceptuelle]",
            "[Fonctionnement technique & Architecture]",
            "[Syntaxe et options clés]",
            "[Exemples concrets annotés]",
            "[Bonnes pratiques & Vérifications non destructives]",
        ),
        recommended_tool_categories=('documentation_tools', 'command_reference', 'system_diagnostics'),
        recommended_tools=('man', 'info', 'which', 'apropos', 'tldr'),
        prerequisites=("Accès terminal local standard ; aucune modification de configuration requise.",),
        limits_and_precautions=("Fournir des explications factuelles basées sur les documentations officielles sans inventer d'options.",),
        completion_criteria=("La technologie est expliquée clairement avec syntaxe explicite et exemples reproductibles.",),
        tui_metadata=ScenarioTUIMetadata(1, '[GUIDANCE]', '📘', 'Alt+G', 'assist'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 01 - ASSIST : 2. Troubleshooting
    # ------------------------------------------------------------------------
    SCENARIO_TROUBLESHOOTING: FocusScenario(
        id=SCENARIO_TROUBLESHOOTING,
        name='Troubleshooting',
        description="Diagnostiquer un problème Linux, réseau, logiciel ou système de manière méthodique.",
        compatible_modes=(MODE_ASSIST,),
        objective="Isoler la cause racine d'un dysfonctionnement système ou réseau sans perturber l'environnement.",
        required_information=(
            "Symptôme observé ou message d'erreur textuel exact.",
            "Composant, service ou interface réseau affecté.",
            "Changements récents ou actions ayant précédé la panne.",
        ),
        parameters=(
            ScenarioParameter('component', "Service, interface ou brique en panne", 'string', False, ''),
            ScenarioParameter('symptom', "Description du symptôme ou message d'erreur", 'string', False, ''),
            ScenarioParameter('urgency', "Niveau de criticité du dysfonctionnement", 'choice', False, 'medium', ('low', 'medium', 'high', 'critical')),
        ),
        methodology=(
            "1. Caractérisation précise du dysfonctionnement et des messages d'erreur.",
            "2. Collecte non destructive de télémétrie système (journalctl, ss, dmesg, ip).",
            "3. Formulation et hiérarchisation des hypothèses de cause racine.",
            "4. Vérification progressive des hypothèses par commandes passives.",
            "5. Proposition d'un plan de remédiation gradué, documenté et réversible.",
        ),
        ai_instructions=(
            "Tu guides le diagnostic de pannes sous Linux/Kali. Priorise toujours la collecte d'indices "
            "passifs (journaux, état des sockets, statut des services) avant de suggérer une modification. "
            "Chaque hypothèse doit être assortie d'une commande d'observation précise. Ne jamais proposer "
            "de redémarrage brutal ou de suppression de paquets sans diagnostic avéré."
        ),
        expected_response_structure=(
            "[Qualification du problème & Symptômes]",
            "[Télémétrie & Observations passives]",
            "[Hypothèses de cause racine]",
            "[Commandes de vérification ciblées]",
            "[Plan de remédiation gradué]",
        ),
        recommended_tool_categories=('system_diagnostics', 'network_discovery', 'log_analysis'),
        recommended_tools=('journalctl', 'dmesg', 'ss', 'ip', 'systemctl', 'lsof'),
        prerequisites=("Disposer d'un accès terminal pour exécuter des commandes de diagnostic en lecture seule.",),
        limits_and_precautions=("Ne proposer aucune écriture destructrice ou réinitialisation avant confirmation du diagnostic.",),
        completion_criteria=("La cause probable est identifiée et étayée par des traces factuelles de diagnostic.",),
        tui_metadata=ScenarioTUIMetadata(2, '[TROUBLE]', '🔧', 'Alt+T', 'assist'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 01 - ASSIST : 3. Script Assistance
    # ------------------------------------------------------------------------
    SCENARIO_SCRIPT_ASSISTANCE: FocusScenario(
        id=SCENARIO_SCRIPT_ASSISTANCE,
        name='Script Assistance',
        description="Préparer, expliquer et vérifier un script technique d'automatisation ou d'administration.",
        compatible_modes=(MODE_ASSIST,),
        objective="Concevoir ou auditer des scripts Shell/Python sécurisés, commentés, robustes et idempotents.",
        required_information=(
            "Objectif fonctionnel du script et langage cible (Bash, sh, Python).",
            "Environnement d'exécution (version système, privilèges requis).",
            "Fichiers d'entrée et format de sortie attendu.",
        ),
        parameters=(
            ScenarioParameter('language', "Langage du script", 'choice', False, 'bash', ('bash', 'sh', 'python')),
            ScenarioParameter('purpose', "Finalité du script", 'string', False, ''),
            ScenarioParameter('safety_checks', "Exiger gestion stricte des erreurs et idempotence", 'boolean', False, True),
        ),
        methodology=(
            "1. Définition des entrées, sorties et comportement attendu du script.",
            "2. Structuration du flux d'exécution et gestion stricte des erreurs (set -euo pipefail).",
            "3. Implémentation du code sécurisé sans injection de commandes ni effets de bord.",
            "4. Revue d'idempotence, de portabilité et de robustesse syntaxique.",
            "5. Préparation des tests de validation et vérification par shellcheck/pylint.",
        ),
        ai_instructions=(
            "Tu rédiges et vérifies des scripts techniques. Si le langage est Bash/sh, inclus obligatoirement "
            "'set -euo pipefail' et protège rigoureusement toutes les variables avec des guillemets doubles. "
            "Commente chaque fonction. Signale les dépendances requises et prévois un mode simulation (--dry-run). "
            "Bannis formellement les commandes 'eval' et les expansions non sécurisées."
        ),
        expected_response_structure=(
            "[Spécification & Flux d'exécution]",
            "[Code source commenté et sécurisé]",
            "[Gestion des erreurs & Idempotence]",
            "[Revue de sécurité & Bonnes pratiques]",
            "[Procédure de test non destructive]",
        ),
        recommended_tool_categories=('script_tools', 'package_management', 'command_reference'),
        recommended_tools=('bash', 'python3', 'shellcheck', 'shfmt'),
        prerequisites=("Interpréteur Bash ou Python disponible localement.",),
        limits_and_precautions=("Tester impérativement le script sur un jeu de données factice avant tout usage opérationnel.",),
        completion_criteria=("Le script est complet, syntaxiquement vérifié et intègre la gestion sécurisée des erreurs.",),
        tui_metadata=ScenarioTUIMetadata(3, '[SCRIPT]', '📜', 'Alt+S', 'assist'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 02 - TRACE : 4. Digital Evidence
    # ------------------------------------------------------------------------
    SCENARIO_DIGITAL_EVIDENCE: FocusScenario(
        id=SCENARIO_DIGITAL_EVIDENCE,
        name='Digital Evidence',
        description="Examiner et documenter des éléments de preuve numérique en préservant l'intégrité.",
        compatible_modes=(MODE_TRACE,),
        objective="Consigner les métadonnées, calculer les empreintes SHA-256 et établir la chaîne de conservation des artefacts.",
        required_information=(
            "Chemin du fichier image bit-à-bit ou artefact à examiner.",
            "Empreinte SHA-256 de référence si disponible.",
            "Description du support d'origine et numéro de scellé.",
        ),
        parameters=(
            ScenarioParameter('evidence_type', "Type d'élément de preuve", 'choice', False, 'disk_image', ('disk_image', 'memory_dump', 'file', 'packet_capture', 'log_file')),
            ScenarioParameter('hash_algorithm', "Algorithme d'empreinte", 'choice', False, 'sha256', ('sha256', 'sha512', 'md5_legacy')),
            ScenarioParameter('custody_reference', "Numéro de scellé ou référence de dossier", 'string', False, ''),
        ),
        methodology=(
            "1. Consignation de la chaîne de conservation (origine, numéro de scellé, opérateur).",
            "2. Calcul et vérification d'empreinte cryptographique (SHA-256) sur copie de travail brute.",
            "3. Montage passif en lecture seule stricte (ro, loop, noexec, nosuid).",
            "4. Inventaire des artefacts et métadonnées de bas niveau (inodes, MACB, hachages).",
            "5. Rédaction du journal de manipulation opposable et rapport d'intégrité.",
        ),
        ai_instructions=(
            "Tu conduis l'analyse forensique de preuves numériques. Rappelle systématiquement qu'on ne travaille "
            "JAMAIS sur l'original mais sur copie bit-à-bit vérifiée. Exige le calcul préalable et contradictoire "
            "du hash SHA-256. Formule des commandes garantissant un accès strictement passif (ro, noatime). "
            "Distingue rigoureusement les métadonnées de fichier constatées de toute interprétation humaine."
        ),
        expected_response_structure=(
            "[Chaîne de conservation & Scellés]",
            "[Empreintes cryptographiques (SHA-256)]",
            "[Procédure de montage passif en lecture seule]",
            "[Inventaire des artefacts extraits]",
            "[Journal d'intégrité forensique & Réserves]",
        ),
        recommended_tool_categories=('disk_forensics', 'metadata_extraction', 'file_carving'),
        recommended_tools=('sha256sum', 'dc3dd', 'ewf-tools', 'sleuthkit', 'losetup'),
        prerequisites=("Disposer d'une copie bit-à-bit (RAW/dd ou E01) hébergée sur support sain.",),
        limits_and_precautions=("Toute commande d'écriture ou de réparation de système de fichiers invalide la preuve.",),
        completion_criteria=("L'intégrité est prouvée par empreinte cryptographique et la chaîne de conservation est formalisée.",),
        tui_metadata=ScenarioTUIMetadata(4, '[EVIDENCE]', '📁', 'Alt+E', 'trace'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 02 - TRACE : 5. Timeline Analysis
    # ------------------------------------------------------------------------
    SCENARIO_TIMELINE_ANALYSIS: FocusScenario(
        id=SCENARIO_TIMELINE_ANALYSIS,
        name='Timeline Analysis',
        description="Reconstruire une chronologie à partir d'artefacts, systèmes de fichiers et journaux.",
        compatible_modes=(MODE_TRACE,),
        objective="Corréler temporellement en UTC les événements MACB (mtime, atime, ctime, btime) et traces systèmes.",
        required_information=(
            "Système de fichiers extrait ou image forensique montée en lecture seule.",
            "Plage temporelle suspecte identifiée ou présumée.",
            "Fuseau horaire d'origine de la machine examinée.",
        ),
        parameters=(
            ScenarioParameter('time_range', "Plage temporelle suspecte (ex: 2026-11-01T00:00:00Z à 2026-11-02T12:00:00Z)", 'string', False, ''),
            ScenarioParameter('timezone', "Fuseau horaire de normalisation", 'choice', False, 'UTC', ('UTC', 'Europe/Paris', 'America/New_York', 'Asia/Tokyo')),
            ScenarioParameter('sources', "Sources d'artefacts à corréler", 'string', False, 'mft,fls,journalctl'),
        ),
        methodology=(
            "1. Délimitation de la fenêtre temporelle suspecte et normalisation en UTC.",
            "2. Extraction des timestamps de fichiers (mtime, atime, ctime, btime / crtime).",
            "3. Intégration des journaux d'événements système et applicatifs.",
            "4. Tri chronologique, détection des anomalies temporelles (timestomping) et corrélations.",
            "5. Synthèse chronologique des événements pivots de l'incident.",
        ),
        ai_instructions=(
            "Tu guides la reconstruction de chronologie forensique (timeline). Tous les horodatages "
            "doivent impérativement être exprimés en UTC avec indication de la source exacte. Signale toute "
            "anomalie temporelle évidente (ctime antérieur à mtime, atime figé, microsecondes nulles) comme "
            "indice possible d'antidatage (timestomping). Sépare les faits chronologiques bruts de tes déductions."
        ),
        expected_response_structure=(
            "[Cadrage temporel UTC & Sources]",
            "[Extraction méthodologique des timestamps (MACB)]",
            "[Chronologie unifiée des événements pivots]",
            "[Anomalies temporelles & Suspicions d'antidatage]",
            "[Synthèse séquentielle des faits établis]",
        ),
        recommended_tool_categories=('timeline_generation', 'disk_forensics', 'metadata_extraction'),
        recommended_tools=('fls', 'mactime', 'log2timeline', 'plaso', 'sleuthkit'),
        prerequisites=("Corps d'artefacts ou système de fichiers accessible en lecture seule.",),
        limits_and_precautions=("Les horodatages atime/mtime peuvent avoir été manipulés par l'attaquant.",),
        completion_criteria=("La chronologie unifiée en UTC est établie avec sources identifiées pour chaque entrée.",),
        tui_metadata=ScenarioTUIMetadata(5, '[TIMELINE]', '⏱', 'Alt+L', 'trace'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 02 - TRACE : 6. Memory Forensics
    # ------------------------------------------------------------------------
    SCENARIO_MEMORY_FORENSICS: FocusScenario(
        id=SCENARIO_MEMORY_FORENSICS,
        name='Memory Forensics',
        description="Préparer et accompagner l'analyse d'une capture mémoire volatile (RAM).",
        compatible_modes=(MODE_TRACE,),
        objective="Identifier les processus masqués, connexions réseau injectées et artefacts volatils sans altération.",
        required_information=(
            "Chemin du dump mémoire brut (raw, dmp, vmem, lime).",
            "Système d'exploitation cible présumé (Linux, Windows, version de noyau).",
            "Indicateurs ou PID suspects déjà repérés.",
        ),
        parameters=(
            ScenarioParameter('profile_or_os', "Système d'exploitation présumé (ex: Linux 6.1, Windows 11)", 'string', False, ''),
            ScenarioParameter('focus_artifact', "Artefact mémoire prioritaire", 'choice', False, 'all', ('processes', 'network_sockets', 'injected_code', 'kernel_modules', 'all')),
            ScenarioParameter('suspicious_pid', "PID suspect éventuel", 'integer', False, None),
        ),
        methodology=(
            "1. Identification de l'architecture de la mémoire et sélection des symboles/profils.",
            "2. Énumération de l'arbre des processus (pslist, pstree, psscan) et détection de masquage (DKOM).",
            "3. Analyse des connexions réseau établies lors de la capture (netscan).",
            "4. Détection d'injections de code, DLLs non mappées et hooks noyau (malfind).",
            "5. Extraction des binaires et modules suspects pour qualification statique.",
        ),
        ai_instructions=(
            "Tu guides l'analyse de mémoire vive avec Volatility 3 ou outils similaires. Recommande d'abord "
            "la vérification du profil/symboles. Compare systématiquement la liste active des processus "
            "avec le scan brut de structures de données pour détecter le démasquage DKOM. Précise les "
            "drapeaux de commande Volatility et recommande l'extraction sécurisée (dump) vers un dossier isolé."
        ),
        expected_response_structure=(
            "[Caractéristiques du dump RAM & Symboles]",
            "[Analyse de l'arbre des processus & Masquages]",
            "[Télémétrie réseau volatile (sockets actifs)]",
            "[Détection d'injections de code & Mémoire RWX]",
            "[Artefacts extraits & Pistes d'investigation]",
        ),
        recommended_tool_categories=('memory_forensics', 'malware_triage', 'metadata_extraction'),
        recommended_tools=('volatility3', 'volatility', 'bulk_extractor', 'strings'),
        prerequisites=("Fichier de capture mémoire brute intact avec empreinte SHA-256 calculée.",),
        limits_and_precautions=("L'absence d'artefact en mémoire ne prouve pas l'absence d'activité antérieure au dump.",),
        completion_criteria=("Les processus, connexions et régions injectées sont répertoriés avec leurs adresses mémoire.",),
        tui_metadata=ScenarioTUIMetadata(6, '[MEMORY]', '🧠', 'Alt+M', 'trace'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 03 - INTEL : 7. Infrastructure Intelligence
    # ------------------------------------------------------------------------
    SCENARIO_INFRASTRUCTURE_INTELLIGENCE: FocusScenario(
        id=SCENARIO_INFRASTRUCTURE_INTELLIGENCE,
        name='Infrastructure Intelligence',
        description="Examiner une IP, un domaine, un ASN ou une infrastructure réseau suspecte.",
        compatible_modes=(MODE_INTEL,),
        objective="Cartographier passivement les points de présence, ASN, serveurs DNS et sous-domaines d'une infrastructure.",
        required_information=(
            "Indicateur d'infrastructure cible (adresse IP, nom de domaine, plage CIDR, ASN).",
            "Type d'investigation souhaité (strictement passive ou semi-passive).",
        ),
        parameters=(
            ScenarioParameter('target', "IP, domaine, CIDR ou ASN cible", 'string', False, ''),
            ScenarioParameter('mode_query', "Type d'interrogation", 'choice', False, 'passive_only', ('passive_only', 'semi_passive')),
            ScenarioParameter('max_depth', "Profondeur de découverte", 'integer', False, 1),
        ),
        methodology=(
            "1. Définition du périmètre de l'infrastructure cible (IP, CIDR, FQDN, ASN).",
            "2. Résolution DNS passive et historique (Passive DNS, CT logs).",
            "3. Cartographie des relations BGP/ASN, hébergeurs et géolocalisation d'infrastructure.",
            "4. Découverte passive des sous-domaines et certificats TLS associés.",
            "5. Consolidation de la topologie adverse et identification des points de pivot.",
        ),
        ai_instructions=(
            "Tu mènes une reconnaissance d'infrastructure cyber. Privilégie strictement les méthodes "
            "passives (registres WHOIS publics, bases ASN, journaux de transparence de certificats). "
            "Avertis explicitement l'utilisateur avant toute commande envoyant des paquets directement à la cible. "
            "Rappelle que l'adresse IP d'un serveur partagé ou CDN ne caractérise pas à elle seule l'attaquant."
        ),
        expected_response_structure=(
            "[Périmètre ciblé & Typologie de l'infrastructure]",
            "[Analyse DNS passif & Historique d'hébergement]",
            "[Routage BGP, ASN & Hébergeurs identifiés]",
            "[Certificats TLS & Découverte passive de sous-domaines]",
            "[Synthèse topologique & Points de pivot]",
        ),
        recommended_tool_categories=('passive_dns', 'whois_lookup', 'asn_enrichment', 'certificate_transparency'),
        recommended_tools=('whois', 'dig', 'amass', 'sublist3r', 'curl', 'jq'),
        prerequisites=("Connexion Internet locale ou miroirs de bases CTI configurés.",),
        limits_and_precautions=("Les résolutions directes alertent les serveurs DNS autoritaires adverses.",),
        completion_criteria=("La cartographie passive de l'infrastructure est documentée sans contact direct avec la cible.",),
        tui_metadata=ScenarioTUIMetadata(7, '[INFRA]', '🌐', 'Alt+I', 'intel'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 03 - INTEL : 8. Indicator Enrichment
    # ------------------------------------------------------------------------
    SCENARIO_INDICATOR_ENRICHMENT: FocusScenario(
        id=SCENARIO_INDICATOR_ENRICHMENT,
        name='Indicator Enrichment',
        description="Contextualiser des indicateurs (IoC) et vérifier leurs sources en sources ouvertes.",
        compatible_modes=(MODE_INTEL,),
        objective="Enrichir les hashs, domaines et IP par recoupement CTI en évaluant la fraîcheur et la fiabilité.",
        required_information=(
            "Valeur brute de l'indicateur (hash SHA-256, domaine, adresse IP, URL dé-armoricée).",
            "Contexte d'observation initial (alerte IDS, journal proxy, pièce jointe).",
        ),
        parameters=(
            ScenarioParameter('indicator_type', "Type d'indicateur", 'choice', False, 'ip', ('ip', 'domain', 'hash', 'url', 'asn')),
            ScenarioParameter('reputation_sources', "Sources ou flux CTI à prioriser", 'string', False, 'circl,abuseipdb,virustotal_passive'),
            ScenarioParameter('confidence_threshold', "Seuil de confiance minimum", 'choice', False, 'medium', ('low', 'medium', 'high')),
        ),
        methodology=(
            "1. Normalisation et classification typologique des indicateurs (hash, IP, domaine, URL).",
            "2. Interrogation des bases de réputation et flux CTI disponibles.",
            "3. Évaluation de la fraîcheur, de la fiabilité des sources et de la criticité.",
            "4. Identification des campagnes, malwares ou acteurs associés (ATT&CK).",
            "5. Synthèse de réputation avec indice de confiance explicité.",
        ),
        ai_instructions=(
            "Tu enrichis des indicateurs de compromission (IoC). Dé-arme systématiquement les URLs "
            "et domaines malveillants (remplace 'http' par 'hxxp' et les points par '[.]'). Sépare "
            "strictement les faits observés des scores de réputation tiers. Précise l'âge des premières "
            "et dernières observations. Indique explicitement le niveau de confiance (faible, moyen, élevé)."
        ),
        expected_response_structure=(
            "[Qualification & Normalisation de l'IoC (dé-armé)]",
            "[Recoupement CTI & Historique de réputation]",
            "[Évaluation de la fiabilité & Fraîcheur des données]",
            "[Rattachement aux campagnes / Malwares connus]",
            "[Indice de confiance & Recommandations de blocage]",
        ),
        recommended_tool_categories=('threat_feeds', 'whois_lookup', 'passive_dns', 'metadata_extraction'),
        recommended_tools=('curl', 'jq', 'whois', 'dig', 'sha256sum'),
        prerequisites=("Disposer des indicateurs bruts sous forme textuelle sécurisée.",),
        limits_and_precautions=("Un indicateur vierge de signalement récent peut être un domaine tout juste enregistré (DGA/bulletproof).",),
        completion_criteria=("L'indicateur est contextualisé avec sources, date et niveau de confiance explicité.",),
        tui_metadata=ScenarioTUIMetadata(8, '[ENRICH]', '🔍', 'Alt+R', 'intel'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 03 - INTEL : 9. Threat Research
    # ------------------------------------------------------------------------
    SCENARIO_THREAT_RESEARCH: FocusScenario(
        id=SCENARIO_THREAT_RESEARCH,
        name='Threat Research',
        description="Étudier des menaces, infrastructures, hypothèses et informations de renseignement.",
        compatible_modes=(MODE_INTEL,),
        objective="Caractériser les modes opératoires et campagnes de menace avec la taxonomie Diamond / MITRE.",
        required_information=(
            "Nom du groupe de menace, malware ou campagne ciblée.",
            "Secteur d'activité ou zone géographique concernée.",
            "Question de renseignement spécifique formulée.",
        ),
        parameters=(
            ScenarioParameter('threat_actor_or_campaign', "Groupe de menace ou campagne", 'string', False, ''),
            ScenarioParameter('framework', "Modèle d'analyse", 'choice', False, 'mitre_attck', ('mitre_attck', 'diamond_model', 'cyber_kill_chain')),
            ScenarioParameter('timeframe', "Période couverte par la recherche", 'string', False, 'derniers_12_mois'),
        ),
        methodology=(
            "1. Cadrage du groupe de menace, du secteur ciblé ou de la campagne.",
            "2. Collecte de rapports publics, avis CERT et analyses de sécurité reconnues.",
            "3. Cartographie des tactiques, techniques et procédures selon MITRE ATT&CK.",
            "4. Modélisation par le Diamond Model (Adversaire, Capacité, Infrastructure, Victime).",
            "5. Rédaction de la note d'analyse des menaces avec lacunes de renseignement signalées.",
        ),
        ai_instructions=(
            "Tu mènes une recherche stratégique et tactique de Threat Intelligence. Adopte un ton analytique "
            "rigoureux conforme au standard de renseignement. Distingue l'attribution revendiquée, l'attribution "
            "probable et la simple analogie d'outillage. Identifie les TTPs récurrents selon MITRE ATT&CK. "
            "Conclus toujours en listant les lacunes de renseignement (ce qui n'est pas vérifié)."
        ),
        expected_response_structure=(
            "[Profil de la menace & Contexte géopolitique/économique]",
            "[Cartographie des TTPs (MITRE ATT&CK)]",
            "[Modélisation Diamond Model (Adversaire, Capacité, Infrastructure, Victime)]",
            "[Capacités techniques & Vecteurs d'accès privilégiés]",
            "[Incertitudes & Lacunes de renseignement documentées]",
        ),
        recommended_tool_categories=('threat_feeds', 'osint_reconnaissance', 'command_reference'),
        recommended_tools=('curl', 'jq', 'grep', 'python3'),
        prerequisites=("Accès aux bases de connaissances ouvertes et rapports CERT.",),
        limits_and_precautions=("L'attribution publique peut résulter d'opérations sous faux drapeau (false flag).",),
        completion_criteria=("La menace est structurée selon un référentiel reconnu avec mention explicite des incertitudes.",),
        tui_metadata=ScenarioTUIMetadata(9, '[RESEARCH]', '🎯', 'Alt+H', 'intel'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 04 - DEFEND : 10. Incident Triage
    # ------------------------------------------------------------------------
    SCENARIO_INCIDENT_TRIAGE: FocusScenario(
        id=SCENARIO_INCIDENT_TRIAGE,
        name='Incident Triage',
        description="Qualifier un incident et définir les premières vérifications prioritaires.",
        compatible_modes=(MODE_DEFEND,),
        objective="Évaluer la sévérité, l'impact opérationnel et les mesures de confinement immédiates réversibles.",
        required_information=(
            "Description de l'événement déclencheur ou de l'alerte SOC.",
            "Actifs concernés (serveurs, postes, équipements réseau, données).",
            "Indices de compromission actifs constatés.",
        ),
        parameters=(
            ScenarioParameter('severity', "Niveau de sévérité initial estimé", 'choice', False, 'p2_high', ('p1_critical', 'p2_high', 'p3_medium', 'p4_low')),
            ScenarioParameter('incident_type', "Type d'incident présumé", 'choice', False, 'unknown', ('ransomware', 'data_exfiltration', 'unauthorized_access', 'dos', 'unknown')),
            ScenarioParameter('affected_scope', "Périmètre d'impact supposé", 'string', False, ''),
        ),
        methodology=(
            "1. Réception et qualification initiale de l'alerte (gravité, portée, criticité des actifs).",
            "2. Vérification de la véracité de l'alerte pour éliminer les faux positifs évidents.",
            "3. Évaluation du rayon d'impact et du stade d'avancement de l'intrusion.",
            "4. Définition des mesures immédiates de confinement conservatoire et réversible.",
            "5. Orientation de la réponse : escalade, ouverture d'enquête forensique ou clôture.",
        ),
        ai_instructions=(
            "Tu qualifies un incident de sécurité en première ligne SOC. Priorise la préservation de la preuve "
            "volatile avant tout arrêt machine. Propose des règles de confinement immédiates (isolation réseau logique, "
            "règles de filtrage temporaire) en explicitant leurs impacts sur la continuité d'activité. "
            "Définis clairement le seuil de bascule vers le déclenchement d'une cellule de crise."
        ),
        expected_response_structure=(
            "[Matrice de criticité & Évaluation de la gravité]",
            "[Levée de doute & Élimination des faux positifs]",
            "[Rayon d'impact & Actifs critiques menacés]",
            "[Mesures conservatoires d'urgence (réversibles)]",
            "[Plan d'escalade & Prochaines actions prioritaires]",
        ),
        recommended_tool_categories=('containment_tools', 'system_diagnostics', 'network_monitoring'),
        recommended_tools=('journalctl', 'ss', 'iptables', 'nftables', 'lsof'),
        prerequisites=("Visibilité sur la télémétrie locale ou les alertes transmises.",),
        limits_and_precautions=("Ne pas couper brutalement l'alimentation électrique d'une machine compromise (perte de la RAM).",),
        completion_criteria=("L'alerte est qualifiée avec matrice de sévérité et plan de confinement immédiat.",),
        tui_metadata=ScenarioTUIMetadata(10, '[TRIAGE]', '🚨', 'Alt+A', 'defend'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 04 - DEFEND : 11. Log Investigation
    # ------------------------------------------------------------------------
    SCENARIO_LOG_INVESTIGATION: FocusScenario(
        id=SCENARIO_LOG_INVESTIGATION,
        name='Log Investigation',
        description="Analyser des journaux et rechercher des événements suspects ou anomalies.",
        compatible_modes=(MODE_DEFEND,),
        objective="Interroger méthodiquement les journaux (auth, syslog, web, proxy) par requêtes ciblées reproductibles.",
        required_information=(
            "Fichiers de journaux à analyser ou source SIEM.",
            "Fenêtre temporelle d'intérêt.",
            "Motifs ou comportements suspects recherchés.",
        ),
        parameters=(
            ScenarioParameter('log_format', "Format des journaux", 'choice', False, 'syslog', ('syslog', 'journalctl', 'apache_nginx', 'zeek', 'suricata', 'winevt')),
            ScenarioParameter('search_pattern', "Motif de recherche initial", 'string', False, ''),
            ScenarioParameter('time_window', "Fenêtre temporelle", 'string', False, ''),
        ),
        methodology=(
            "1. Identification des sources de journaux pertinentes et vérification de complétude.",
            "2. Formulation de requêtes ciblées filtrant le bruit opérationnel.",
            "3. Recherche des motifs d'attaque connus (injections, échecs d'authentification massifs, exécution anormale).",
            "4. Reconstitution de la chaîne d'événements observée dans les journaux.",
            "5. Synthèse des découvertes et formulation de règles de détection d'après les traces.",
        ),
        ai_instructions=(
            "Tu analyses des journaux de sécurité. Rédige des commandes de filtrage efficaces (grep, awk, jq, journalctl) "
            "optimisées pour ne pas saturer la mémoire. Explique précisément chaque filtre d'expression régulière. "
            "Mets en évidence les anomalies de volume, les connexions hors horaires et les cascades d'erreurs 401/403/500."
        ),
        expected_response_structure=(
            "[Sources de journaux & Période d'analyse]",
            "[Requêtes de filtrage ciblées (commandes prêtes)]",
            "[Anomalies & Événements suspects isolés]",
            "[Chronologie des motifs observés]",
            "[Recommandations de détection durable]",
        ),
        recommended_tool_categories=('log_analysis', 'siem_hunting', 'host_telemetry'),
        recommended_tools=('grep', 'awk', 'journalctl', 'sed', 'jq', 'zgrep'),
        prerequisites=("Accès en lecture aux fichiers de logs ou flux journalctl.",),
        limits_and_precautions=("Les attaquants peuvent tenter d'effacer ou falsifier les journaux locaux non déportés.",),
        completion_criteria=("Les lignes suspectes sont isolées avec horodatage, source et commandes d'extraction associées.",),
        tui_metadata=ScenarioTUIMetadata(11, '[LOGS]', '📜', 'Alt+O', 'defend'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 04 - DEFEND : 12. Threat Hunting
    # ------------------------------------------------------------------------
    SCENARIO_THREAT_HUNTING: FocusScenario(
        id=SCENARIO_THREAT_HUNTING,
        name='Threat Hunting',
        description="Construire et vérifier des hypothèses de détection proactive sur le SIEM ou l'hôte.",
        compatible_modes=(MODE_DEFEND,),
        objective="Formuler des hypothèses de traque basées sur des TTPs et vérifier la présence d'activités furtives.",
        required_information=(
            "Technique TTP ciblée (ex: exécution via lolbins, persistance cron, dll hijacking).",
            "Sources de télémétrie disponibles (auditd, sysmon, logs proxy, flux réseau).",
            "Périmètre des machines inspectées.",
        ),
        parameters=(
            ScenarioParameter('hypothesis', "Hypothèse de traque formulée", 'string', False, ''),
            ScenarioParameter('data_source', "Source télémétrique principale", 'choice', False, 'process_creation', ('process_creation', 'network_connection', 'file_modification', 'authentication')),
            ScenarioParameter('environment', "Environnement cible", 'choice', False, 'linux', ('linux', 'windows', 'cloud', 'hybrid')),
        ),
        methodology=(
            "1. Formulation d'une hypothèse de traque basée sur des TTPs ATT&CK ou de la CTI récente.",
            "2. Détermination de la télémétrie requise (processus, connexions réseau, persistance).",
            "3. Exécution de requêtes de recherche étendues avec élimination méthodique des faux positifs.",
            "4. Analyse des comportements suspects détectés et validation d'anomalies.",
            "5. Conversion des requêtes de traque validées en règles de détection permanentes (Sigma/YARA).",
        ),
        ai_instructions=(
            "Tu mènes une traque proactive (Threat Hunting). Pars d'une hypothèse formulée selon le schéma : "
            "'Si un attaquant utilise [Technique], nous devrions observer [Traces télémétriques]'. "
            "Fournis des requêtes d'investigation concrètes et explique comment éliminer le bruit des processus "
            "légitimes d'administration. Propose la conversion du résultat en règle de détection Sigma."
        ),
        expected_response_structure=(
            "[Hypothèse de traque & Technique ciblée]",
            "[Télémétrie requise & Sources de données]",
            "[Requêtes d'investigation & Filtrage du bruit légitime]",
            "[Résultats attendus & Critères d'alerte]",
            "[Règle de détection pérenne (Sigma / YARA)]",
        ),
        recommended_tool_categories=('siem_hunting', 'log_analysis', 'host_telemetry'),
        recommended_tools=('yara', 'auditd', 'journalctl', 'ss', 'find'),
        prerequisites=("Disposer de télémétrie système ou journaux centralisés exploitables.",),
        limits_and_precautions=("L'absence de résultat valide l'hypothèse sur le périmètre sans prouver l'absence totale de menace.",),
        completion_criteria=("L'hypothèse est testée et une règle de détection pérenne est formulée pour le SOC.",),
        tui_metadata=ScenarioTUIMetadata(12, '[HUNTING]', '🏹', 'Alt+U', 'defend'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 05 - ASSESS : 13. Security Assessment
    # ------------------------------------------------------------------------
    SCENARIO_SECURITY_ASSESSMENT: FocusScenario(
        id=SCENARIO_SECURITY_ASSESSMENT,
        name='Security Assessment',
        description="Préparer un audit technique avec périmètre et objectifs.",
        compatible_modes=(MODE_ASSESS,),
        objective="Définir la cartographie de surface d'attaque et le plan d'audit dans les limites du mandat.",
        required_information=(
            "Périmètre formellement autorisé (adresses IP, sous-réseaux, noms de domaine).",
            "Référence de l'autorisation écrite ou du bon de commande d'audit.",
            "Systèmes ou plages exclus de toute sollicitation.",
        ),
        parameters=(
            ScenarioParameter('scope', "Périmètre autorisé", 'string', False, ''),
            ScenarioParameter('assessment_type', "Type d'évaluation", 'choice', False, 'internal_audit', ('internal_audit', 'external_surface', 'configuration_review')),
            ScenarioParameter('authorization_id', "Référence de l'autorisation d'audit", 'string', False, ''),
        ),
        methodology=(
            "1. Vérification de l'autorisation d'audit écrite et validation des limites du périmètre.",
            "2. Définition de la méthodologie d'évaluation (boîte noire, grise, blanche).",
            "3. Reconnaissance passive puis active non intrusive des services exposés.",
            "4. Analyse des écarts de configuration par rapport aux référentiels (ANSSI, CIS).",
            "5. Rédaction du rapport d'audit avec plan d'action hiérarchisé selon le risque.",
        ),
        ai_instructions=(
            "Tu prépares et cadres un audit technique de sécurité. Vérifie scrupuleusement que l'utilisateur "
            "rappelle le périmètre autorisé. Formule des commandes de cartographie mesurées (nmap avec cadencement "
            "adapté -T3) pour éviter toute perturbation de service. Ne suggère aucune action intrusive ou non autorisée."
        ),
        expected_response_structure=(
            "[Vérification du périmètre & Mandat d'audit]",
            "[Méthodologie d'évaluation & Référentiels]",
            "[Cartographie des services & Surface d'attaque]",
            "[Analyse des écarts de configuration]",
            "[Plan d'action de remédiation priorisé]",
        ),
        recommended_tool_categories=('network_scanning', 'vulnerability_scanning', 'compliance_audit'),
        recommended_tools=('nmap', 'nikto', 'sslyze', 'curl', 'testssl'),
        prerequisites=("Autorisation écrite formelle du propriétaire des systèmes audités.",),
        limits_and_precautions=("Tout test hors du périmètre convenu constitue une infraction légale.",),
        completion_criteria=("Le plan d'audit et la cartographie sont établis dans le respect strict du mandat.",),
        tui_metadata=ScenarioTUIMetadata(13, '[ASSESS]', '📊', 'Alt+K', 'assess'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 05 - ASSESS : 14. Vulnerability Review
    # ------------------------------------------------------------------------
    SCENARIO_VULNERABILITY_REVIEW: FocusScenario(
        id=SCENARIO_VULNERABILITY_REVIEW,
        name='Vulnerability Review',
        description="Examiner, qualifier et prioriser des vulnérabilités.",
        compatible_modes=(MODE_ASSESS,),
        objective="Analyser l'exploitabilité réelle, le score CVSS contextualisé et les mesures d'atténuation.",
        required_information=(
            "Identifiant de vulnérabilité (CVE, CWE) ou composant logiciel affecté.",
            "Version exacte du composant installé localement.",
            "Exposition du service (local uniquement, réseau interne, Internet).",
        ),
        parameters=(
            ScenarioParameter('target_software', "Logiciel ou service audité", 'string', False, ''),
            ScenarioParameter('cve_id', "Identifiant CVE éventuel", 'string', False, ''),
            ScenarioParameter('min_cvss', "Seuil CVSS minimal", 'choice', False, 'medium', ('none', 'medium', 'high', 'critical')),
        ),
        methodology=(
            "1. Identification des vulnérabilités (identifiants CVE/CWE) et versions logicielles affectées.",
            "2. Évaluation de l'exploitabilité réelle en contexte (vecteur d'accès, privilèges requis, interaction).",
            "3. Calcul du score CVSS environnemental et contextualisé.",
            "4. Analyse des correctifs disponibles et des mesures de contournement palliatives.",
            "5. Établissement de la feuille de route de remédiation priorisée.",
        ),
        ai_instructions=(
            "Tu qualifies des vulnérabilités de sécurité. Ne te limite pas au score CVSS de base : évalue "
            "l'exploitabilité réelle dans le contexte décrit (présence de pare-feu, authentification requise, "
            "version des dépendances). Propose systématiquement une mesure de contournement immédiate "
            "(désactivation de fonctionnalité, règle de filtrage) avant même l'application du patch officiel."
        ),
        expected_response_structure=(
            "[Fiche de vulnérabilité (CVE/CWE & Versions)]",
            "[Analyse d'exploitabilité réelle en contexte]",
            "[Score CVSS contextualisé & Vecteur d'attaque]",
            "[Mesures de contournement palliatives immédiates]",
            "[Plan d'application des correctifs officiels]",
        ),
        recommended_tool_categories=('vulnerability_scanning', 'cve_database', 'command_reference'),
        recommended_tools=('cve-search', 'searchsploit', 'curl', 'jq'),
        prerequisites=("Connaissance de la version exacte du composant logiciel analysé.",),
        limits_and_precautions=("L'existence d'un exploit public ne garantit pas son fonctionnement sur la cible.",),
        completion_criteria=("La vulnérabilité est qualifiée avec exploitabilité contextuelle et plan de remédiation.",),
        tui_metadata=ScenarioTUIMetadata(14, '[VULN]', '🛡', 'Alt+V', 'assess'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 05 - ASSESS : 15. Authorized Penetration Test
    # ------------------------------------------------------------------------
    SCENARIO_AUTHORIZED_PENETRATION_TEST: FocusScenario(
        id=SCENARIO_AUTHORIZED_PENETRATION_TEST,
        name='Authorized Penetration Test',
        description="Organiser des tests d'intrusion dans un périmètre expressément autorisé.",
        compatible_modes=(MODE_ASSESS,),
        objective="Établir les vecteurs d'intrusion contrôlés en respectant les règles d'engagement et la sécurité des données.",
        required_information=(
            "Mandat écrit signé d'autorisation de test d'intrusion.",
            "Périmètre IP/domaines et plages d'adresses formellement exclues.",
            "Fenêtre horaire et contact d'urgence pour arrêt immédiat.",
        ),
        parameters=(
            ScenarioParameter('mandate_ref', "Référence du mandat d'intrusion signé", 'string', False, ''),
            ScenarioParameter('test_mode', "Mode de test", 'choice', False, 'gray_box', ('black_box', 'gray_box', 'white_box')),
            ScenarioParameter('out_of_bounds', "Systèmes et plages formellement exclus", 'string', False, ''),
        ),
        methodology=(
            "1. Validation formelle du mandat d'intrusion, de la fenêtre d'action et des cibles interdites.",
            "2. Découverte et cartographie de la surface d'attaque externe et interne autorisée.",
            "3. Analyse des vecteurs d'entrée potentiels sans déni de service.",
            "4. Validation contrôlée des faiblesses avec preuve de concept (PoC) minimale non destructive.",
            "5. Consignation des chemins d'accès compromis et recommandations de renforcement.",
        ),
        ai_instructions=(
            "Tu accompagnes un test d'intrusion autorisé (pentest). Exige la référence au mandat écrit. "
            "Bannis formellement toute commande susceptible de provoquer un déni de service ou d'altérer "
            "les données de production. Propose uniquement des preuves de concept (PoC) minimales démontrant "
            "la vulnérabilité sans persistance offensive non convenue. Documente chaque étape pour le rapport."
        ),
        expected_response_structure=(
            "[Vérification du mandat & Règles d'engagement (RoE)]",
            "[Reconnaissance de surface d'attaque autorisée]",
            "[Vecteurs d'intrusion testés & Preuves de concept (PoC)]",
            "[Impact démontré & Risque résiduel]",
            "[Recommandations immédiates de durcissement]",
        ),
        recommended_tool_categories=('web_security_tools', 'network_scanning', 'exploitation_tools'),
        recommended_tools=('nmap', 'hydra', 'sqlmap', 'curl', 'wfuzz'),
        prerequisites=("Mandat signé d'autorisation de test d'intrusion et contact d'urgence validé.",),
        limits_and_precautions=("Tout test en dehors de la fenêtre horaire ou du périmètre signé est illégal.",),
        completion_criteria=("Les vecteurs d'intrusion sont validés de manière contrôlée avec rapport documenté.",),
        tui_metadata=ScenarioTUIMetadata(15, '[PENTEST]', '⚡', 'Alt+P', 'assess'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 06 - VALIDATE : 16. ATT&CK Mapping
    # ------------------------------------------------------------------------
    SCENARIO_ATTCK_MAPPING: FocusScenario(
        id=SCENARIO_ATTCK_MAPPING,
        name='ATT&CK Mapping',
        description="Cartographier une simulation contrôlée sur les techniques MITRE ATT&CK.",
        compatible_modes=(MODE_VALIDATE,),
        objective="Associer précisément les actions offensives simulées aux identifiants TTPs MITRE ATT&CK.",
        required_information=(
            "Action simulée ou commande exécutée.",
            "Système cible (Linux, Windows, Cloud).",
            "Résultat observé (succès, blocage, trace générée).",
        ),
        parameters=(
            ScenarioParameter('technique_id', "Identifiant technique MITRE (ex: T1059.004)", 'string', False, ''),
            ScenarioParameter('tactic', "Tactique MITRE ciblée", 'choice', False, 'execution', (
                'initial_access', 'execution', 'persistence', 'privilege_escalation',
                'defense_evasion', 'credential_access', 'discovery', 'lateral_movement',
                'collection', 'exfiltration', 'command_and_control', 'impact',
            )),
            ScenarioParameter('layer_format', "Format de restitution", 'choice', False, 'markdown_matrix', ('navigator_json', 'markdown_matrix')),
        ),
        methodology=(
            "1. Décomposition des actions observées ou simulées en étapes élémentaires.",
            "2. Identification de la tactique (Enterprise matrix) et de la technique (ex: T1059.004).",
            "3. Documentation des sous-techniques, des commandes utilisées et des artefacts produits.",
            "4. Évaluation de la couverture de visibilité et des capacités de détection associées.",
            "5. Production d'une matrice de couverture synthétique (layer ATT&CK Navigator).",
        ),
        ai_instructions=(
            "Tu réalises une cartographie sur la matrice MITRE ATT&CK. Identifie avec précision l'identifiant "
            "technique (Txxxx) et sous-technique (Txxxx.yyy). Associe à chaque technique les sources de données "
            "de télémétrie recommandées par MITRE (Data Sources). Explique comment la simulation se positionne "
            "dans le cycle d'attaque complet."
        ),
        expected_response_structure=(
            "[Action simulée & Décomposition technique]",
            "[Correspondance MITRE ATT&CK (ID, Tactique, Nom)]",
            "[Télémétrie & Sources de données requises (Data Sources)]",
            "[Évaluation de la visibilité défensive]",
            "[Synthèse de couverture matricielle]",
        ),
        recommended_tool_categories=('framework_mapping', 'detection_engineering', 'command_reference'),
        recommended_tools=('python3', 'jq', 'curl'),
        prerequisites=("Description technique précise de l'action ou simulation réalisée.",),
        limits_and_precautions=("Une même commande peut relever de plusieurs tactiques selon l'intention opérationnelle.",),
        completion_criteria=("L'action est rattachée à son identifiant ATT&CK officiel avec sources de télémétrie.",),
        tui_metadata=ScenarioTUIMetadata(16, '[ATTCK]', '🗺', 'Alt+C', 'validate'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 06 - VALIDATE : 17. Detection Validation
    # ------------------------------------------------------------------------
    SCENARIO_DETECTION_VALIDATION: FocusScenario(
        id=SCENARIO_DETECTION_VALIDATION,
        name='Detection Validation',
        description="Vérifier l'efficacité d'une capacité de détection.",
        compatible_modes=(MODE_VALIDATE,),
        objective="Valider l'émission d'alerte, la télémétrie capturée et mesurer le temps de détection (MTTD).",
        required_information=(
            "Règle de détection testée (Sigma, YARA, règle SIEM/EDR).",
            "Procédure de simulation contrôlée prévue.",
            "Environnement de test isolé.",
        ),
        parameters=(
            ScenarioParameter('detection_rule', "Nom ou référence de la règle testée", 'string', False, ''),
            ScenarioParameter('simulation_tool', "Méthode de simulation", 'choice', False, 'custom_telemetry', ('atomic_red_team', 'custom_telemetry', 'synthetic_log')),
            ScenarioParameter('success_threshold_seconds', "Délai maximal de détection attendu (secondes)", 'integer', False, 60),
        ),
        methodology=(
            "1. Définition de la règle de détection testée (Sigma, Splunk, Elastic, Sysmon).",
            "2. Préparation d'une simulation contrôlée et reproductible de la technique d'attaque.",
            "3. Exécution de la simulation dans un environnement de test surveillé.",
            "4. Contrôle de la télémétrie reçue, du déclenchement d'alerte et mesure du délai (MTTD).",
            "5. Ajustement des filtres pour éliminer les angles morts et faux positifs.",
        ),
        ai_instructions=(
            "Tu valides l'efficacité de règles de détection. Compare ce qui a été exécuté avec ce que "
            "la règle inspecte effectivement. Identifie les angles morts d'évasion évidents (variations d'arguments, "
            "encodage base64, chemins alternatifs). Mesure l'exhaustivité de la détection et propose les ajustements "
            "nécessaires pour combler les failles."
        ),
        expected_response_structure=(
            "[Règle défensive auditée & Conditions de déclenchement]",
            "[Procédure de simulation unitaire contrôlée]",
            "[Contrôle de la télémétrie & Alertes émises]",
            "[Mesure du délai (MTTD) & Angles morts constatés]",
            "[Optimisations recommandées de la règle]",
        ),
        recommended_tool_categories=('detection_validation', 'detection_engineering', 'host_telemetry'),
        recommended_tools=('auditd', 'journalctl', 'curl', 'python3'),
        prerequisites=("Environnement de test dédié avec surveillance télémétrique active.",),
        limits_and_precautions=("Ne jamais exécuter de simulation offensive sur un système de production non préparé.",),
        completion_criteria=("L'efficacité de la règle est quantifiée avec identification des angles morts.",),
        tui_metadata=ScenarioTUIMetadata(17, '[DETECTION]', '🔍', 'Alt+D', 'validate'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 06 - VALIDATE : 18. Purple Team Exercise
    # ------------------------------------------------------------------------
    SCENARIO_PURPLE_TEAM_EXERCISE: FocusScenario(
        id=SCENARIO_PURPLE_TEAM_EXERCISE,
        name='Purple Team Exercise',
        description="Organiser une collaboration entre simulation et défense.",
        compatible_modes=(MODE_VALIDATE,),
        objective="Synchroniser les tests atomiques avec les analystes SOC pour améliorer immédiatement les règles.",
        required_information=(
            "Technique ou scénario conjoint convenu entre équipes Red et Blue.",
            "Canal de synchronisation opérationnelle en direct.",
            "Système cible instrumenté avec agents de détection.",
        ),
        parameters=(
            ScenarioParameter('red_action', "Action offensive simulée", 'string', False, ''),
            ScenarioParameter('blue_detection', "Détection Blue Team attendue", 'string', False, ''),
            ScenarioParameter('iteration', "Numéro d'itération du test atomique", 'integer', False, 1),
        ),
        methodology=(
            "1. Définition des scénarios atomiques prioritaires concertés entre Red et Blue Team.",
            "2. Exécution progressive et transparente d'une technique unitaire par la Red Team.",
            "3. Analyse en temps réel des journaux, traces et alertes par la Blue Team.",
            "4. Débriefing immédiat sur les lacunes de détection constatées.",
            "5. Création ou mise à jour conjointe de la règle de détection et re-test immédiat.",
        ),
        ai_instructions=(
            "Tu orchestres une session Purple Team collaborative. Encourage la transparence totale : "
            "chaque commande de simulation doit être partagée avec ses horodatages exacts. Guide la Blue Team "
            "dans la localisation immédiate de la trace télémétrique correspondante. Propose un ajustement "
            "rapide de règle et encadre le re-test unitaire pour valider l'amélioration."
        ),
        expected_response_structure=(
            "[Objectifs de l'itération Purple Team & Cadrage]",
            "[Exécution unitaire Red Team (commandes & horodatages)]",
            "[Observations Blue Team en direct (télémétrie captée)]",
            "[Analyse conjointe de l'écart & Ajustement de détection]",
            "[Validation du re-test & Consignation des progrès]",
        ),
        recommended_tool_categories=('purple_teaming', 'detection_validation', 'framework_mapping'),
        recommended_tools=('auditd', 'journalctl', 'ss', 'yara', 'python3'),
        prerequisites=("Participation conjointe des acteurs offensifs et défensifs avec droits adaptés.",),
        limits_and_precautions=("Les tests doivent être exécutés un par un pour isoler précisément chaque artefact.",),
        completion_criteria=("L'itération est bouclée avec amélioration avérée de la détection après re-test.",),
        tui_metadata=ScenarioTUIMetadata(18, '[PURPLE]', '🟣', 'Alt+B', 'validate'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 07 - ENGINEER : 19. System Hardening
    # ------------------------------------------------------------------------
    SCENARIO_SYSTEM_HARDENING: FocusScenario(
        id=SCENARIO_SYSTEM_HARDENING,
        name='System Hardening',
        description="Construire une procédure de durcissement Linux ou Windows.",
        compatible_modes=(MODE_ENGINEER,),
        objective="Établir une configuration de référence sécurisée (bastion, sysctl, permissions, services minimaux).",
        required_information=(
            "Système d'exploitation cible et version exacte.",
            "Rôle opérationnel du serveur (web, base de données, bastion, hyperviseur).",
            "Référentiel de conformité ciblé (ANSSI recommandation, CIS Benchmark, DISA STIG).",
        ),
        parameters=(
            ScenarioParameter('benchmark', "Référentiel de durcissement", 'choice', False, 'anssi_intermediaire', ('anssi_intermediaire', 'anssi_renforce', 'cis_level_1', 'cis_level_2')),
            ScenarioParameter('os_target', "Système d'exploitation cible", 'choice', False, 'debian_kali', ('debian_kali', 'ubuntu_server', 'rhel_rocky', 'windows_server')),
            ScenarioParameter('rollback_ready', "Exiger plan de retour arrière formalisé", 'boolean', False, True),
        ),
        methodology=(
            "1. Analyse de l'état initial du système et des services actifs (audit de configuration).",
            "2. Définition de la procédure de sauvegarde et plan de retour arrière (rollback).",
            "3. Durcissement du noyau et pile réseau via sysctl (/etc/sysctl.d/).",
            "4. Restriction des permissions fichiers, services superflus, PAM et configurations SSH.",
            "5. Audit de conformité final et vérification du bon fonctionnement des services légitimes.",
        ),
        ai_instructions=(
            "Tu guides le durcissement technique d'un système. Rédige des directives de configuration claires "
            "avec fichiers de surcharge dédiés (ex: /etc/sysctl.d/99-security.conf) plutôt que de modifier les fichiers "
            "systèmes par défaut. Inclus impérativement une procédure de sauvegarde préalable et un plan de retour "
            "arrière pour chaque mesure (notamment SSH et pare-feu)."
        ),
        expected_response_structure=(
            "[Référentiel de conformité & État initial]",
            "[Procédure de sauvegarde préalable & Retour arrière]",
            "[Paramétrage noyau & Réseau (sysctl)]",
            "[Désactivation des services superflus & Droits fichiers]",
            "[Vérification post-durcissement & Non-régression]",
        ),
        recommended_tool_categories=('system_hardening', 'configuration_audit', 'security_benchmarks'),
        recommended_tools=('sysctl', 'ss', 'systemctl', 'chmod', 'chown', 'auditd'),
        prerequisites=("Privilèges d'administration système et console de secours accessible en cas de coupure SSH.",),
        limits_and_precautions=("Un durcissement excessif peut bloquer des dépendances applicatives indispensables.",),
        completion_criteria=("La configuration sécurisée est appliquée avec procédure de sauvegarde et non-régression validée.",),
        tui_metadata=ScenarioTUIMetadata(19, '[HARDEN]', '🛡', 'Alt+H', 'engineer'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 07 - ENGINEER : 20. Network Security
    # ------------------------------------------------------------------------
    SCENARIO_NETWORK_SECURITY: FocusScenario(
        id=SCENARIO_NETWORK_SECURITY,
        name='Network Security',
        description="Examiner une architecture réseau, un pare-feu ou un VPN.",
        compatible_modes=(MODE_ENGINEER,),
        objective="Auditer et définir les règles de filtrage réseau, segmentation et chiffrement de transit.",
        required_information=(
            "Matrice des flux applicatifs nécessaires (adresses IP sources, destinations, ports, protocoles).",
            "Technologie de pare-feu utilisée (nftables, iptables, ufw, matériel dédié).",
            "Zones de sécurité et segmentation (DMZ, réseau de gestion, utilisateurs).",
        ),
        parameters=(
            ScenarioParameter('firewall_technology', "Technologie de pare-feu", 'choice', False, 'nftables', ('nftables', 'iptables', 'ufw', 'wireguard')),
            ScenarioParameter('architecture_layer', "Zone réseau concernée", 'choice', False, 'perimeter', ('perimeter', 'dmz', 'internal', 'management')),
            ScenarioParameter('default_policy', "Politique par défaut", 'choice', False, 'drop_all', ('drop_all', 'reject')),
        ),
        methodology=(
            "1. Cartographie des flux réseaux nécessaires et identification des segments sensibles.",
            "2. Définition de la politique de filtrage par défaut (DROP strict en entrée et transit).",
            "3. Rédaction des règles de pare-feu minimales nécessaires (nftables / iptables).",
            "4. Configuration des tunnels chiffrés et contrôle de l'authentification réseau.",
            "5. Vérification du filtrage, tests de fuite et documentation des flux autorisés.",
        ),
        ai_instructions=(
            "Tu conçois et audites des règles de sécurité réseau. Applique systématiquement le principe du moindre privilège : "
            "politique par défaut DROP en entrée et transit. Favorise la syntaxe moderne nftables. Prévois toujours "
            "une sécurité anti-verrouillage (règle temporaire de test réversible ou minuterie) lors de l'application "
            "à distance de règles de pare-feu pour éviter de perdre l'accès d'administration."
        ),
        expected_response_structure=(
            "[Matrice des flux autorisés & Segmentation]",
            "[Politique par défaut & Règles de sécurité]",
            "[Fichier de configuration du pare-feu (syntaxe exacte)]",
            "[Mesure de protection anti-coupure d'administration]",
            "[Procédure de validation du filtrage & Tests de fuite]",
        ),
        recommended_tool_categories=('network_security', 'firewall_tools', 'network_monitoring'),
        recommended_tools=('nft', 'iptables', 'ip', 'ss', 'tcpdump', 'wireguard'),
        prerequisites=("Schéma d'architecture réseau et inventaire précis des ports requis.",),
        limits_and_precautions=("Une mauvaise règle de filtrage peut isoler instantanément un équipement distant.",),
        completion_criteria=("Le jeu de règles filtrant est documenté avec politique DROP par défaut et accès d'administration préservé.",),
        tui_metadata=ScenarioTUIMetadata(20, '[NETSEC]', '🔒', 'Alt+N', 'engineer'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 07 - ENGINEER : 21. Security Automation
    # ------------------------------------------------------------------------
    SCENARIO_SECURITY_AUTOMATION: FocusScenario(
        id=SCENARIO_SECURITY_AUTOMATION,
        name='Security Automation',
        description="Concevoir et vérifier des automatisations techniques sûres et reproductibles.",
        compatible_modes=(MODE_ENGINEER,),
        objective="Structurer des playbooks ou scripts d'administration défensive avec gestion stricte des erreurs.",
        required_information=(
            "Tâche de sécurité à automatiser (déploiement de clés, rotation de certificats, audit régulier).",
            "Outil ou environnement d'automatisation (Ansible, script Bash idempotent, Python).",
            "Environnement cible et contraintes de disponibilité.",
        ),
        parameters=(
            ScenarioParameter('tool_framework', "Framework d'automatisation", 'choice', False, 'bash_idempotent', ('ansible', 'bash_idempotent', 'python_script')),
            ScenarioParameter('dry_run_capable', "Exiger capacité de simulation (--dry-run / check)", 'boolean', False, True),
            ScenarioParameter('target_environment', "Environnement cible", 'string', False, 'production_linux'),
        ),
        methodology=(
            "1. Spécification de la tâche d'administration ou de collecte à automatiser.",
            "2. Choix de la technologie adaptée garantissant l'idempotence et la sécurité d'exécution.",
            "3. Intégration d'un mode simulation (--dry-run) et de vérifications préalables.",
            "4. Gestion stricte des codes retour, journalisation d'audit et gestion des erreurs.",
            "5. Validation sur environnement de pré-production et documentation de maintenance.",
        ),
        ai_instructions=(
            "Tu conçois des automatisations de sécurité. L'idempotence est obligatoire : exécuter le script "
            "deux fois de suite ne doit apporter aucune modification la seconde fois. Fournis systématiquement "
            "un mode simulation (dry-run). Gère les secrets de façon sûre (pas de mot de passe en clair). "
            "Ajoute des traces d'audit horodatées pour chaque opération critique."
        ),
        expected_response_structure=(
            "[Spécification fonctionnelle & Principe d'idempotence]",
            "[Code d'automatisation commenté & Sécurisé]",
            "[Mode simulation (dry-run) & Pré-conditions d'exécution]",
            "[Gestion des secrets & Traces d'audit]",
            "[Protocole de recette & Validation non destructive]",
        ),
        recommended_tool_categories=('security_automation', 'script_tools', 'system_hardening'),
        recommended_tools=('python3', 'bash', 'systemd', 'cron', 'ansible'),
        prerequisites=("Environnement de test ou conteneur pour vérifier l'idempotence de l'automatisation.",),
        limits_and_precautions=("Toute automatisation à grande échelle propage instantanément les erreurs de conception.",),
        completion_criteria=("L'automatisation est idempotente, intègre un mode dry-run et gère les erreurs de manière robuste.",),
        tui_metadata=ScenarioTUIMetadata(21, '[AUTOMATION]', '⚙', 'Alt+M', 'engineer'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 08 - COORDINATE : 22. Exercise Planning
    # ------------------------------------------------------------------------
    SCENARIO_EXERCISE_PLANNING: FocusScenario(
        id=SCENARIO_EXERCISE_PLANNING,
        name='Exercise Planning',
        description="Préparer et organiser un exercice de cybersécurité.",
        compatible_modes=(MODE_COORDINATE,),
        objective="Définir le scénario pédagogique, le calendrier d'injection des événements et les participants.",
        required_information=(
            "Type d'exercice (crise sur table, simulation technique, exercice hybride).",
            "Public cible (direction, équipe technique, cellule de crise).",
            "Thématique principale (ransomware, fuite de données, panne majeure d'infrastructure).",
        ),
        parameters=(
            ScenarioParameter('exercise_type', "Format d'exercice", 'choice', False, 'tabletop', ('tabletop', 'hybrid_simulation', 'crisis_management')),
            ScenarioParameter('duration_hours', "Durée prévue en heures", 'integer', False, 4),
            ScenarioParameter('injects_count', "Nombre d'injections scénarisées", 'integer', False, 5),
        ),
        methodology=(
            "1. Définition des objectifs stratégiques et pédagogiques de l'exercice.",
            "2. Structuration du scénario général (chronologie, déclencheurs, niveau de réalisme).",
            "3. Préparation des injections d'incidents (injects) et du rythme de diffusion (MEL / MSEL).",
            "4. Organisation des rôles (White Team, Blue Team, Observateurs) et de la logistique.",
            "5. Définition des critères d'évaluation et de la grille d'observation.",
        ),
        ai_instructions=(
            "Tu structures la planification d'un exercice de cybersécurité. Structure un tableau d'injections "
            "(Master Scenario Events List - MSEL) avec : horaire relatif (T0+xx), émetteur simulé, canal, message, "
            "réaction attendue et critères d'évaluation. Veille au réalisme des temps de réaction sans saturer les participants."
        ),
        expected_response_structure=(
            "[Objectifs pédagogiques & Cible de l'exercice]",
            "[Scénario narratif global & Chronologie T0]",
            "[Tableau d'injections scénarisées (MSEL)]",
            "[Rôles & Gouvernance de l'exercice (White Team / Joueurs)]",
            "[Grille d'évaluation & Indicateurs de succès]",
        ),
        recommended_tool_categories=('exercise_governance', 'documentation_tools', 'reporting_tools'),
        recommended_tools=('libreoffice', 'pandoc', 'python3'),
        prerequisites=("Validation des objectifs par la direction de l'organisation organisatrice.",),
        limits_and_precautions=("S'assurer que les communications de l'exercice portent la mention 'EXERCICE CYBER - SANS IMPACT REEL'.",),
        completion_criteria=("Le plan d'exercice et le catalogue d'injections (MSEL) sont formalisés et validés.",),
        tui_metadata=ScenarioTUIMetadata(22, '[EXERCISE]', '📋', 'Alt+X', 'coordinate'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 08 - COORDINATE : 23. Rules of Engagement
    # ------------------------------------------------------------------------
    SCENARIO_RULES_OF_ENGAGEMENT: FocusScenario(
        id=SCENARIO_RULES_OF_ENGAGEMENT,
        name='Rules of Engagement',
        description="Définir les objectifs, responsabilités, limites et autorisations.",
        compatible_modes=(MODE_COORDINATE,),
        objective="Formaliser la convention d'exercice (RoE), la chaîne d'alerte d'urgence et les exclusions.",
        required_information=(
            "Périmètre précis autorisé et systèmes expressément exclus.",
            "Fenêtres horaires autorisées et restrictions calendaires.",
            "Noms et coordonnées des signataires autorisés et points de contact d'urgence.",
        ),
        parameters=(
            ScenarioParameter('exercise_name', "Nom de l'opération ou de l'exercice", 'string', False, ''),
            ScenarioParameter('authorized_window', "Fenêtre horaire autorisée", 'string', False, '09h00-18h00'),
            ScenarioParameter('emergency_stop_contact', "Point de contact unique arrêt d'urgence", 'string', False, ''),
        ),
        methodology=(
            "1. Délimitation explicite des périmètres autorisés et des systèmes formellement exclus.",
            "2. Fixation des fenêtres horaires, canaux de communication officiels et points de contact d'urgence.",
            "3. Définition des actions strictement interdites (déni de service, altération de données de production).",
            "4. Établissement de la procédure d'arrêt d'urgence immédiat (Emergency Stop).",
            "5. Formalisation du protocole de signature et de conservation de l'accord écrit.",
        ),
        ai_instructions=(
            "Tu rédiges les règles d'engagement (Rules of Engagement - RoE). Reste juridique, précis et sans "
            "ambiguïté. Définis les actions autorisées, celles soumises à accord préalable et celles formellement "
            "prohibées. Définis la formule codée ou le canal prioritaire pour déclencher l'arrêt d'urgence absolu."
        ),
        expected_response_structure=(
            "[Périmètre formel & Systèmes formellement exclus]",
            "[Fenêtres d'intervention & Restrictions calendaires]",
            "[Actions strictement prohibées (DoS, altérations irréversibles)]",
            "[Procédure d'arrêt d'urgence (Emergency Stop)]",
            "[Protocole d'approbation formelle & Signatures requises]",
        ),
        recommended_tool_categories=('exercise_governance', 'compliance_audit', 'reporting_tools'),
        recommended_tools=('pandoc', 'git'),
        prerequisites=("Pouvoir d'autorisation formel du signataire représentant l'entité évaluée.",),
        limits_and_precautions=("Aucune opération ne peut démarrer sans convention RoE signée par les deux parties.",),
        completion_criteria=("Le document des règles d'engagement est exhaustif, non ambigu et prêt pour signature.",),
        tui_metadata=ScenarioTUIMetadata(23, '[ROE]', '⚖', 'Alt+W', 'coordinate'),
        custom=False,
    ),

    # ------------------------------------------------------------------------
    # 08 - COORDINATE : 24. After Action Review
    # ------------------------------------------------------------------------
    SCENARIO_AFTER_ACTION_REVIEW: FocusScenario(
        id=SCENARIO_AFTER_ACTION_REVIEW,
        name='After Action Review',
        description="Structurer une analyse après exercice ou incident.",
        compatible_modes=(MODE_COORDINATE,),
        objective="Consigner la chronologie des faits, les écarts constatés, les points forts et le plan d'actions correctives.",
        required_information=(
            "Chronologie réelle de l'incident ou de l'exercice déroulé.",
            "Observations des participants et écarts par rapport aux procédures prévues.",
            "Difficultés techniques ou organisationnelles majeures rencontrées.",
        ),
        parameters=(
            ScenarioParameter('incident_or_exercise_ref', "Référence de l'incident ou de l'exercice", 'string', False, ''),
            ScenarioParameter('format', "Format de restitution", 'choice', False, 'standard_retex', ('standard_retex', 'anssi_post_mortem', 'lessons_learned')),
            ScenarioParameter('focus_axis', "Axe prioritaire d'analyse", 'choice', False, 'all', ('timeline', 'tooling', 'process', 'all')),
        ),
        methodology=(
            "1. Consolidation de la chronologie factuelle des événements et décisions prises.",
            "2. Analyse des écarts entre les procédures prévues et la réalité opérationnelle.",
            "3. Identification des points forts, des difficultés rencontrées et des lacunes d'outillage.",
            "4. Élaboration du plan d'actions correctives avec responsables désignés et échéances.",
            "5. Rédaction du rapport de synthèse RETEX destiné à la direction et aux équipes techniques.",
        ),
        ai_instructions=(
            "Tu animes et structures le retour d'expérience (RETEX / Post-Mortem). Adopte une approche "
            "constructive et 'blameless' (sans recherche de coupable individuel). Identifie les causes profondes "
            "systémiques (formation, ergonomie des outils, procédures obsolètes). Formule des actions correctives "
            "SMART (Spécifiques, Mesurables, Atteignables, Réalistes, Temporellement définies)."
        ),
        expected_response_structure=(
            "[Chronologie factuelle des faits & Décisions clés]",
            "[Analyse des écarts & Temps de réponse réels]",
            "[Points forts & Difficultés organisationnelles / techniques]",
            "[Plan d'actions correctives SMART (Responsables & Échéances)]",
            "[Recommandations stratégiques & Enseignements pérennes]",
        ),
        recommended_tool_categories=('exercise_governance', 'reporting_tools', 'documentation_tools'),
        recommended_tools=('pandoc', 'python3', 'git'),
        prerequisites=("Données réelles ou journal de bord de l'exercice ou de l'incident disponibles.",),
        limits_and_precautions=("Le RETEX doit se concentrer sur l'amélioration des processus et non la sanction d'individus.",),
        completion_criteria=("Le rapport RETEX est finalisé avec un plan d'actions correctives hiérarchisé et planifié.",),
        tui_metadata=ScenarioTUIMetadata(24, '[RETEX]', '📝', 'Alt+Y', 'coordinate'),
        custom=False,
    ),
}

# ============================================================================
# Playbooks guidés de l'OSINT Team (D-037)
# ============================================================================

OSINT_PLAYBOOK_SCENARIOS: dict[str, FocusScenario] = {
    SCENARIO_DOMAIN_INVESTIGATION: FocusScenario(
        id=SCENARIO_DOMAIN_INVESTIGATION,
        name='Domaine suspect',
        description="Qualification méthodique d'un nom de domaine : whois, dig, crt.sh (curl), sous-domaines, whatweb et archives web.",
        compatible_modes=(MODE_INTEL,),
        objective="Investiguer un domaine suspect étape par étape sans fuite d'information et avec traçabilité SHA-256.",
        required_information=(
            "Nom de domaine cible (FQDN).",
            "Cadre légal de l'analyse (mission OSINT).",
        ),
        parameters=(
            ScenarioParameter('target', "Nom de domaine cible à investiguer", 'string', True),
        ),
        methodology=(
            "1. Consultation passive WHOIS (registrar, dates, serveurs NS, contacts).",
            "2. Résolution DNS complète via dig (A, AAAA, MX, TXT/SPF/DMARC, SOA).",
            "3. Extraction des certificats SSL/TLS émis sur crt.sh via curl.",
            "4. Énumération passive des sous-domaines via subfinder ou amass.",
            "5. Empreinte technologique HTTP via whatweb (action active).",
            "6. Exploration des URLs archivées sur Wayback Machine via waybackurls.",
        ),
        ai_instructions=(
            "Tu guides l'enquêteur pas à pas dans l'analyse OSINT d'un nom de domaine. "
            "Chaque commande doit être préparée de façon bornée et soumise à [o/N]. "
            "Distingue rigoureusement les actions passives des actions actives. "
            "Rappelle les pivots découverts après chaque commande."
        ),
        expected_response_structure=(
            "[Étape du Playbook & Statut]",
            "[Commande préparée bornée]",
            "[Ce qu'on cherche]",
            "[Pivots d'investigation]",
        ),
        recommended_tool_categories=('osint_tools', 'network_discovery', 'domain_recon'),
        recommended_tools=('whois', 'dig', 'curl', 'subfinder', 'whatweb', 'waybackurls'),
        prerequisites=("Nom de domaine syntaxiquement valide.",),
        limits_and_precautions=(
            "L'étape whatweb est active et contacte directement l'infrastructure cible.",
            "Aucune exécution sans validation explicite [o/N].",
        ),
        completion_criteria=("Toutes les étapes du playbook ont été déroulées ou sautées avec traçabilité SHA-256.",),
        tui_metadata=ScenarioTUIMetadata(101, '[DOMAINE]', '🔍', 'Alt+D', 'intel'),
        custom=False,
    ),
    SCENARIO_IMAGE_FORENSICS: FocusScenario(
        id=SCENARIO_IMAGE_FORENSICS,
        name="Analyse d'image forensique",
        description="Scellage d'intégrité SHA-256, extraction des métadonnées EXIF, audit mat2 et analyse géospatiale/temporelle.",
        compatible_modes=(MODE_INTEL,),
        objective="Extraire et qualifier les éléments probatoires d'un fichier image sans altération du support original.",
        required_information=(
            "Chemin local du fichier image à analyser.",
        ),
        parameters=(
            ScenarioParameter('target', "Chemin absolu ou relatif du fichier image", 'path', True),
        ),
        methodology=(
            "1. Scellage de l'empreinte cryptographique SHA-256 de la pièce.",
            "2. Extraction exhaustive des métadonnées EXIF via exiftool.",
            "3. Audit des métadonnées résiduelles et masquage via mat2.",
            "4. Extraction isolée des coordonnées GPS et horodatages originaux.",
        ),
        ai_instructions=(
            "Tu guides l'analyse forensique d'un fichier image. Respecte la chaîne de conservation : "
            "toujours commencer par le calcul de l'empreinte SHA-256. Décompose les métadonnées techniques "
            "(appareil, logiciel de retouche) et isole les coordonnées GPS pour cartographie."
        ),
        expected_response_structure=(
            "[Étape du Playbook & Intégrité]",
            "[Commande préparée bornée]",
            "[Ce qu'on cherche]",
            "[Indices spatio-temporels]",
        ),
        recommended_tool_categories=('forensic_tools', 'media_analysis', 'metadata_tools'),
        recommended_tools=('exiftool', 'mat2', 'strings'),
        prerequisites=("Fichier image accessible localement en lecture seule.",),
        limits_and_precautions=("Analyse strictement locale sans téléversement vers des services tiers.",),
        completion_criteria=("L'empreinte SHA-256 et les métadonnées sont consignées dans le dossier d'enquête.",),
        tui_metadata=ScenarioTUIMetadata(102, '[IMAGE]', '🖼', 'Alt+I', 'intel'),
        custom=False,
    ),
    SCENARIO_IDENTITY_CORRELATION: FocusScenario(
        id=SCENARIO_IDENTITY_CORRELATION,
        name="Investigation Email & Pseudonyme",
        description="Recherche de comptes en ligne, énumération multi-plateformes, corrélation d'identités et qualification de certitude.",
        compatible_modes=(MODE_INTEL,),
        objective="Identifier et recouper les comptes publics associés à un pseudonyme ou une adresse email.",
        required_information=(
            "Pseudonyme ou adresse email de la cible.",
        ),
        parameters=(
            ScenarioParameter('target', "Pseudonyme ou adresse email", 'string', True),
        ),
        methodology=(
            "1. Énumération de présence de comptes via maigret ou holehe.",
            "2. Validation croisée multi-sources via sherlock.",
            "3. Corrélation des profils, biographies et score de certitude.",
        ),
        ai_instructions=(
            "Tu guides l'investigation sur une identité numérique ou pseudonyme. "
            "Applique une rigueur absolue : un profil portant le même pseudo n'est pas nécessairement la même personne. "
            "Qualifie le niveau de certitude : observé, source unique ou recoupé."
        ),
        expected_response_structure=(
            "[Étape du Playbook & Cible]",
            "[Commande préparée]",
            "[Comptes détectés]",
            "[Niveau de certitude & Recoupement]",
        ),
        recommended_tool_categories=('osint_tools', 'identity_recon', 'social_discovery'),
        recommended_tools=('maigret', 'sherlock', 'holehe'),
        prerequisites=("Identifiant ou adresse email syntaxiquement valide.",),
        limits_and_precautions=("Zéro clé API, zéro connexion avec compte enquêteur, respect de la proportionnalité.",),
        completion_criteria=("Les profils avérés sont qualifiés avec source et niveau de certitude au dossier.",),
        tui_metadata=ScenarioTUIMetadata(103, '[IDENTITE]', '👤', 'Alt+U', 'intel'),
        custom=False,
    ),
    SCENARIO_ORG_EXPOSURE: FocusScenario(
        id=SCENARIO_ORG_EXPOSURE,
        name="Surface d'exposition d'une organisation",
        description="Collecte OSINT d'organisation : emails d'employés, sous-domaines, technologies en ligne et détection de secrets publics.",
        compatible_modes=(MODE_INTEL,),
        objective="Cartographier l'exposition publique d'une organisation en sources ouvertes.",
        required_information=(
            "Domaine principal de l'organisation.",
            "URL optionnelle d'un dépôt de code public.",
        ),
        parameters=(
            ScenarioParameter('target', "Domaine principal de l'organisation", 'string', True),
        ),
        methodology=(
            "1. Collecte OSINT globale via theHarvester (emails, hôtes, employés).",
            "2. Énumération passive des sous-domaines via subfinder.",
            "3. Détection des technologies exposées via httpx ou whatweb.",
            "4. Recherche de fuites de secrets dans le code public via trufflehog ou gitleaks.",
        ),
        ai_instructions=(
            "Tu guides la cartographie de la surface d'exposition d'une organisation. "
            "Priorise les fuites potentielles de secrets et identifiants exposés. "
            "Détaille les risques associés à chaque élément découvert."
        ),
        expected_response_structure=(
            "[Étape du Playbook]",
            "[Commande préparée]",
            "[Éléments exposés découverts]",
            "[Pivots d'infrastructure & Secrets]",
        ),
        recommended_tool_categories=('osint_tools', 'recon_tools', 'secrets_detection'),
        recommended_tools=('theharvester', 'subfinder', 'httpx', 'trufflehog', 'gitleaks'),
        prerequisites=("Nom de domaine de l'organisation cible.",),
        limits_and_precautions=("Seule la détection sur sources publiques est autorisée sans engagement actif intrusif.",),
        completion_criteria=("La cartographie d'exposition et les alertes de secrets sont documentées.",),
        tui_metadata=ScenarioTUIMetadata(104, '[EXPOSITION]', '🏢', 'Alt+O', 'intel'),
        custom=False,
    ),
    SCENARIO_PHONE_INTEL: FocusScenario(
        id=SCENARIO_PHONE_INTEL,
        name="Renseignement téléphonique",
        description="Investigation sur un numéro de téléphone international : validation E.164, opérateur télécom et dorks web sans clé API.",
        compatible_modes=(MODE_INTEL,),
        objective="Identifier l'opérateur, le pays et les mentions publiques associées à un numéro de téléphone.",
        required_information=(
            "Numéro de téléphone au format international (+...).",
        ),
        parameters=(
            ScenarioParameter('target', "Numéro de téléphone au format E.164", 'string', True),
        ),
        methodology=(
            "1. Analyse de validité et identification de l'opérateur via phoneinfoga.",
            "2. Génération et exécution de dorks de recherche passive sur le numéro.",
        ),
        ai_instructions=(
            "Tu guides l'analyse OSINT d'un numéro de téléphone. "
            "Vérifie rigoureusement le format E.164. Aucun appel, SMS ni interaction active avec la ligne. "
            "Recherche exclusivement des mentions préexistantes en sources ouvertes."
        ),
        expected_response_structure=(
            "[Étape du Playbook]",
            "[Commande préparée]",
            "[Opérateur & Caractéristiques]",
            "[Traces & Mentions en ligne]",
        ),
        recommended_tool_categories=('osint_tools', 'phone_recon'),
        recommended_tools=('phoneinfoga',),
        prerequisites=("Numéro de téléphone au format international E.164.",),
        limits_and_precautions=("Aucune clé API requise ; scans gratuits uniquement ; zéro interaction réseau avec l'appareil.",),
        completion_criteria=("L'opérateur, le type de ligne et les corrélations web sont consignés.",),
        tui_metadata=ScenarioTUIMetadata(105, '[PHONE]', '📞', 'Alt+P', 'intel'),
        custom=False,
    ),
    SCENARIO_WEB_ARCHIVES: FocusScenario(
        id=SCENARIO_WEB_ARCHIVES,
        name="Exploration d'archives web",
        description="Exploration chronologique de la mémoire du Web : extraction d'URLs historiques, recoupement multi-archives et instantanés.",
        compatible_modes=(MODE_INTEL,),
        objective="Retrouver des endpoints, documents ou données sensibles archivés disparus du Web actif.",
        required_information=(
            "Nom de domaine ou URL cible.",
        ),
        parameters=(
            ScenarioParameter('target', "Nom de domaine ou URL cible", 'string', True),
        ),
        methodology=(
            "1. Extraction des URLs archivées sur Wayback Machine via waybackurls.",
            "2. Recoupement multi-fournisseurs d'archives via gau.",
            "3. Consultation de disponibilité d'instantanés via curl sur l'API Wayback.",
        ),
        ai_instructions=(
            "Tu guides l'exploration des archives web historiques. "
            "Filtre les résultats pour isoler les extensions sensibles (.json, .bak, .env, .pdf). "
            "Consigne les URLs d'intérêt dans le dossier d'enquête avec horodatage d'archivage."
        ),
        expected_response_structure=(
            "[Étape du Playbook]",
            "[Commande préparée]",
            "[URLs & Ressources sensibles trouvées]",
            "[Pivots historiques]",
        ),
        recommended_tool_categories=('osint_tools', 'archive_tools', 'web_recon'),
        recommended_tools=('waybackurls', 'gau', 'curl'),
        prerequisites=("Nom de domaine ou URL accessible dans les archives publiques.",),
        limits_and_precautions=("Consultation d'archives publiques sans contact avec le serveur actuel.",),
        completion_criteria=("Les ressources historiques identifiées sont documentées au dossier.",),
        tui_metadata=ScenarioTUIMetadata(106, '[ARCHIVES]', '🏛', 'Alt+A', 'intel'),
        custom=False,
    ),
}

# ============================================================================
# Registre extensible des scénarios
# ============================================================================

class ScenarioRegistry:
    """Registre des scénarios professionnels avec gestion de l'extensibilité."""

    def __init__(self):
        self._scenarios: dict[str, FocusScenario] = {}
        # Enregistrer les 24 scénarios natifs
        for scenario_id in ORDERED_BUILTIN_SCENARIO_IDS:
            self._scenarios[scenario_id] = BUILTIN_SCENARIOS[scenario_id]
        # Enregistrer les playbooks OSINT (D-037)
        for scenario_id in ORDERED_OSINT_PLAYBOOK_IDS:
            self._scenarios[scenario_id] = OSINT_PLAYBOOK_SCENARIOS[scenario_id]

    def list_scenarios(self, mode_id: str | None = None, include_playbooks: bool = False) -> tuple[FocusScenario, ...]:
        """Retourne la liste des scénarios disponibles, filtrés par mode si demandé."""
        order = ORDERED_BUILTIN_SCENARIO_IDS + (ORDERED_OSINT_PLAYBOOK_IDS if include_playbooks else ())
        builtins = [self._scenarios[sid] for sid in order if sid in self._scenarios]
        customs = [s for sid, s in self._scenarios.items() if sid not in ORDERED_BUILTIN_SCENARIO_IDS and sid not in ORDERED_OSINT_PLAYBOOK_IDS]
        all_scenarios = builtins + customs

        if mode_id is None:
            return tuple(all_scenarios)

        norm_mode = mode_id.strip().lower()
        if norm_mode.startswith('mode_'):
            norm_mode = norm_mode[5:]

        return tuple(s for s in all_scenarios if norm_mode in s.compatible_modes)

    def is_scenario_masked(self, scenario_id: str) -> bool:
        """Vérifie si un scénario est masqué selon le cap D-037 (modes retirés)."""
        try:
            sc = self.get_scenario(scenario_id)
            return not any(m in ACTIVE_SCENARIO_MODES for m in sc.compatible_modes)
        except UnknownScenarioError:
            return True

    def list_visible_scenarios(self, mode_id: str | None = None) -> tuple[FocusScenario, ...]:
        """Retourne uniquement les scénarios visibles (non masqués par le cap D-037).

        Les anciens scénarios des modes retirés (assist, trace, defend, assess,
        validate, engineer, coordinate) restent enregistrés dans le registre
        mais sont masqués de la vue active.
        """
        scs = self.list_scenarios(mode_id=mode_id, include_playbooks=True)
        if mode_id is not None:
            norm_mode = mode_id.strip().lower()
            if norm_mode.startswith('mode_'):
                norm_mode = norm_mode[5:]
            if norm_mode in WITHDRAWN_SCENARIO_MODES:
                return ()
        return tuple(s for s in scs if not self.is_scenario_masked(s.id))

    def list_scenario_ids(self, mode_id: str | None = None, include_playbooks: bool = False) -> tuple[str, ...]:
        """Retourne la liste ordonnée des identifiants des scénarios."""
        return tuple(s.id for s in self.list_scenarios(mode_id=mode_id, include_playbooks=include_playbooks))

        """Retourne la liste ordonnée des identifiants des scénarios."""
        return tuple(s.id for s in self.list_scenarios(mode_id=mode_id))

    def get_scenario(self, scenario_id: str) -> FocusScenario:
        """Récupère un scénario par son identifiant ou alias, ou lève UnknownScenarioError."""
        normalized = self._normalize_id(scenario_id)
        # Résolution d'alias
        if normalized in SCENARIO_ALIASES:
            normalized = SCENARIO_ALIASES[normalized]

        if normalized not in self._scenarios:
            raise UnknownScenarioError(
                f"Scénario inconnu : '{scenario_id}'. Scénarios disponibles : {', '.join(self.list_scenario_ids())}"
            )
        return self._scenarios[normalized]

    def has_scenario(self, scenario_id: str) -> bool:
        """Vérifie si un scénario existe (y compris via alias)."""
        try:
            normalized = self._normalize_id(scenario_id)
            if normalized in SCENARIO_ALIASES:
                normalized = SCENARIO_ALIASES[normalized]
            return normalized in self._scenarios
        except Exception:
            return False

    def is_compatible(self, scenario_id: str, mode_id: str) -> bool:
        """Vérifie si un scénario est compatible avec un mode donné."""
        try:
            scenario = self.get_scenario(scenario_id)
            norm_mode = mode_id.strip().lower()
            if norm_mode.startswith('mode_'):
                norm_mode = norm_mode[5:]
            return norm_mode in scenario.compatible_modes
        except UnknownScenarioError:
            return False

    def register_custom_scenario(self, scenario: FocusScenario) -> None:
        """Enregistre un scénario personnalisé après validation stricte."""
        self.validate_scenario_definition(scenario)
        if scenario.id in ORDERED_BUILTIN_SCENARIO_IDS or scenario.id in BUILTIN_SCENARIOS:
            raise InvalidScenarioDefinitionError(
                f"Impossible d'écraser le scénario natif obligatoire : '{scenario.id}'."
            )

        custom_scenario = FocusScenario(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            compatible_modes=scenario.compatible_modes,
            objective=scenario.objective,
            required_information=scenario.required_information,
            parameters=scenario.parameters,
            methodology=scenario.methodology,
            ai_instructions=scenario.ai_instructions,
            expected_response_structure=scenario.expected_response_structure,
            recommended_tool_categories=scenario.recommended_tool_categories,
            recommended_tools=scenario.recommended_tools,
            prerequisites=scenario.prerequisites,
            limits_and_precautions=scenario.limits_and_precautions,
            completion_criteria=scenario.completion_criteria,
            tui_metadata=scenario.tui_metadata,
            custom=True,
        )
        self._scenarios[custom_scenario.id] = custom_scenario

    def unregister_custom_scenario(self, scenario_id: str) -> bool:
        """Supprime un scénario personnalisé. Refuse la suppression des scénarios natifs."""
        normalized = self._normalize_id(scenario_id)
        if normalized in ORDERED_BUILTIN_SCENARIO_IDS or normalized in BUILTIN_SCENARIOS:
            raise InvalidScenarioDefinitionError(
                f"Interdiction formelle de supprimer le scénario natif : '{normalized}'."
            )
        if normalized in self._scenarios:
            del self._scenarios[normalized]
            return True
        return False

    def validate_scenario_definition(self, scenario: Any) -> None:
        """Valide exhaustivement une définition de scénario sans exécution de code."""
        if not isinstance(scenario, FocusScenario):
            raise InvalidScenarioDefinitionError(
                f"L'objet fourni doit être une instance de FocusScenario, reçu : {type(scenario).__name__}."
            )

        # Validation de l'identifiant
        if not isinstance(scenario.id, str) or not _SCENARIO_ID_PATTERN.fullmatch(scenario.id):
            raise InvalidScenarioDefinitionError(
                f"Identifiant de scénario invalide : '{scenario.id}'. "
                f"Attendu : chaîne minuscule alphanumérique (2 à 48 caractères avec _ et -)."
            )

        # Validation des textes obligatoires
        for field_name in ('name', 'description', 'objective', 'ai_instructions'):
            val = getattr(scenario, field_name, None)
            if not isinstance(val, str) or not val.strip():
                raise InvalidScenarioDefinitionError(
                    f"Le champ obligatoire '{field_name}' doit être une chaîne non vide."
                )

        # Validation des modes compatibles
        if not isinstance(scenario.compatible_modes, (tuple, list)) or not scenario.compatible_modes:
            raise InvalidScenarioDefinitionError(
                "Le champ 'compatible_modes' doit être un tuple ou liste non vide."
            )
        for m in scenario.compatible_modes:
            if not isinstance(m, str) or not m.strip():
                raise InvalidScenarioDefinitionError("Chaque mode compatible doit être une chaîne non vide.")
            if m not in ORDERED_BUILTIN_MODE_IDS:
                raise InvalidScenarioDefinitionError(
                    f"Mode inconnu dans compatible_modes : '{m}'. Modes valides : {', '.join(ORDERED_BUILTIN_MODE_IDS)}"
                )

        # Validation des listes de chaînes obligatoires
        for field_name in (
            'required_information',
            'methodology',
            'expected_response_structure',
            'recommended_tool_categories',
            'recommended_tools',
            'prerequisites',
            'limits_and_precautions',
            'completion_criteria',
        ):
            val = getattr(scenario, field_name, None)
            if not isinstance(val, (tuple, list)):
                raise InvalidScenarioDefinitionError(
                    f"Le champ '{field_name}' doit être un tuple ou une liste."
                )
            for item in val:
                if not isinstance(item, str) or not item.strip():
                    raise InvalidScenarioDefinitionError(
                        f"Tous les éléments de '{field_name}' doivent être des chaînes non vides."
                    )
                if callable(item):
                    raise InvalidScenarioDefinitionError("Éléments exécutables interdits.")

        # Validation des paramètres
        if not isinstance(scenario.parameters, (tuple, list)):
            raise InvalidScenarioDefinitionError("'parameters' doit être un tuple de ScenarioParameter.")
        for p in scenario.parameters:
            if not isinstance(p, ScenarioParameter):
                raise InvalidScenarioDefinitionError(
                    f"Chaque paramètre doit être une instance de ScenarioParameter, reçu {type(p).__name__}."
                )
            if not p.name or not isinstance(p.name, str) or not p.name.isidentifier():
                raise InvalidScenarioDefinitionError(
                    f"Nom de paramètre invalide : '{getattr(p, 'name', None)}'."
                )

        # Validation des métadonnées TUI
        if not isinstance(scenario.tui_metadata, ScenarioTUIMetadata):
            raise InvalidScenarioDefinitionError("tui_metadata doit être une instance de ScenarioTUIMetadata.")
        if type(scenario.tui_metadata.index) is not int or scenario.tui_metadata.index < 1:
            raise InvalidScenarioDefinitionError("tui_metadata.index doit être un entier >= 1.")
        if not scenario.tui_metadata.badge or not scenario.tui_metadata.glyph:
            raise InvalidScenarioDefinitionError("Badge et icône TUI ne peuvent pas être vides.")

    @staticmethod
    def _normalize_id(scenario_id: str) -> str:
        if not isinstance(scenario_id, str):
            raise UnknownScenarioError(
                f"Identifiant de scénario invalide : type {type(scenario_id).__name__} non pris en charge."
            )
        normalized = scenario_id.strip().lower()
        if not normalized:
            raise UnknownScenarioError("Identifiant de scénario vide.")
        if normalized.startswith('scenario_'):
            normalized = normalized[9:]
        return normalized


def create_default_scenario_registry() -> ScenarioRegistry:
    """Crée et retourne une instance prête à l'emploi du registre des scénarios."""
    return ScenarioRegistry()
