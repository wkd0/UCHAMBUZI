# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_settings_catalog.py
# Role          : Adaptation des catalogues 06 et 07 aux panneaux et moteur 08
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Contrats explicites ; aucun scénario ou modèle de remplacement inventé."""
from focus_orchestrator import FocusScenariosCatalog


class InteractiveCatalog:
    """Expose le catalogue 07 et adapte la recherche à la signature du contrôleur."""
    def __init__(self, source=None):
        self.source = FocusScenariosCatalog() if source is None else source
        self.manager = getattr(self.source, 'manager', None)

    def profiles(self):
        return self.source.profiles()

    def get_profile(self, profile_id):
        return self.source.get_profile(profile_id)

    def scenarios(self, profile_id=None):
        return self.source.scenarios(profile_id)

    def scenario_items(self, profile_id=None, *, include_free=True):
        if hasattr(self.source, 'scenario_items'):
            return self.source.scenario_items(profile_id, include_free=include_free)
        from focus_selectors import Item
        return ([Item('off', 'Conversation libre')] if include_free else []) + [Item(s.id,s.title,s.description) for s in self.scenarios(profile_id)]

    def mode_items(self):
        if hasattr(self.source, 'mode_items'):
            return self.source.mode_items()
        from focus_selectors import Item
        return [Item(p.id,p.name,p.instructions) for p in self.profiles()]

    def get_scenario(self, profile_id, scenario_id):
        if not isinstance(scenario_id, str):
            return None
        key = scenario_id.strip().casefold()
        # Legacy ID is an alias to an existing real scenario, never an extra item.
        if key == 'timeline':
            key = 'timeline_analysis'
        if hasattr(self.source, 'get_scenario'):
            return self.source.get_scenario(profile_id, key)
        return next((s for s in self.scenarios(profile_id)
                     if s.id.casefold() == key or s.title.casefold() == key), None)


class ScenarioInstructions:
    """Point d'injection de FocusAI.mode_engine, sans modifier le moteur 08.

    Le prompt complet de mission07 remplace le simple texte descriptif du scénario.
    Le même instantané est utilisé dans le consentement et dans le transport IA.
    """
    def __init__(self, manager):
        self.manager = manager
        self._pinned = None

    def __getattr__(self, name):
        return getattr(self.manager.mode_engine, name)

    def compose_active_instructions(self, *, active_scenario=None, **kwargs):
        return self._pinned if self._pinned is not None else self.manager.compose_active_instructions()

    def freeze(self):
        self._pinned = self.manager.compose_active_instructions()

    def unfreeze(self):
        self._pinned = None
