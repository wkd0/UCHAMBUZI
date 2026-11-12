# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_model_profiles.py
# Role          : Selection prudente des consignes par famille et modele IA
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Profils internes expérimentaux ; aucune option numérique non qualifiée.

La famille est une identité explicite, distincte du protocole de transport :
une passerelle compatible OpenAI servant Grok doit passer ``grok`` ou ``xai``.
Ce module ne sélectionne ni fournisseur, ni modèle, ni clé, et n'envoie rien.
Les instructions sont additives : les protections système restent prioritaires.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ModelProfile:
    id: str
    family: str
    instructions: str
    # Tuple immuable, vide tant qu'aucun réglage n'a été qualifié.
    options: tuple[tuple[str, object], ...] = ()
    experimental: bool = True

    def generation_options(self):
        """Retourne une copie adaptée à un fournisseur, sans état partagé."""
        return dict(self.options)


GENERIC = ModelProfile('generic', 'unknown', '', experimental=False)
REDSAGE = ModelProfile(
    'redsage-qwen3-8b-dpo', 'ollama',
    "Réponds d'abord à la question. Utilise les éléments effectivement fournis, "
    "signale les inconnues et ne déduis ni compromission ni attribution d'un indice isolé.",
)
OPENAI = ModelProfile(
    'openai-gpt', 'openai',
    "Réponds directement et adapte le niveau de détail à la demande. "
    "Distingue observations, hypothèses et limites sans inventer de vérification.",
)
ANTHROPIC = ModelProfile(
    'anthropic-claude', 'anthropic',
    "Commence par la réponse utile, puis développe seulement les précisions pertinentes. "
    "Distingue les données fournies des hypothèses et des actions proposées.",
)
GROK = ModelProfile(
    'xai-grok', 'xai',
    "Privilégie une réponse directe et vérifiable. Identifie les données manquantes "
    "et distingue une consultation réseau d'un fait déjà observé.",
)
OPENAI_LUNA = ModelProfile(
    'openai-gpt-6-luna', 'openai',
    OPENAI.instructions + ' Pour une consultation extérieure, distingue le réseau utilisé et le contact avec la cible.',
)
OPENAI_SOL = ModelProfile(
    'openai-gpt-6.1-sol', 'openai',
    OPENAI.instructions + ' Réserve les détails supplémentaires aux éléments utiles à la question.',
)
CLAUDE_SONNET = ModelProfile(
    'anthropic-sonnet', 'anthropic',
    ANTHROPIC.instructions + " Le champ executable=false indique une interdiction d'exécution, pas la nature du contenu.",
)
GROK_43 = ModelProfile(
    'xai-grok-4.3', 'xai',
    GROK.instructions + " Une consultation d'un tiers utilise le réseau même sans contacter directement la cible.",
)

_IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9._:/-]{0,199}\Z')
_OPENAI_MODEL = re.compile(r'(?:gpt-[a-z0-9][a-z0-9._-]*|o[1-9][a-z0-9._-]*)\Z')
_CLAUDE_MODEL = re.compile(r'(?:claude-[a-z0-9][a-z0-9._-]*|sonnet|opus|fable|haiku)\Z')
_GROK_MODEL = re.compile(r'grok-[a-z0-9][a-z0-9._-]*\Z')


def resolve_model_profile(family, model_id):
    """Retourne un profil connu ou le profil neutre, sans deviner une famille.

    ``family`` est l'identité réelle du fournisseur, pas l'URL ou le protocole.
    Un alias local n'est reconnu que sous le nom RedSage explicitement testé.
    Aucune option n'est ajoutée pour les modèles ou familles inconnus.
    """
    if not isinstance(family, str) or not isinstance(model_id, str):
        return GENERIC
    family, model_id = family.strip().casefold(), model_id.strip().casefold()
    if not _IDENTIFIER.fullmatch(model_id):
        return GENERIC
    if family == 'ollama' and model_id == 'redsage-qwen3:8b-dpo':
        return REDSAGE
    if family == 'openai' and model_id == 'gpt-6-luna':
        return OPENAI_LUNA
    if family == 'openai' and model_id == 'gpt-6.1-sol':
        return OPENAI_SOL
    if family == 'anthropic' and model_id in ('sonnet', 'claude-sonnet-5-5'):
        return CLAUDE_SONNET
    if family in ('grok', 'xai') and model_id in ('grok-4.3', 'grok-4.3-latest'):
        return GROK_43
    if family == 'openai' and _OPENAI_MODEL.fullmatch(model_id):
        return OPENAI
    if family == 'anthropic' and _CLAUDE_MODEL.fullmatch(model_id):
        return ANTHROPIC
    if family in ('grok', 'xai') and _GROK_MODEL.fullmatch(model_id):
        return GROK
    return GENERIC
