# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_branding.py
# Role          : Rendu du logo et accueil Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Identité terminal autonome ; les données d'accueil viennent de l'appelant."""
from __future__ import annotations

from dataclasses import dataclass
import os
import sys
import unicodedata
from typing import Mapping

# Dessin par cellules : o = scarification orange, autres traits = œil marine.
_FULL = (
    '                  ▰▰▰',
    '                ▰▰▰▰▰▰▰',
    '              ▰▰▰▰▰▰▰▰▰▰▰',
    '          ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄',
    '      ▄▄▀▀          │          ▀▀▄▄',
    '   ▄▀▀   o       ╭──┼──╮       o   ▀▀▄',
    '  ◀    o        ─┤  ●  ├─        o    ▶',
    '   ▀▄▄   o       ╰──┼──╯       o   ▄▄▀',
    '      ▀▀▄▄          │          ▄▄▀▀',
    '          ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀',
)
_COMPACT = (
    '          ▰▰▰',
    '         ▰▰▰▰▰',
    '    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄',
    '  ▄▀ o   ╭─┼─╮   o ▀▄',
    ' ◀  o   ─┤ ● ├─   o  ▶',
    '  ▀▄ o   ╰─┼─╯   o ▄▀',
    '    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀',
)
_ASCII = ('       ===', '      =====', '   .----------.', '  / .  -+-  .  \\', ' <  .  -O-  .   >', '  \\ .  -+-  .  /', "   '----------'")
_MINIMAL = ('  ▰▰▰', '◀ o⊕o ▶')
_ASCII_MIN = (' ===', '<.+.>')
_RESET = '\x1b[0m'
_ORANGE = '\x1b[38;2;232;93;38m'
_NAVY = '\x1b[38;2;13;27;42m'
_LIGHT = '\x1b[38;2;226;232;240m'


def cell_width(text: str) -> int:
    """Largeur prudente des cellules Unicode, hors contrôles et séquences ANSI."""
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def _clean(value: object, ascii_only: bool = False) -> str:
    text = ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C'))
    if ascii_only:
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'replace').decode('ascii')
    return text.strip()


def _clip(text: str, width: int) -> str:
    out = ''
    for char in text:
        if cell_width(out + char) > width:
            break
        out += char
    return out


def _center(text: str, width: int) -> str:
    return ' ' * max(0, (width - cell_width(text)) // 2) + text


def _color_line(line: str, crest: bool, theme: str) -> str:
    base = _NAVY if theme == 'light' else _LIGHT
    result = []
    current = None
    for char in line:
        color = _ORANGE if crest or char == 'o' else base
        if char != ' ' and color != current:
            result.append(color)
            current = color
        result.append('●' if char == 'o' else char)
    if current:
        result.append(_RESET)
    return ''.join(result)


def _monochrome(line: str, ascii_only: bool) -> str:
    return line if ascii_only else line.replace('o', '●')


def terminal_options(stream=None, env: Mapping[str, str] | None = None) -> tuple[bool, bool]:
    """Retourne (Unicode, TrueColor) selon le flux et l'environnement."""
    stream = sys.stdout if stream is None else stream
    env = os.environ if env is None else env
    encoding = getattr(stream, 'encoding', None) or 'ascii'
    try:
        '▰◀●'.encode(encoding)
        unicode_ok = True
    except (UnicodeError, LookupError):
        unicode_ok = False
    tty = bool(getattr(stream, 'isatty', lambda: False)())
    color = tty and 'NO_COLOR' not in env and env.get('TERM', '') not in ('', 'dumb') and env.get('COLORTERM', '').lower() in ('truecolor', '24bit')
    return unicode_ok, color


def render_logo(width: int, height: int = 100, *, unicode: bool = True,
                color: bool = False, theme: str = 'dark', variant: str = 'auto') -> list[str]:
    """Retourne des lignes centrées ; les options explicites sont la politique de l'appelant."""
    if theme not in ('dark', 'light') or variant not in ('auto', 'full', 'compact', 'minimal'):
        raise ValueError('Thème ou variante inconnu')
    if width <= 0 or height <= 0:
        return []
    candidates = [('full', _FULL), ('compact', _COMPACT), ('minimal', _MINIMAL)] if unicode else [('compact', _ASCII), ('minimal', _ASCII_MIN)]
    rank = {'full': 0, 'compact': 1, 'minimal': 2}
    candidates = [(name, art) for name, art in candidates if rank[name] >= rank.get(variant, 0)]
    for name, art in candidates:
        if variant == 'auto' and name == 'full' and width < 63:
            continue
        margin = min(len(line) - len(line.lstrip()) for line in art)
        art = tuple(line[margin:].rstrip() for line in art)
        if max(map(cell_width, art)) <= width and len(art) <= height:
            result = []
            for i, line in enumerate(art):
                prefix = ' ' * ((width - max(map(cell_width, art))) // 2)
                drawn = _color_line(line, i < (3 if name == 'full' else 2), theme) if color else _monochrome(line, not unicode)
                result.append(prefix + drawn)
            return result
    return []


@dataclass(frozen=True)
class WelcomeInfo:
    version: str | None = None
    model: str | None = None
    mode: str | None = None
    directory: str | None = None

    @classmethod
    def from_snapshot(cls, snapshot, *, version: str | None = None, mode: str | None = None, directory: str | None = None):
        model = snapshot.settings.model
        return cls(version, f'{model.provider} / {model.id}' if model else None, mode, directory)


def render_welcome(width: int, info: WelcomeInfo, *, height: int = 100, unicode: bool = True,
                   color: bool = False, theme: str = 'dark', conversation_started: bool = False) -> list[str]:
    """L'accueil disparaît après le premier échange ; aucune donnée n'est inventée."""
    if conversation_started or width <= 0 or height <= 0:
        return []
    lines = render_logo(width, max(0, height - 8), unicode=unicode, color=color, theme=theme)
    def safe(value):
        return _clean(value, not unicode) if value else ''
    entries = ['UCHAMBUZI FOCUS', 'Version : ' + (safe(info.version) or 'inconnue'),
               'Modèle IA : ' + (safe(info.model) or 'non renseigné'),
               'Mode professionnel : ' + (safe(info.mode) or 'non renseigné'),
               'Répertoire : ' + (safe(info.directory) or 'non renseigné'),
               'Commandes : /aide', '› Votre message' if unicode else '> Votre message']
    for entry in entries:
        entry = safe(entry)
        lines.append(_center(_clip(entry, width), width))
    return lines[:height]


class BrandLogo:
    """Adaptateur structurel BrandLogoExtension : lignes brutes, sans ANSI."""
    def __init__(self, *, unicode: bool = True):
        self.unicode = unicode

    def render_logo(self, width: int, height: int) -> list[str]:
        if width <= 0 or height <= 0:
            return []
        logo = render_logo(width, height - 1, unicode=self.unicode)
        return logo + [_center(_clip('UCHAMBUZI', width), width)]
