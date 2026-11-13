# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : osint_specialties.py
# Role          : Specialites OSINT, routage d'indices, pivots et recommandations
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Specialites OSINT de l'OSINT Team, routage des indices et pivots d'investigation.

Ce module constitue la reference de routage pour l'OSINT Team selon le cap D-037 :
- Les 7 specialites OSINT couvertes (domain, infra, person, social, media, leaks, web_archive)
- Qualification de l'indice de l'enqueteur (IP, domaine, URL, email, pseudo, tel, hash, image, fichier)
- Proposition d'outils issus du catalogue strict (liste blanche data/tools/catalog.json)
- Distinction passive / active imperative avant toute approbation
- Suggestion de pivots techniques pour progresser dans l'enquete sans cle API.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

import indices_outils
from tools_catalog import discover_tools, load_catalog

# ============================================================================
# Contrat officiel des 7 specialites OSINT
# ============================================================================

SPECIALTIES: tuple[str, ...] = (
    'domain',
    'infra',
    'person',
    'social',
    'media',
    'leaks',
    'web_archive',
)


@dataclass(frozen=True)
class OSINTSpecialty:
    """Definition formelle d'une specialite au sein de l'OSINT Team."""
    id: str
    name: str
    description: str
    input_types: tuple[str, ...]
    recommended_tools: tuple[str, ...]


_SPECIALTIES_CATALOG: tuple[OSINTSpecialty, ...] = (
    OSINTSpecialty(
        id='domain',
        name='Domaines & DNS',
        description='Reconnaissance de noms de domaine, énumération DNS, sous-domaines et enregistrements WHOIS.',
        input_types=('domain', 'ip', 'url'),
        recommended_tools=(
            'whois', 'dig', 'subfinder', 'dnsrecon', 'dnsenum',
            'amass', 'sublist3r', 'fierce', 'theharvester', 'dnsx', 'photon',
        ),
    ),
    OSINTSpecialty(
        id='infra',
        name='Infrastructure & Réseau',
        description='Cartographie d’infrastructures, serveurs web, technologies exposées, WAF et scan d’adresses IP.',
        input_types=('ip', 'domain', 'url'),
        recommended_tools=(
            'whatweb', 'wafw00f', 'httpx', 'nmap', 'curl', 'amass', 'dmitry', 'spiderfoot',
        ),
    ),
    OSINTSpecialty(
        id='person',
        name='Personne & Identité',
        description='Recherche d’identités, vérification d’adresses e-mail, numéros de téléphone et pseudonymes.',
        input_types=('email', 'phone', 'username'),
        recommended_tools=(
            'holehe', 'phoneinfoga', 'maigret', 'sherlock', 'social-analyzer',
            'theharvester', 'spiderfoot', 'recon-ng',
        ),
    ),
    OSINTSpecialty(
        id='social',
        name='Réseaux Sociaux',
        description='Investigation sur les profils de plateformes sociales, présence en ligne et pseudonymes.',
        input_types=('username',),
        recommended_tools=(
            'maigret', 'sherlock', 'social-analyzer',
        ),
    ),
    OSINTSpecialty(
        id='media',
        name='Médias & Fichiers',
        description='Analyse de métadonnées d’images, extraction de chaînes, stéganographie et carving de fichiers.',
        input_types=('image', 'file'),
        recommended_tools=(
            'exiftool', 'mat2', 'foremost', 'binwalk', 'strings', 'metagoofil',
        ),
    ),
    OSINTSpecialty(
        id='leaks',
        name='Fuites & Secrets',
        description='Détection de secrets, clés d’API compromises, tokens et fuites dans les dépôts et fichiers.',
        input_types=('file', 'hash'),
        recommended_tools=(
            'gitleaks', 'trufflehog',
        ),
    ),
    OSINTSpecialty(
        id='web_archive',
        name='Web & Archives',
        description='Exploration d’historiques web, endpoints archivés, URLs passées (Wayback Machine).',
        input_types=('domain', 'url'),
        recommended_tools=(
            'gau',
        ),
    ),
)

_SPECIALTIES_MAP: dict[str, OSINTSpecialty] = {s.id: s for s in _SPECIALTIES_CATALOG}


def get_specialty(specialty_id: str) -> OSINTSpecialty | None:
    """Résout une spécialité OSINT par son identifiant strict ou normalisé."""
    if not isinstance(specialty_id, str):
        return None
    key = specialty_id.strip().lower()
    return _SPECIALTIES_MAP.get(key)


def list_specialties() -> tuple[OSINTSpecialty, ...]:
    """Retourne la liste ordonnée des 7 spécialités OSINT."""
    return _SPECIALTIES_CATALOG


# ============================================================================
# Recommandations d'outils et routage d'indices
# ============================================================================

@dataclass(frozen=True)
class ToolRecommendation:
    """Recommandation d'outil qualifiee selon l'activite et la disponibilite."""
    id: str
    name: str
    activity: str  # 'passive' ou 'active'
    state: str  # 'installed', 'available', 'unverified', etc.
    installed: bool
    source: str  # 'kali' ou 'vendored'
    specialties: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class PivotSuggestion:
    """Suggestion de pivot technique issu d'une observation forensique."""
    source_indicator: str
    source_type: str
    pivot_type: str
    pivot_value: str
    specialty: str
    recommended_tools: tuple[str, ...]
    activity: str
    explanation: str


@dataclass(frozen=True)
class ClueRouting:
    """Proposition structuree de routage pour un indice donne."""
    clue: str
    clue_type: str
    validation: str
    normalized: str | None
    specialties: tuple[OSINTSpecialty, ...]
    recommended_tools: tuple[ToolRecommendation, ...]
    passive_tools: tuple[ToolRecommendation, ...]
    active_tools: tuple[ToolRecommendation, ...]
    installed_tools: tuple[ToolRecommendation, ...]
    to_install_tools: tuple[ToolRecommendation, ...]
    pivots: tuple[PivotSuggestion, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'clue': self.clue,
            'clue_type': self.clue_type,
            'validation': self.validation,
            'normalized': self.normalized,
            'specialties': [s.id for s in self.specialties],
            'recommended_tools': [t.id for t in self.recommended_tools],
            'passive_tools': [t.id for t in self.passive_tools],
            'active_tools': [t.id for t in self.active_tools],
            'installed_tools': [t.id for t in self.installed_tools],
            'to_install_tools': [t.id for t in self.to_install_tools],
            'pivots_count': len(self.pivots),
            'summary': self.summary,
        }

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


def _determine_specialties_for_type(clue_type: str) -> tuple[OSINTSpecialty, ...]:
    """Associe les spécialités pertinentes à un type d'indice."""
    matching: list[OSINTSpecialty] = []
    for spec in _SPECIALTIES_CATALOG:
        if clue_type in spec.input_types:
            matching.append(spec)
    return tuple(matching)


def route_clue(
    clue: str | dict[str, Any],
    *,
    catalog: Sequence[dict[str, Any]] | None = None,
    tools_states: dict[str, Any] | None = None,
) -> ClueRouting:
    """Qualifie un indice et route vers les spécialités et outils pertinents.

    Distingue rigoureusement les approches passives et actives, ainsi que les
    outils immédiatement utilisables de ceux nécessitant une installation.
    """
    if isinstance(clue, dict):
        raw_val = clue.get('original') or clue.get('value') or ''
        clue_type = clue.get('type') or indices_outils.detect_indice_type(raw_val) or 'unknown'
        classification = clue
    else:
        raw_val = str(clue)
        detected = indices_outils.detect_indice_type(raw_val)
        clue_type = detected if detected else 'unknown'
        if clue_type != 'unknown':
            classification = indices_outils.classify(raw_val, clue_type)
        else:
            classification = {
                'validation': 'invalid',
                'original': raw_val,
                'normalized': None,
                'ambiguities': ['Type d’indice non identifiable.'],
            }

    validation = classification.get('validation', 'unknown')
    normalized = classification.get('normalized')

    # Spécialités candidates
    relevant_specialties = _determine_specialties_for_type(clue_type)
    relevant_specialty_ids = {s.id for s in relevant_specialties}

    # Chargement catalogue et découverte des outils
    cat = tuple(catalog) if catalog is not None else load_catalog()
    states = tools_states if tools_states is not None else discover_tools(cat)

    recommendations: list[ToolRecommendation] = []
    seen_tool_ids: set[str] = set()

    # 1. Sélection des outils correspondant au type d'indice direct
    # ou aux spécialités identifiées
    for row in cat:
        tid = row['id']
        if tid in seen_tool_ids:
            continue
        tool_inputs = set(row.get('input_types', []))
        tool_specs = set(row.get('specialties', []))

        # Correspondance directe par type ou par spécialité
        direct_match = clue_type in tool_inputs
        specialty_match = bool(tool_specs & relevant_specialty_ids)

        if direct_match or specialty_match:
            seen_tool_ids.add(tid)
            state_info = states.get(tid)
            st_val = state_info.state if state_info else 'available'
            is_inst = (st_val == 'installed')
            rec = ToolRecommendation(
                id=tid,
                name=row['name'],
                activity=row.get('activity', 'active'),
                state=st_val,
                installed=is_inst,
                source=row.get('source', 'kali'),
                specialties=tuple(row.get('specialties', ())),
                notes=row.get('notes', ''),
            )
            recommendations.append(rec)

    # Ordonnancement : passif d'abord, puis installé d'abord
    recommendations.sort(key=lambda t: (0 if t.activity == 'passive' else 1, 0 if t.installed else 1, t.name))

    passive_tools = tuple(t for t in recommendations if t.activity == 'passive')
    active_tools = tuple(t for t in recommendations if t.activity == 'active')
    installed_tools = tuple(t for t in recommendations if t.installed)
    to_install_tools = tuple(t for t in recommendations if not t.installed)

    # Génération des suggestions de pivots
    pivots = tuple(suggest_pivots(classification))

    # Synthèse textuelle claire en français
    specs_label = ', '.join(s.name for s in relevant_specialties) if relevant_specialties else 'Aucune spécialité directe'
    pass_names = ', '.join(t.id for t in passive_tools) or 'aucun'
    act_names = ', '.join(t.id for t in active_tools) or 'aucun'
    inst_names = ', '.join(t.id for t in installed_tools) or 'aucun'
    to_inst_names = ', '.join(t.id for t in to_install_tools) or 'aucun'

    summary = (
        f"Indice qualifié : [{clue_type.upper()}] '{raw_val}' (statut: {validation}).\n"
        f"Spécialités recommandées : {specs_label}.\n"
        f"Outils passifs préconisés : {pass_names}.\n"
        f"Outils actifs (approbation requise) : {act_names}.\n"
        f"Disponibilité locale : installés [{inst_names}] ; à installer [{to_inst_names}]."
    )

    return ClueRouting(
        clue=raw_val,
        clue_type=clue_type,
        validation=validation,
        normalized=normalized,
        specialties=relevant_specialties,
        recommended_tools=tuple(recommendations),
        passive_tools=passive_tools,
        active_tools=active_tools,
        installed_tools=installed_tools,
        to_install_tools=to_install_tools,
        pivots=pivots,
        summary=summary,
    )


# Alias d'interface standard
route_indicator = route_clue


# ============================================================================
# Generation dynamique de pivots d'investigation
# ============================================================================

def suggest_pivots(findings: Any) -> list[PivotSuggestion]:
    """Déduit des pistes de rebond (pivots) à partir des indices constatés.

    Supporte divers formats d'entrée :
    - Valeur brute (str)
    - Dictionnaire d'indice qualifié (classify())
    - Dictionnaire de constatations structurées (ex: {'email': '...'})
    - Liste ou séquence d'indices.
    """
    suggestions: list[PivotSuggestion] = []
    if findings is None:
        return suggestions

    # Si c'est une liste, itérer récursivement
    if isinstance(findings, (list, tuple, set)):
        for item in findings:
            suggestions.extend(suggest_pivots(item))
        return _deduplicate_pivots(suggestions)

    # Extraction des paires (type, valeur)
    items_to_process: list[tuple[str, str]] = []

    if isinstance(findings, str):
        val = findings.strip()
        detected_type = indices_outils.detect_indice_type(val)
        if detected_type:
            items_to_process.append((detected_type, val))
    elif isinstance(findings, dict):
        if 'type' in findings and ('original' in findings or 'normalized' in findings or 'value' in findings):
            t = str(findings['type'])
            v = str(findings.get('normalized') or findings.get('original') or findings.get('value') or '')
            if t and v:
                items_to_process.append((t, v))
        else:
            for k, val in findings.items():
                if isinstance(val, str) and val.strip():
                    k_lower = k.lower()
                    if k_lower in ('ip', 'ipv4', 'ipv6'):
                        items_to_process.append(('ip', val.strip()))
                    elif k_lower in ('domain', 'domaine', 'hostname', 'host'):
                        items_to_process.append(('domain', val.strip()))
                    elif k_lower in ('email', 'mail', 'courriel'):
                        items_to_process.append(('email', val.strip()))
                    elif k_lower in ('phone', 'tel', 'telephone'):
                        items_to_process.append(('phone', val.strip()))
                    elif k_lower in ('username', 'pseudo', 'user', 'handle'):
                        items_to_process.append(('username', val.strip()))
                    elif k_lower in ('url', 'link', 'lien'):
                        items_to_process.append(('url', val.strip()))
                    elif k_lower in ('image', 'photo', 'picture'):
                        items_to_process.append(('image', val.strip()))
                    elif k_lower in ('file', 'fichier', 'path'):
                        items_to_process.append(('file', val.strip()))
                    elif k_lower in ('hash', 'sha256', 'md5', 'sha1'):
                        items_to_process.append(('hash', val.strip()))
                    else:
                        det = indices_outils.detect_indice_type(val.strip())
                        if det:
                            items_to_process.append((det, val.strip()))

    for kind, val in items_to_process:
        if kind == 'email':
            # Exemple explicite du cap : email -> domaine -> holehe/maigret
            if '@' in val:
                local_part, domain_part = val.rsplit('@', 1)
                local_clean = re.sub(r'\+.*$', '', local_part)  # retirer alias +tag

                # 1. Analyse directe du compte e-mail
                suggestions.append(PivotSuggestion(
                    source_indicator=val,
                    source_type='email',
                    pivot_type='email',
                    pivot_value=val,
                    specialty='person',
                    recommended_tools=('holehe',),
                    activity='active',
                    explanation="Vérifier la création de comptes associés à cette adresse e-mail sur plus de 120 services en ligne sans clé API.",
                ))

                # 2. Pivot vers le nom de domaine
                suggestions.append(PivotSuggestion(
                    source_indicator=val,
                    source_type='email',
                    pivot_type='domain',
                    pivot_value=domain_part,
                    specialty='domain',
                    recommended_tools=('whois', 'dig', 'subfinder'),
                    activity='passive',
                    explanation=f"Rechercher le propriétaire, les serveurs MX et l'infrastructure du domaine messagerie '{domain_part}'.",
                ))

                # 3. Pivot vers le pseudonyme local
                suggestions.append(PivotSuggestion(
                    source_indicator=val,
                    source_type='email',
                    pivot_type='username',
                    pivot_value=local_clean,
                    specialty='social',
                    recommended_tools=('maigret', 'sherlock', 'social-analyzer'),
                    activity='active',
                    explanation=f"Rechercher l'existence du pseudonyme '{local_clean}' sur les réseaux sociaux et plateformes publiques.",
                ))

        elif kind == 'domain':
            # Pivot WHOIS & DNS passif
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='domain',
                pivot_type='domain',
                pivot_value=val,
                specialty='domain',
                recommended_tools=('whois', 'dig'),
                activity='passive',
                explanation="Consulter les serveurs de noms, le registrar, les contacts historiques et les enregistrements DNS passifs.",
            ))
            # Pivot énumération sous-domaines
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='domain',
                pivot_type='domain',
                pivot_value=val,
                specialty='domain',
                recommended_tools=('subfinder', 'dnsrecon', 'dnsenum'),
                activity='passive',
                explanation="Découvrir les sous-domaines exposés par Certificate Transparency et requêtes DNS ciblées.",
            ))
            # Pivot technologies web & infrastructure
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='domain',
                pivot_type='infra',
                pivot_value=val,
                specialty='infra',
                recommended_tools=('httpx', 'whatweb', 'wafw00f'),
                activity='active',
                explanation="Identifier les technologies HTTP, serveurs applicatifs et présence d'un WAF sur le domaine.",
            ))
            # Pivot archives web
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='domain',
                pivot_type='web_archive',
                pivot_value=val,
                specialty='web_archive',
                recommended_tools=('gau',),
                activity='passive',
                explanation="Récupérer l'historique des URLs archivées sur la Wayback Machine pour détecter d'anciens endpoints.",
            ))
            # Pivot fuites organisation
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='domain',
                pivot_type='person',
                pivot_value=val,
                specialty='person',
                recommended_tools=('theharvester',),
                activity='active',
                explanation="Collecter les adresses électroniques et collaborateurs publiquement liés au nom de domaine.",
            ))

        elif kind == 'ip':
            # Pivot WHOIS IP & ASN
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='ip',
                pivot_type='infra',
                pivot_value=val,
                specialty='infra',
                recommended_tools=('whois', 'dig'),
                activity='passive',
                explanation="Qualifier le bloc réseau (CIDR), le système autonome (ASN) et l'hébergeur responsable de l'adresse.",
            ))
            # Pivot reverse DNS
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='ip',
                pivot_type='domain',
                pivot_value=val,
                specialty='domain',
                recommended_tools=('dig',),
                activity='passive',
                explanation="Effectuer une résolution inverse (PTR) pour rattacher l'adresse IP à un nom de machine ou domaine.",
            ))
            # Pivot cartographie active de services
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='ip',
                pivot_type='infra',
                pivot_value=val,
                specialty='infra',
                recommended_tools=('nmap',),
                activity='active',
                explanation="Identifier les ports ouverts et services exposés (requiert l'accord explicite [o/N] de l'enquêteur).",
            ))

        elif kind in ('username', 'pseudo'):
            clean_user = val.lstrip('@')
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='username',
                pivot_type='username',
                pivot_value=clean_user,
                specialty='social',
                recommended_tools=('maigret', 'sherlock', 'social-analyzer'),
                activity='active',
                explanation=f"Cartographier les comptes publics associés au pseudonyme '{clean_user}' sur les réseaux sociaux.",
            ))
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='username',
                pivot_type='file',
                pivot_value=clean_user,
                specialty='leaks',
                recommended_tools=('gitleaks', 'trufflehog'),
                activity='passive',
                explanation=f"Rechercher d'éventuels dépôts publics ou fuites de code mentionnant l'identifiant '{clean_user}'.",
            ))

        elif kind == 'phone':
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='phone',
                pivot_type='phone',
                pivot_value=val,
                specialty='person',
                recommended_tools=('phoneinfoga',),
                activity='active',
                explanation="Identifier le pays, l'opérateur (carrier), le type de ligne (mobile/fixe/VoIP) et footprints publics.",
            ))

        elif kind == 'image':
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='image',
                pivot_type='image',
                pivot_value=val,
                specialty='media',
                recommended_tools=('exiftool',),
                activity='passive',
                explanation="Extraire les métadonnées EXIF : horodatage de prise de vue, coordonnées GPS, appareil et auteur.",
            ))
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='image',
                pivot_type='file',
                pivot_value=val,
                specialty='media',
                recommended_tools=('mat2', 'strings', 'binwalk'),
                activity='passive',
                explanation="Vérifier la présence de données cachées, stéganographie ou flux secondaires intégrés.",
            ))

        elif kind == 'url':
            parts = urlsplit(val)
            host = parts.hostname or ''
            if host:
                suggestions.append(PivotSuggestion(
                    source_indicator=val,
                    source_type='url',
                    pivot_type='domain',
                    pivot_value=host,
                    specialty='domain',
                    recommended_tools=('whois', 'dig', 'subfinder'),
                    activity='passive',
                    explanation=f"Extraire et analyser le nom d'hôte ou domaine '{host}' hébergeant l'URL.",
                ))
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='url',
                pivot_type='infra',
                pivot_value=val,
                specialty='infra',
                recommended_tools=('whatweb', 'wafw00f', 'httpx', 'curl'),
                activity='active',
                explanation="Auditer la réponse HTTP, les en-têtes de sécurité, le serveur web et la protection WAF.",
            ))
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='url',
                pivot_type='web_archive',
                pivot_value=val,
                specialty='web_archive',
                recommended_tools=('gau', 'photon'),
                activity='passive',
                explanation="Rechercher les versions antérieures de la page archivées sur le web.",
            ))

        elif kind == 'hash':
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='hash',
                pivot_type='file',
                pivot_value=val,
                specialty='leaks',
                recommended_tools=('gitleaks', 'trufflehog'),
                activity='passive',
                explanation="Comparer l'empreinte avec les banques de données de secrets compromis et artefacts forensiques.",
            ))

        elif kind == 'file':
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='file',
                pivot_type='file',
                pivot_value=val,
                specialty='media',
                recommended_tools=('exiftool', 'strings', 'binwalk'),
                activity='passive',
                explanation="Extraire les chaînes imprimables, métadonnées de création et structures de conteneurs archivés.",
            ))
            suggestions.append(PivotSuggestion(
                source_indicator=val,
                source_type='file',
                pivot_type='file',
                pivot_value=val,
                specialty='leaks',
                recommended_tools=('gitleaks', 'trufflehog'),
                activity='passive',
                explanation="Auditer le contenu du fichier pour détecter des clés cryptographiques privées ou tokens exposés.",
            ))

    return _deduplicate_pivots(suggestions)


def _deduplicate_pivots(pivots: list[PivotSuggestion]) -> list[PivotSuggestion]:
    """Déduplique les suggestions de pivots selon la cible, la spécialité et les outils."""
    seen: set[tuple[str, str, str, tuple[str, ...]]] = set()
    unique: list[PivotSuggestion] = []
    for p in pivots:
        key = (p.pivot_type, p.pivot_value, p.specialty, p.recommended_tools)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def extract_candidate_pivots(tool_name: str, stdout: str) -> list[dict]:
    """Extrait des pistes syntaxiquement valides, jamais une preuve d'identité.

    Contrat : type, value, tool, source (provenance), recommended_tool.
    Sortie bornée et dédupliquée ; aucune commande ni URL fournie par la sortie
    n'est interprétée comme une instruction.
    """
    import ipaddress
    import json
    import math

    if not isinstance(tool_name, str) or not isinstance(stdout, str):
        return []
    tool = tool_name.casefold()
    # Holehe répète l'adresse cible et liste des services, pas de nouvelles
    # entités attribuables à la cible. Même un statut positif reste à qualifier ;
    # les domaines des services et les liens du bandeau ne sont pas des pivots.
    # La sortie brute reste consignée par le parcours d'exécution.
    if tool == 'holehe':
        return []
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', stdout[:1_000_000])
    result, seen = [], set()

    def add(kind, value, source='stdout'):
        if len(result) >= 64:
            return
        if kind != 'gps':
            classified = indices_outils.classify(value, kind)
            if classified['validation'] != 'valid':
                return
            value = classified['normalized']
        key = (kind, value)
        if key in seen:
            if kind == 'username':
                row = next(row for row in result if (row['type'], row['value']) == key)
                if source not in row['sources']:
                    row['sources'].append(source)
            return
        seen.add(key)
        result.append(dict(type=kind, value=value, tool=tool, source=source, sources=[source],
                           recommended_tool={'email': 'holehe', 'domain': 'dig',
                                             'ip': 'whois', 'username': 'maigret',
                                             'gps': 'curl'}[kind]))

    def gps(lat, lon, source):
        def number(raw, axis):
            if isinstance(raw, bool):
                raise ValueError('GPS booléen')
            if isinstance(raw, (int, float)):
                return float(raw)
            match = re.fullmatch(r'''\s*([+-]?\d+(?:\.\d+)?)\s*(?:deg\s+(\d+(?:\.\d+)?)['′]\s*(\d+(?:\.\d+)?)["″])?\s*([NSEW])?\s*''', str(raw), re.I)
            if not match:
                raise ValueError('GPS invalide')
            degrees, minutes, seconds, hemisphere = match.groups()
            value = float(degrees)
            if minutes:
                if float(minutes) >= 60 or float(seconds) >= 60:
                    raise ValueError('DMS invalide')
                value = abs(value) + float(minutes) / 60 + float(seconds) / 3600
            if hemisphere:
                if hemisphere.upper() not in ('NS' if axis == 'lat' else 'EW'):
                    raise ValueError('Hémisphère invalide')
                value = abs(value) * (-1 if hemisphere.upper() in 'SW' else 1)
            return value
        try:
            a, b = number(lat, 'lat'), number(lon, 'lon')
            if math.isfinite(a) and math.isfinite(b) and abs(a) <= 90 and abs(b) <= 180:
                add('gps', f'{a:.6f}, {b:.6f}', source)
        except (ValueError, TypeError, OverflowError):
            pass

    emails = list(re.finditer(r"(?<![\w@.+-])[A-Za-z0-9_%+.'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,63}(?![\w@-])", text))
    for match in emails:
        add('email', match.group().rstrip('.'))
    # Ne pas confondre la partie domaine d'un email avec un hôte découvert.
    hosts_text = text
    for match in reversed(emails):
        hosts_text = hosts_text[:match.start()] + ' ' * len(match.group()) + hosts_text[match.end():]
    if tool not in ('exiftool', 'mat2', 'file', 'whatsmyname', 'blackbird'):
        for match in re.finditer(r'(?<![\w@./-])(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}(?![\w-]|\.[\w.-])', hosts_text):
            if tool != 'github' or match.group().lower() not in ('github.com', 'api.github.com'):
                add('domain', match.group().lower())
    for token in re.findall(r'(?<![\w.:])[0-9a-fA-F:.]{3,}(?![\w.:])', text):
        try:
            add('ip', str(ipaddress.ip_address(token.rstrip('.'))))
        except ValueError:
            pass

    if tool == 'exiftool':
        try:
            data = json.loads(text)
        except (ValueError, RecursionError):
            data = None
        for row in data if isinstance(data, list) else [data]:
            if isinstance(row, dict):
                values = {key.split(':')[-1]: val for key, val in row.items()}
                lat, lon = values.get('GPSLatitude'), values.get('GPSLongitude')
                if lat is not None and lon is not None:
                    if values.get('GPSLatitudeRef') in ('S', 'N'):
                        lat = f'{lat} {values["GPSLatitudeRef"]}'
                    if values.get('GPSLongitudeRef') in ('W', 'E'):
                        lon = f'{lon} {values["GPSLongitudeRef"]}'
                    gps(lat, lon, str(row.get('SourceFile', 'ExifTool'))[:200])
        # Réinitialiser les coordonnées entre deux fichiers ExifTool.
        for block in re.split(r'^========.*$', text, flags=re.M):
            lat = re.search(r'^\s*(?:\[.*?\]\s*)?GPS Latitude\s*:\s*(.+)$', block, re.M)
            lon = re.search(r'^\s*(?:\[.*?\]\s*)?GPS Longitude\s*:\s*(.+)$', block, re.M)
            if lat and lon:
                gps(lat[1], lon[1], 'ExifTool')

    if tool in ('whatsmyname', 'blackbird', 'github'):
        try:
            account_data = json.loads(text)
        except (ValueError, RecursionError):
            account_data = None
        account_lines = []
        def accounts(node, depth=0):
            if depth > 40:
                return
            if isinstance(node, list):
                for item in node:
                    accounts(item, depth + 1)
            elif isinstance(node, dict):
                positive = (node.get('exists') is True or node.get('found') is True
                            or str(node.get('status', '')).lower() == 'found')
                negative = (node.get('exists') is False or node.get('found') is False
                            or str(node.get('status', '')).lower() in ('not found', 'not_found', 'error'))
                if not negative and (positive or tool == 'github'):
                    for key in ('url', 'profile_url', 'html_url'):
                        if isinstance(node.get(key), str):
                            account_lines.append('[+] ' + node[key])
                    if tool == 'github' and isinstance(node.get('login'), str):
                        add('username', node['login'], 'GitHub login')
                for child in node.values():
                    if isinstance(child, (list, dict)):
                        accounts(child, depth + 1)
        accounts(account_data)
        # Un lien affiché sur une ligne négative n'est pas un compte trouvé.
        for line in account_lines if account_data is not None else text.splitlines():
            if re.search(r'not.?found|not.?exist|\bfalse\b|\[-\]|❌|\berror\b', line, re.I):
                continue
            if tool != 'github' and not re.search(r'\[\+\]|✔|\bfound\b|"(?:exists|found)"\s*:\s*true', line, re.I):
                continue
            for url in re.findall(r'https?://[^\s<>"\x27]+', line):
                try:
                    parts = urlsplit(url.rstrip('.,);'))
                    if parts.username or parts.password:
                        continue
                    segments = parts.path.strip('/').split('/')
                    host = (parts.hostname or '').lower().removeprefix('www.')
                    if host in ('github.com', 'twitter.com', 'x.com', 'instagram.com', 'tiktok.com') and len(segments) == 1:
                        user = segments[0].removeprefix('@')
                        if user.lower() not in ('login', 'search', 'explore', 'settings', 'signup'):
                            add('username', user, url[:500])
                    elif host == 'reddit.com' and len(segments) == 2 and segments[0] in ('u', 'user'):
                        add('username', segments[1], url[:500])
                except ValueError:
                    pass
    return result
