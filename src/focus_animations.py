# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_animations.py
# Role          : Transitions reelles non bloquantes et mouvement reduit
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Horloge consultative : aucun thread, sommeil, accès clavier ou fragment IA."""
import time


class Animations:
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.enabled = True
        self.reduced = False
        self.label = ''
        self.start = 0
        self.duration = 0
        self.glyph = ''

    def mode_event(self, event):
        hints = event.animation_hints
        self.begin('Mode : ' + event.new_mode_id, hints.get('glyph', ''), hints.get('duration_ms', 120)/1000)

    def scenario_event(self, event):
        hints = event.animation_hints
        self.begin('Scénario : ' + (event.new_scenario_id or 'libre'),
                   hints.get('glyph', ''), hints.get('duration_ms', 100)/1000)

    def begin(self, label, glyph='', duration=.12):
        self.label, self.glyph = label, str(glyph)
        self.start = self.clock()
        self.duration = max(0, min(.18, duration)) if self.enabled and not self.reduced else 0

    @property
    def active(self):
        return self.duration > 0 and self.clock() < self.start+self.duration

    def frame(self, *, unicode=True):
        if not self.active:
            return ''
        frame = min(2, int((self.clock()-self.start)/self.duration*3))
        return (self.glyph+' ' if unicode and self.glyph else '') + self.label + (' ·' if unicode else ' .')*(frame+1)
