# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_render_cells.py
# Role          : Rendu visuel moderne style Claude Code (cellules, puces ⏺/⎿, tables)
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Bibliothèque de rendu visuel moderne style Claude Code pour UCHAMBUZI.

Fournit des composants de présentation épurés, lisibles et sans encadrés Panel :
- Puces d'étapes et indentation forensique (⏺ et ⎿)
- Résumés d'exécution d'outils avec troncature à 3 lignes et /details
- Entrées utilisateur sobres (> prompt) et amorces assistant
- Clés / valeurs alignées en grille (sans Panel)
- Tables minimales avec en-tête épuré (box.SIMPLE_HEAD)
- Détection et support complet de NO_COLOR et repli ASCII automatique
- Rendu responsive pour largeurs 60, 80 et 140+ colonnes
"""
from __future__ import annotations

import io
import os
import sys
from typing import Any, Mapping, Sequence

from rich import box
from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text


# ============================================================================
# Constantes graphiques et palettes TrueColor (Identité UCHAMBUZI)
# ============================================================================

COLOR_ORANGE = "#E85D26"        # Logo officiel et avertissements critiques
COLOR_CYAN = "#38BDF8"          # Dossier, contexte et accents secondaires
COLOR_SLATE = "#94A3B8"         # Gris ardoise (branches, détails, métadonnées)
COLOR_SLATE_LIGHT = "#CBD5E1"   # Texte adouci pour sorties courtes
COLOR_GREEN = "#10B981"         # Succès, validation et commandes exécutées
COLOR_AMBER = "#F59E0B"         # Précaution forensique
COLOR_RED = "#EF4444"           # Erreurs et alertes bloquantes
COLOR_WHITE = "#FFFFFF"         # Blanc éclatant pour titres
COLOR_BORDER = "#334155"        # Séparateurs discrets

# Glyphes Unicode
GLYPH_STEP_UNICODE = "⏺"
GLYPH_BRANCH_UNICODE = "⎿ "
GLYPH_DOT_UNICODE = "·"
GLYPH_PROMPT_UNICODE = "> "

# Glyphes de repli ASCII
GLYPH_STEP_ASCII = "*"
GLYPH_BRANCH_ASCII = "└ "
GLYPH_DOT_ASCII = "."
GLYPH_PROMPT_ASCII = "> "

# Style minimal ASCII pour tables épurées
SIMPLE_HEAD_ASCII = box.Box(
    "    \n"
    "    \n"
    " -- \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
    "    \n"
)

# Correspondance des styles de puces selon le type d'étape
STEP_COLOR_MAP: dict[str, str] = {
    # Succès / Commande -> vert
    "success": "bold #10B981",
    "command": "bold #10B981",
    "cmd": "bold #10B981",
    "exec": "bold #10B981",
    "ok": "bold #10B981",
    "done": "bold #10B981",
    "valid": "bold #10B981",
    # Précaution -> ambre / orange
    "warning": "bold #F59E0B",
    "precaution": "bold #F59E0B",
    "warn": "bold #F59E0B",
    "caution": "bold #F59E0B",
    "alert": "bold #E85D26",
    "attention": "bold #F59E0B",
    "danger": "bold #EF4444",
    # Dossier / Contexte -> cyan
    "case": "bold #38BDF8",
    "context": "bold #38BDF8",
    "dossier": "bold #38BDF8",
    "session": "bold #38BDF8",
    "investigation": "bold #38BDF8",
    # Pensée / Info -> dim / gris ardoise
    "thought": "dim",
    "thinking": "dim",
    "info": "#94A3B8",
    "dim": "dim",
    "debug": "dim",
    "trace": "dim",
    # Erreur -> rouge
    "error": "bold #EF4444",
    "fail": "bold #EF4444",
    "failure": "bold #EF4444",
}


# ============================================================================
# Fonctions de détection environnement (Accessibilité, UTF-8, NO_COLOR)
# ============================================================================

def is_no_color(env: Mapping[str, str] | None = None) -> bool:
    """Détecte si la désactivation des couleurs est demandée (standard no-color.org)."""
    target_env = os.environ if env is None else env
    return "NO_COLOR" in target_env and target_env["NO_COLOR"] != ""


def is_ascii_mode(console: Console | None = None, env: Mapping[str, str] | None = None) -> bool:
    """Détecte si un repli ASCII est nécessaire pour le terminal courant."""
    target_env = os.environ if env is None else env

    if target_env.get("UCHAMBUZI_ASCII") in ("1", "true", "yes", "on"):
        return True
    if target_env.get("NO_UNICODE") in ("1", "true", "yes", "on"):
        return True

    lc_all = target_env.get("LC_ALL", "")
    lang = target_env.get("LANG", "")
    if lc_all in ("C", "POSIX") or (not lc_all and lang in ("C", "POSIX")):
        return True

    if console is not None:
        enc = getattr(console, "encoding", None)
        if isinstance(enc, str):
            enc_lower = enc.lower().replace("-", "").replace("_", "")
            if "ascii" in enc_lower or enc_lower == "c":
                return True
        file_obj = getattr(console, "file", None)
        if file_obj is not None:
            file_enc = getattr(file_obj, "encoding", None)
            if isinstance(file_enc, str):
                try:
                    "⏺⎿·".encode(file_enc)
                except (UnicodeEncodeError, LookupError):
                    return True

    for stream in (sys.stdout, sys.stderr):
        encoding = getattr(stream, "encoding", None)
        if isinstance(encoding, str):
            clean = encoding.lower().replace("-", "").replace("_", "")
            if "ascii" in clean:
                return True
            try:
                "⏺⎿·".encode(encoding)
            except (UnicodeEncodeError, LookupError):
                return True

    default_enc = sys.getdefaultencoding().lower().replace("-", "").replace("_", "")
    if "ascii" in default_enc:
        return True

    return False


def get_step_glyph(ascii_mode: bool = False) -> str:
    """Retourne la puce d'étape (⏺ ou *)."""
    return GLYPH_STEP_ASCII if ascii_mode else GLYPH_STEP_UNICODE


def get_branch_glyph(ascii_mode: bool = False) -> str:
    """Retourne la branche de sous-détail (⎿  ou └ )."""
    return GLYPH_BRANCH_ASCII if ascii_mode else GLYPH_BRANCH_UNICODE


def get_dot_glyph(ascii_mode: bool = False) -> str:
    """Retourne le point séparateur (· ou .)."""
    return GLYPH_DOT_ASCII if ascii_mode else GLYPH_DOT_UNICODE


def to_plain_text(renderable: RenderableType, width: int = 100) -> str:
    """Convertit un objet de rendu en texte brut sans codes d'échappement ANSI."""
    buf = io.StringIO()
    console = Console(file=buf, record=True, width=width)
    console.print(renderable)
    return console.export_text()


# ============================================================================
# Fonctions de rendu visuel
# ============================================================================

def render_step(
    console: Console | None,
    step_type: str,
    title: str,
    detail: str = "",
    *,
    force_ascii: bool | None = None,
) -> RenderableType:
    """Affiche et retourne une étape d'analyse stylée.

    Puce colorée : vert (succès/commande), ambre (précaution),
    cyan (dossier/contexte), dim (pensée/info).
    Sous-détail indenté avec ⎿  en gris ardoise.
    """
    ascii_mode = is_ascii_mode(console) if force_ascii is None else force_ascii
    bullet_glyph = get_step_glyph(ascii_mode)
    branch_glyph = get_branch_glyph(ascii_mode)

    step_key = step_type.lower().strip()
    no_col = is_no_color()
    bullet_style = "" if no_col else STEP_COLOR_MAP.get(step_key, "bold #38BDF8")
    title_style = "" if no_col else ("dim #CBD5E1" if step_key in ("thought", "thinking", "dim", "debug") else "bold white")
    slate_style = "" if no_col else COLOR_SLATE

    title_text = Text()
    title_text.append(bullet_glyph, style=bullet_style)
    title_text.append(f" {title}", style=title_style)

    if detail and str(detail).strip():
        lines = str(detail).strip().splitlines()
        branch_text = Text()
        branch_text.append(branch_glyph, style=slate_style)
        branch_text.append(lines[0], style=slate_style)

        renderables: list[RenderableType] = [title_text, branch_text]
        for line in lines[1:]:
            cont_text = Text()
            cont_text.append("  ", style=slate_style)
            cont_text.append(line, style=slate_style)
            renderables.append(cont_text)

        result: RenderableType = Group(*renderables)
    else:
        result = title_text

    if console is not None:
        console.print(result)
    return result


def render_tool_summary(
    console: Console | None,
    tool_name: str,
    args: str,
    lines: Sequence[str] | str | None,
    identifier: int | str,
    duration: float,
    exit_code: int = 0,
    *,
    force_ascii: bool | None = None,
) -> RenderableType:
    """Affiche et retourne le résumé compact d'exécution d'un outil forensique.

    - ⏺ <tool_name>(<args>)
    - ⎿ <résultat court sur 1 à 3 lignes>
    - Si plus de 3 lignes : + N lignes · /details <identifier> (ou Ctrl+O) pour développer
    - Pied : code <exit_code> · <duration:.2f>s · consigné au dossier
    """
    ascii_mode = is_ascii_mode(console) if force_ascii is None else force_ascii
    bullet_glyph = get_step_glyph(ascii_mode)
    branch_glyph = get_branch_glyph(ascii_mode)
    dot_glyph = get_dot_glyph(ascii_mode)

    bullet_style = "bold #10B981" if exit_code == 0 else "bold #EF4444"

    header_text = Text()
    header_text.append(bullet_glyph, style=bullet_style)
    header_text.append(f" {tool_name}", style="bold white")

    args_str = str(args) if args is not None else ""
    if args_str:
        if args_str.startswith("(") and args_str.endswith(")"):
            header_text.append(args_str, style=COLOR_SLATE)
        else:
            header_text.append(f"({args_str})", style=COLOR_SLATE)
    else:
        header_text.append("()", style=COLOR_SLATE)

    if isinstance(lines, str):
        lines_list = lines.splitlines()
    elif lines is None:
        lines_list = []
    else:
        lines_list = [str(x) for x in lines]

    elements: list[RenderableType] = [header_text]

    if not lines_list:
        empty_text = Text()
        empty_text.append(branch_glyph, style=COLOR_SLATE)
        empty_text.append("(aucun retour)", style="dim " + COLOR_SLATE)
        elements.append(empty_text)
    else:
        for idx, line in enumerate(lines_list[:3]):
            line_text = Text()
            if idx == 0:
                line_text.append(branch_glyph, style=COLOR_SLATE)
            else:
                line_text.append("  ", style=COLOR_SLATE)
            line_text.append(str(line), style=COLOR_SLATE_LIGHT)
            elements.append(line_text)

        if len(lines_list) > 3:
            remaining = len(lines_list) - 3
            more_text = Text()
            more_text.append("  + ", style="dim " + COLOR_SLATE)
            more_text.append(f"{remaining} lignes ", style="dim " + COLOR_SLATE)
            more_text.append(f"{dot_glyph} ", style="dim " + COLOR_SLATE)
            more_text.append(f"/details {identifier} (ou Ctrl+O) pour développer", style="dim " + COLOR_SLATE)
            elements.append(more_text)

    footer_text = Text()
    footer_text.append("  code ", style="dim " + COLOR_SLATE)
    code_color = COLOR_GREEN if exit_code == 0 else COLOR_RED
    footer_text.append(str(exit_code), style=code_color)
    footer_text.append(f" {dot_glyph} {duration:.2f}s {dot_glyph} consigné au dossier", style="dim " + COLOR_SLATE)
    elements.append(footer_text)

    result = Group(*elements)
    if console is not None:
        console.print(result)
    return result


def render_user_prompt(
    console: Console | None,
    text: str,
    *,
    force_ascii: bool | None = None,
) -> RenderableType:
    """Rendu sobre du message saisi par l'utilisateur (> <text>)."""
    raw_text = str(text) if text is not None else ""
    lines = raw_text.splitlines() or [""]

    prompt_text = Text()
    prompt_text.append("> ", style="bold " + COLOR_SLATE)
    prompt_text.append(lines[0], style="bold white")

    for line in lines[1:]:
        prompt_text.append("\n")
        prompt_text.append("  ", style=COLOR_SLATE)
        prompt_text.append(line, style="bold white")

    if console is not None:
        console.print(prompt_text)
    return prompt_text


def render_assistant_lead(
    console: Console | None,
    *,
    end: str = "\n",
    force_ascii: bool | None = None,
) -> RenderableType:
    """Marqueur discret de début de réponse de l'assistant (simple puce ⏺)."""
    ascii_mode = is_ascii_mode(console) if force_ascii is None else force_ascii
    bullet_glyph = get_step_glyph(ascii_mode)

    lead_text = Text(bullet_glyph, style="bold " + COLOR_CYAN)

    if console is not None:
        console.print(lead_text, end=end)
    return lead_text


def render_kv(
    console: Console | None,
    title: str,
    items: Sequence[tuple[str, Any]] | Mapping[str, Any],
    style_title: str = "bold white",
    *,
    force_ascii: bool | None = None,
) -> RenderableType:
    """Affiche une liste clé/valeur parfaitement alignée sans aucun encadré Panel."""
    if isinstance(items, Mapping):
        item_list = list(items.items())
    else:
        item_list = list(items)

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=COLOR_SLATE, justify="left")
    grid.add_column(style=COLOR_WHITE, justify="left")

    for k, v in item_list:
        grid.add_row(f"  {k}", str(v))

    if title and title.strip():
        title_text = Text(title.strip(), style=style_title)
        result: RenderableType = Group(title_text, grid)
    else:
        result = grid

    if console is not None:
        console.print(result)
    return result


def render_minimal_table(
    console: Console | None,
    title: str,
    columns: Sequence[dict[str, Any] | str],
    rows: Sequence[Sequence[Any]],
    *,
    force_ascii: bool | None = None,
) -> Table:
    """Rendu de tableau épuré sans bordure externe (box.SIMPLE_HEAD)."""
    ascii_mode = is_ascii_mode(console) if force_ascii is None else force_ascii
    box_style = SIMPLE_HEAD_ASCII if ascii_mode else box.SIMPLE_HEAD

    clean_title = title.strip() if title and title.strip() else None

    table = Table(
        title=clean_title,
        title_style="bold " + COLOR_CYAN,
        title_justify="left",
        box=box_style,
        show_edge=False,
        show_header=True,
        header_style="bold " + COLOR_CYAN,
        border_style=COLOR_BORDER,
        pad_edge=False,
        collapse_padding=True,
    )

    for col in columns:
        if isinstance(col, str):
            table.add_column(col, header_style="bold " + COLOR_CYAN)
        elif isinstance(col, dict):
            header = str(col.get("header") or col.get("name") or col.get("title") or "")
            justify = col.get("justify", "left")
            style = col.get("style", None)
            header_style = col.get("header_style", "bold " + COLOR_CYAN)
            no_wrap = col.get("no_wrap", False)
            width = col.get("width")
            min_width = col.get("min_width")
            max_width = col.get("max_width")
            table.add_column(
                header,
                justify=justify,
                style=style,
                header_style=header_style,
                no_wrap=no_wrap,
                width=width,
                min_width=min_width,
                max_width=max_width,
            )
        else:
            table.add_column(str(col), header_style="bold " + COLOR_CYAN)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    if console is not None:
        console.print(table)
    return table
