# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_theme.py
# Role          : Gestion des palettes de couleurs et glyphes visuels du REPL
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Palettes visuelles haute lisibilité et système de glyphes adaptatif."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any


@dataclass(frozen=True)
class UITheme:
    """Définition d'une palette visuelle pour le REPL."""
    name: str
    label: str
    description: str
    primary: str        # Bordures, logos, titre principal
    secondary: str      # Cibles, indices, accent secondaire
    app_bg: str         # Fond global de l’application et du terminal hôte
    text_main: str      # Texte principal (blanc éclatant)
    text_dim: str       # Texte secondaire (gris très clair, haute lisibilité)
    success: str        # Vert succès
    warning: str        # Jaune ambre
    danger: str         # Rouge alerte
    menu_bg: str        # Fond de base du menu d'autocomplétion
    menu_meta_bg: str   # Fond de la colonne description
    toolbar_bg: str     # Fond de la barre d'état
    toolbar_fg: str     # Texte de la barre d'état

    @property
    def id(self) -> str:
        return self.name


THEMES: dict[str, UITheme] = {
    'focus': UITheme(
        name='focus',
        app_bg='#0D1B2A',
        label='Focus Défaut (Bleu Cyan & Orange WKD)',
        description='Palette officielle UCHAMBUZI avec logo orange éclatant et contrastes cyan',
        primary='#E85D26',
        secondary='#38BDF8',
        text_main='#FFFFFF',
        text_dim='#94A3B8',
        success='#10B981',
        warning='#F59E0B',
        danger='#EF4444',
        menu_bg='#0D1B2A',
        menu_meta_bg='#1E293B',
        toolbar_bg='#DDEAF5',
        toolbar_fg='#000000',
    ),
    'matrix': UITheme(
        name='matrix',
        app_bg='#05100A',
        label='Cyber Matrix (Vert Phosphore)',
        description='Inspiration hacker terminal avec verts intenses et noirs profonds',
        primary='#00FF66',
        secondary='#22D3EE',
        text_main='#FFFFFF',
        text_dim='#A7F3D0',
        success='#00FF66',
        warning='#FDE047',
        danger='#F87171',
        menu_bg='#064E3B',
        menu_meta_bg='#022C22',
        toolbar_bg='#B5E8C7',
        toolbar_fg='#000000',
    ),
    'dracula': UITheme(
        name='dracula',
        app_bg='#282A36',
        label='Dracula Synth (Pourpre & Rose)',
        description='Palette violette et rose néon pour développeurs',
        primary='#BD93F9',
        secondary='#FF79C6',
        text_main='#F8F8F2',
        text_dim='#8BE9FD',
        success='#50FA7B',
        warning='#F1FA8C',
        danger='#FF5555',
        menu_bg='#282A36',
        menu_meta_bg='#1E1F29',
        toolbar_bg='#E0D3F5',
        toolbar_fg='#000000',
    ),
    'claude': UITheme(
        name='claude',
        app_bg='#1F1E1B',
        label='Claude Code (Terracotta & Sauge)',
        description='Inspiration Claude Code avec teintes chaleureuses terracotta et sauge',
        primary='#CC785C',
        secondary='#85A894',
        text_main='#ECECEC',
        text_dim='#9CA3AF',
        success='#4EAA7A',
        warning='#FBBF24',
        danger='#E06C75',
        menu_bg='#18181A',
        menu_meta_bg='#242428',
        toolbar_bg='#EBD7CE',
        toolbar_fg='#000000',
    ),
    'codex': UITheme(
        name='codex',
        app_bg='#0D1117',
        label='Codex Dark (Émeraude & Mint)',
        description='Inspiration OpenAI Codex CLI avec émeraude profond et mint contrasté',
        primary='#10A37F',
        secondary='#6EE7B7',
        text_main='#ECECEC',
        text_dim='#8E8EA0',
        success='#10B981',
        warning='#F59E0B',
        danger='#EF4444',
        menu_bg='#111113',
        menu_meta_bg='#1D1D21',
        toolbar_bg='#C8E9DE',
        toolbar_fg='#000000',
    ),
    'nord': UITheme(
        name='nord',
        app_bg='#2E3440',
        label='Nordic Frost (Bleus Polaires)',
        description='Nuances arctiques calmes et hautement contrastées',
        primary='#88C0D0',
        secondary='#81A1C1',
        text_main='#ECEFF4',
        text_dim='#D8DEE9',
        success='#A3BE8C',
        warning='#EBCB8B',
        danger='#BF616A',
        menu_bg='#2E3440',
        menu_meta_bg='#3B4252',
        toolbar_bg='#D8E6EB',
        toolbar_fg='#000000',
    ),
    'amber': UITheme(
        name='amber',
        app_bg='#120A00',
        label='Ambre CRT (Rétro Moniteur)',
        description='Esthétique chaleureuse des écrans phosphore ambre',
        primary='#FFB000',
        secondary='#FFD166',
        text_main='#FFFFFF',
        text_dim='#FEF3C7',
        success='#10B981',
        warning='#F59E0B',
        danger='#EF4444',
        menu_bg='#3D2700',
        menu_meta_bg='#261800',
        toolbar_bg='#F7DFAD',
        toolbar_fg='#000000',
    ),
    'high-contrast': UITheme(
        name='high-contrast',
        app_bg='#000000',
        label='High Contrast (Accessibilité Maximale)',
        description='Blanc pur sur fond noir absolu, zéro dégradé',
        primary='#FFFFFF',
        secondary='#FACC15',
        text_main='#FFFFFF',
        text_dim='#E5E7EB',
        success='#4ADE80',
        warning='#FACC15',
        danger='#F87171',
        menu_bg='#000000',
        menu_meta_bg='#18181B',
        toolbar_bg='#FFFFFF',
        toolbar_fg='#000000',
    ),
}

DEFAULT_THEME_ID = 'focus'


def load_theme_preference() -> str:
    """Charge le thème choisi par l'utilisateur s'il existe."""
    path = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'uchambuzi-data' / 'config' / 'theme.json'
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            theme_name = data.get('theme')
            if theme_name in THEMES:
                return theme_name
        except Exception:
            pass
    return DEFAULT_THEME_ID


def save_theme_preference(theme_name: str) -> None:
    """Sauvegarde le thème choisi de manière persistante."""
    path = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'uchambuzi-data' / 'config' / 'theme.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps({'theme': theme_name}, indent=2), encoding='utf-8')
    except Exception:
        pass


def is_utf8_supported() -> bool:
    """Détecte si la sortie standard supporte l'encodage UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, 'encoding', None)
        if encoding:
            clean = encoding.lower().replace('-', '').replace('_', '')
            if 'utf8' in clean:
                return True
            if 'ascii' in clean:
                return False
    default_enc = sys.getdefaultencoding().lower().replace('-', '').replace('_', '')
    return 'utf8' in default_enc


def is_no_color() -> bool:
    """Détecte la variable d'environnement NO_COLOR (standard https://no-color.org)."""
    return bool(os.environ.get('NO_COLOR'))


@dataclass(frozen=True)
class GlyphSet:
    """Ensemble de glyphes graphiques avec support UTF-8 ou ASCII pur."""
    is_utf8: bool
    step: str
    branch: str
    prompt: str
    spinner: tuple[str, ...]
    check: str
    cross: str
    pointer: str
    bullet_dot: str
    bullet_small: str
    corner: str
    tree_tee: str
    diamond: str
    arrow_left: str
    arrow_right: str

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


UNICODE_GLYPHS = GlyphSet(
    is_utf8=True,
    step='⏺',
    branch='⎿',
    prompt='❯',
    spinner=('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'),
    check='✓',
    cross='✗',
    pointer='›',
    bullet_dot='●',
    bullet_small='•',
    corner='└',
    tree_tee='├',
    diamond='◈',
    arrow_left='◀',
    arrow_right='▶',
)

ASCII_GLYPHS = GlyphSet(
    is_utf8=False,
    step='*',
    branch='|',
    prompt='>',
    spinner=('-', '\\', '|', '/'),
    check='OK',
    cross='X',
    pointer='>',
    bullet_dot='*',
    bullet_small='-',
    corner='\\',
    tree_tee='+',
    diamond='#',
    arrow_left='<',
    arrow_right='>',
)


def get_glyphs(utf8: bool | None = None) -> GlyphSet:
    """Retourne l'ensemble de glyphes adapté à l'encodage du terminal."""
    if utf8 is None:
        utf8 = is_utf8_supported()
    return UNICODE_GLYPHS if utf8 else ASCII_GLYPHS


GLYPHS: GlyphSet = get_glyphs()
