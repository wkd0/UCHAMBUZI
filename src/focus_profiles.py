# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_profiles.py
# Role          : Interface des profils Focus et pont vers le moteur des modes
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Pont d'integration des profils Focus vers le moteur des huit modes.

Fournit l'interface de profils prevue par l'architecture Focus v1 tout en
s'appuyant sur l'implementation concrete du moteur de modes professionnels.
"""
from __future__ import annotations

from typing import Sequence

from focus_contracts import Catalog, Profile, Scenario
from focus_modes import (
    BUILTIN_MODES,
    DEFAULT_MODE_ID,
    FocusMode,
    FocusModesCatalog,
    InstructionComposer,
    ModeEngine,
    ModeRegistry,
    ModeTransitionEvent,
    ORDERED_BUILTIN_MODE_IDS,
    create_default_mode_engine,
)

# Export tuple officiel des huit profils Focus
DEFAULT_PROFILES: tuple[Profile, ...] = tuple(
    BUILTIN_MODES[mode_id].to_profile() for mode_id in ORDERED_BUILTIN_MODE_IDS
)


class FocusProfilesCatalog(Catalog):
    """Catalogue de profils et scenarios pour Focus conforme au contrat Catalog."""

    def __init__(self, engine: ModeEngine | None = None):
        self._engine = engine or create_default_mode_engine()
        self._catalog = FocusModesCatalog(self._engine)

    def profiles(self) -> Sequence[Profile]:
        """Retourne la liste ordonnee des huit profils professionnels."""
        return self._catalog.profiles()

    def scenarios(self, profile_id: str | None = None) -> Sequence[Scenario]:
        """Retourne les scenarios compatibles avec le profil ou l'ensemble."""
        try:
            from focus_scenarios import create_default_scenario_registry
            reg = create_default_scenario_registry()
            return tuple(s.to_contract_scenario() for s in (reg.list_visible_scenarios(mode_id=profile_id) if profile_id in (None, 'intel') else reg.list_scenarios(mode_id=profile_id)))
        except Exception:
            return self._catalog.scenarios(profile_id=profile_id)

    def get_profile(self, profile_id: str) -> Profile | None:
        """Recupere un profil specifique."""
        return self._catalog.get_profile(profile_id)

    def get_scenario(self, profile_id_or_scenario: str, scenario_id: str | None = None) -> Scenario | None:
        """Recupere un scenario compatible avec le profil specifie ou par identifiant."""
        return self._catalog.get_scenario(profile_id_or_scenario, scenario_id)

    def scenario_items(self, profile_id: str | None = None, *, include_free: bool = True) -> list[Any]:
        """Retourne les elements adaptes aux selecteurs TUI (Mission 11)."""
        items: list[Any] = []
        if include_free:
            try:
                from focus_selectors import Item
                items.append(Item('off', 'Conversation libre', 'Dialogue sans contrainte de scenario'))
            except ImportError:
                items.append(('off', 'Conversation libre', 'Dialogue sans contrainte de scenario'))
        for s in self.scenarios(profile_id=profile_id):
            try:
                from focus_selectors import Item
                items.append(Item(s.id, s.title, s.description))
            except ImportError:
                items.append((s.id, s.title, s.description))
        return items

    def mode_items(self) -> list[Any]:
        """Retourne les modes adaptes aux selecteurs TUI (Mission 11)."""
        items: list[Any] = []
        for p in self.profiles():
            try:
                from focus_selectors import Item
                items.append(Item(p.id, p.name, p.instructions))
            except ImportError:
                items.append((p.id, p.name, p.instructions))
        return items

    @property
    def engine(self) -> ModeEngine:
        """Accede au moteur de modes sous-jacent."""
        return self._engine


def get_default_profiles() -> tuple[Profile, ...]:
    """Retourne la liste immuable des profils par defaut."""
    return DEFAULT_PROFILES
