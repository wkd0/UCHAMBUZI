# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : __init__.py
# Role          : Accès aux guides de calibration des réponses IA
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Guides contextuels de réponse, communs aux fournisseurs pris en charge."""

from .response_guides import response_guide_for
from .providers import ModelProfile, resolve_model_profile

__all__ = ('ModelProfile', 'resolve_model_profile', 'response_guide_for')
