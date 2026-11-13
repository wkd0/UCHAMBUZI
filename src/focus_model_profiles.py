# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_model_profiles.py
# Role          : Adaptateur de compatibilité pour les profils de fournisseurs IA
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Compatibilité des imports historiques vers les profils ai_calibration."""

from ai_calibration.providers import (
    ANTHROPIC,
    CLAUDE_SONNET,
    GENERIC,
    GROK,
    GROK_43,
    ModelProfile,
    OPENAI,
    OPENAI_LUNA,
    OPENAI_SOL,
    REDSAGE,
    resolve_model_profile,
)

__all__ = (
    'ANTHROPIC', 'CLAUDE_SONNET', 'GENERIC', 'GROK', 'GROK_43', 'ModelProfile',
    'OPENAI', 'OPENAI_LUNA', 'OPENAI_SOL', 'REDSAGE', 'resolve_model_profile',
)
