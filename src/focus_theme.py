# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_theme.py
# Role          : Detection des capacites et palettes ANSI curses
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Couleurs contrôlées, fond explicite ; aucune sonde OSC ni hypothèse de thème."""
from dataclasses import dataclass, replace
import os
import sys
import unicodedata


@dataclass(frozen=True)
class TerminalStyle:
    depth: int
    unicode: bool
    theme: str

    @classmethod
    def detect(cls, values, *, env=None, stream=None, colors=None):
        env = os.environ if env is None else env
        stream = sys.stdout if stream is None else stream
        term = env.get('TERM', '')
        depth = 0
        if getattr(stream, 'isatty', lambda: False)() and term not in ('', 'dumb') and 'NO_COLOR' not in env:
            depth = 24 if term.endswith('-direct') or (colors is not None and colors >= 16777216) or env.get('COLORTERM', '').lower() in ('truecolor', '24bit') else 256 if (colors is not None and colors >= 256) or '256color' in term else 16
        request = values['colors']
        cap = {'mono': 0, '16': 16, '256': 256, 'truecolor': 24}.get(request, depth)
        ranks = {0: 0, 16: 1, 256: 2, 24: 3}
        depth = min((depth, cap), key=lambda d: ranks[d])
        if colors is not None:
            # ncurses direct color support is independent of COLORTERM.
            limit = 24 if colors >= 16777216 else 256 if colors >= 256 else 16 if colors >= 8 else 0
            depth = min((depth, limit), key=lambda d: ranks[d])
        try:
            '▸●─'.encode(getattr(stream, 'encoding', None) or 'ascii')
            unicode = True
        except (UnicodeError, LookupError):
            unicode = False
        unicode = unicode and values['unicode'] != 'off'
        return cls(depth, unicode, values['theme'])

    def text(self, text):
        if self.unicode:
            return text
        mapping = str.maketrans({'—': '-', '–': '-', '·': '.', '’': "'", '◆': '*', '›': '>', '▍': '|', '↕': '^', '─': '-', '│': '|', '┌': '+', '┐': '+', '└': '+', '┘': '+', '█': '_', '▸': '>', '●': 'o', '…': '.', '↑': '^', '↓': 'v', '↪': '>'})
        normalized = unicodedata.normalize('NFKD', text.translate(mapping))
        return ''.join(c for c in normalized if not unicodedata.combining(c)).encode('ascii', 'replace').decode()

    def ansi(self, text, role='accent'):
        from focus_ui import terminal_display
        text = self.text(terminal_display(text))
        if not self.depth:
            return text
        if self.depth == 24:
            code = ('38;2;170;57;15' if self.theme == 'light' else '38;2;232;93;38') if role == 'accent' else '38;2;13;27;42' if self.theme == 'light' else '38;2;226;232;240'
        elif self.depth == 256:
            code = ('38;5;130' if self.theme == 'light' else '38;5;166') if role == 'accent' else '38;5;234' if self.theme == 'light' else '38;5;254'
        else:
            code = ('31' if self.theme == 'light' else '33') if role == 'accent' else '30' if self.theme == 'light' else '37'
        return '\x1b['+code+'m'+text+'\x1b[0m'

    def curses_pairs(self, curses):
        if not self.depth:
            return False
        try:
            curses.start_color()
            bg = 15 if self.theme == 'light' and self.depth != 16 else 7 if self.theme == 'light' else 0
            fg = 0 if self.theme == 'light' else 7
            accent = (130 if self.theme == 'light' else 166) if self.depth == 256 else (0xaa390f if self.theme == 'light' else 0xe85d26) if self.depth == 24 else (1 if self.theme == 'light' else 3)
            error = (160 if self.theme == 'light' else 203) if self.depth == 256 else (0xb91c1c if self.theme == 'light' else 0xff3333) if self.depth == 24 else 1
            if self.depth == 24:
                bg, fg = (0xffffff, 0x0d1b2a) if self.theme == 'light' else (0x000000, 0xe2e8f0)
            for pair, color in ((1, accent), (2, fg), (3, error)):
                curses.init_pair(pair, color, bg)
            return True
        except curses.error:
            return False

    def configure_curses(self, curses):
        """Return effective style, falling back if a supposedly supported pair fails."""
        ranks = {0: 0, 16: 1, 256: 2, 24: 3}
        for depth in (24, 256, 16):
            if ranks[depth] <= ranks[self.depth]:
                candidate = replace(self, depth=depth)
                if candidate.curses_pairs(curses):
                    return candidate, True
        return replace(self, depth=0), False
