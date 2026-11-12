# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_welcome.py
# Role          : Banniere d'accueil, logo officiel et cartes des poles cyber
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Bannière d'accueil, logo vectoriel ASCII et cartes des 4 pôles cyber."""
from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.align import Align
from rich.table import Table
from rich.text import Text

from focus_banner_logo import banner_logo
from focus_teams import TEAMS, active_teams
from repl_theme import UITheme

VERSION = '1.0.0'
TAGLINE = "Assistant d'investigation Cyber, Forensic & OSINT sous Kali Linux"


def build_banner_logo(theme: UITheme) -> Text:
    """Construit le logo officiel UCHAMBUZI d'après les assets vectoriels uchambuzi-lockup-horizontal.svg."""
    return banner_logo(theme.primary, theme.text_dim)


_build_banner_logo = build_banner_logo


def render_teams_mini_grid(active_profile: Any = None) -> Table:
    """Affiche les 4 pôles cyber sous forme de petits rectangles compacts (haute lisibilité)."""
    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    def make_mini_card(num: str, slug: str, mode_id: str, icon: str, name: str, tools: str, color: str) -> Panel:
        is_active = bool(active_profile and getattr(active_profile, 'id', None) == mode_id)
        active_badge = " [bold green]✓ ACTIF[/]" if is_active else ""
        content = Text()
        content.append(f"{tools}", style="dim")
        content.no_wrap = True
        return Panel(
            content,
            title=f"[{color} bold][{num}] {name}[/]{active_badge}",
            title_align="left",
            border_style=color if is_active else "#334155",
            box=box.ROUNDED,
            padding=(0, 1),
        )

    cards = [make_mini_card(str(t.number), t.slug, t.mode_id, t.icon, t.name, t.tools_hint if t.available else "🔒 Bientôt", t.color) for t in TEAMS]
    grid.add_row(cards[0], cards[1])
    grid.add_row(cards[2], cards[3])
    return grid


def print_banner(
    console: Console,
    theme: UITheme,
    active_profile: Any = None,
    adapter: Any = None,
    session: Any = None,
    case_manager: Any = None,
) -> None:
    """Affiche la bannière officielle UCHAMBUZI en conformité avec les assets vectoriels."""
    logo_text = build_banner_logo(theme)

    heading = Text('U C H A M B U Z I', style=f'bold {theme.primary}')
    heading.append(f'   v{VERSION}', style=theme.text_dim)
    tagline = Text(TAGLINE, style=theme.text_dim)
    info = Text()
    spec_name = next((t.name for t in active_teams() if t.mode_id == getattr(active_profile, 'id', '')), 'Conversation')
    info.append('Spécialité : ', style='bold white')
    info.append(f'{spec_name}', style=f'bold {theme.secondary}')
    tagline_profile = getattr(active_profile, "tagline", "Investigation numérique") if active_profile else "Investigation numérique"
    info.append(f' — {tagline_profile}\n', style=theme.text_dim)

    ai_status = f'{adapter.model} (Ollama local)' if (session and getattr(adapter, 'model', None)) else 'Non configurée (fonctions locales actives)'
    info.append('Moteur IA  : ', style='bold white')
    info.append(f'{ai_status}\n', style=f'bold {theme.success}' if session else f'bold {theme.warning}')

    active_case_id = getattr(case_manager, 'active_case_id', None) if case_manager else None
    case_label = f'Dossier #{active_case_id} (actif)' if active_case_id else 'Session temporaire (hors dossier)'
    info.append('Enquête    : ', style='bold white')
    info.append(case_label, style='white')

    details = Group(tagline, Rule(style=theme.text_dim), info)
    if console.width >= 78:
        layout = Table.grid(padding=(0, 2))
        layout.add_column(width=22, no_wrap=True)
        layout.add_column(ratio=1)
        layout.add_row(logo_text, Group(heading, details))
        content = layout
    elif console.width >= 64:
        lockup = Table.grid(padding=(0, 3))
        lockup.add_column(width=22, no_wrap=True)
        lockup.add_column(vertical='middle')
        lockup.add_row(logo_text, heading)
        content = Group(lockup, details)
    else:
        content = Group(heading, details)

    panel = Panel(
        content,
        width=min(100, console.width),
        title=f'[bold {theme.primary}]◈ UCHAMBUZI[/] [dim]· Terminal d\'investigation[/]',
        subtitle=f'[dim][bold white]/help[/] commandes · [bold white]/team[/] pôles cyber · [bold white]Ctrl+D[/] quitter[/]',
        border_style=theme.primary,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(Align.center(panel))
    if console.width >= 80:
        console.print()
        console.print(render_teams_mini_grid(active_profile))
