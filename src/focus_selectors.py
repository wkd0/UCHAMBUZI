# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_selectors.py
# Role          : Selecteurs clavier bornes et adaptatifs
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Sélecteur sans accès réseau ni dépendance à la machine d'état du tour IA."""
from dataclasses import dataclass
import curses


@dataclass(frozen=True)
class Item:
    id: str
    label: str
    description: str = ''
    unavailable: str = ''


class Selector:
    def __init__(self, title, items=(), *, selected=None, kind='mode'):
        self.title, self.items, self.kind = title, tuple(items), kind
        self.index = next((i for i, v in enumerate(self.items) if v.id == selected), 0)
        self.offset = 0
        self.reason = ''

    def handle_key(self, key, page_size=8):
        if key in ('\x1b', '\x03', 'q'):
            return 'cancel', None
        if key in ('\n', '\r', curses.KEY_ENTER):
            if self.items:
                item = self.items[self.index]
                if item.unavailable:
                    self.reason = item.unavailable
                else:
                    return 'select', item.id
            return None, None
        moves = {curses.KEY_UP: -1, curses.KEY_DOWN: 1, 'k': -1, 'j': 1,
                 curses.KEY_PPAGE: -page_size, curses.KEY_NPAGE: page_size}
        if self.items:
            if key in moves:
                self.index = max(0, min(len(self.items)-1, self.index + moves[key]))
            elif key == curses.KEY_HOME:
                self.index = 0
            elif key == curses.KEY_END:
                self.index = len(self.items)-1
        self.reason = ''
        return None, None

    def render(self, width, height, *, unicode=True):
        # Imported lazily to preserve the autonomous controller extension boundary.
        from focus_ui import clip_to_width, terminal_display
        width, height = max(1, width), max(1, height)
        clip = lambda s: clip_to_width(terminal_display(s), width)
        if not self.items:
            return [clip(self.title), clip('(Aucun élément disponible)'), clip('Esc : fermer')][:height]
        if height <= 2:
            return [clip(('> ' if not unicode else '▸ ') + self.items[self.index].label)][:height]
        rows = max(1, height-3)
        self.offset = max(0, min(self.offset, len(self.items)-rows))
        if self.index < self.offset:
            self.offset = self.index
        if self.index >= self.offset+rows:
            self.offset = self.index-rows+1
        result = [clip(f'{self.title} [{self.index+1}/{len(self.items)}]')]
        for i in range(self.offset, min(len(self.items), self.offset+rows)):
            v = self.items[i]
            marker = ('▸ ' if unicode else '> ') if i == self.index else '  '
            result.append(clip(marker + v.label + (' [indisponible]' if v.unavailable else '')))
        item = self.items[self.index]
        result += [clip(self.reason or item.unavailable or item.description), clip('↑↓ PgUp/PgDn Entrée · Esc annuler' if unicode else 'Up/Down PgUp/PgDn Enter Esc')]
        return result[:height]
