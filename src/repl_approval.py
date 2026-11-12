# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_approval.py
# Role          : Module d'approbation humaine forensique interactif (Rich & PromptToolkit)
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Module d'approbation humaine forensique interactif pour UCHAMBUZI.

Fournit une interface épurée sous PromptToolkit (sans plein écran)
permettant à l'enquêteur de valider ou refuser explicitement l'exécution
d'une commande technique.

RÈGLE DE SÉCURITÉ FORENSIQUE ABSOLUE :
Le choix 'Non (Échap)' est TOUJOURS pré-sélectionné par défaut (index = 1).
Toute interruption, exception, Échap ou validation directe sans sélection
résulte en un refus strict (False).
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Sequence

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style as PtStyle
from prompt_toolkit.utils import get_cwidth


# ============================================================================
# Constantes et Libellés Forensiques
# ============================================================================

CHOICE_YES = "Oui, exécuter et consigner au dossier"
CHOICE_NO = "Non (Échap)"
DEFAULT_CHOICE_INDEX = 1  # 0 = Oui, 1 = Non (RÈGLE FORENSIQUE : Non par défaut)

# Caractères d'encadré épuré (box.ROUNDED)
BORDER_TOP_LEFT = "╭"
BORDER_TOP_RIGHT = "╮"
BORDER_BOTTOM_LEFT = "╰"
BORDER_BOTTOM_RIGHT = "╯"
BORDER_HORIZONTAL = "─"
BORDER_VERTICAL = "│"
BORDER_DIVIDER_LEFT = "├"
BORDER_DIVIDER_RIGHT = "┤"

# Palette TrueColor UCHAMBUZI
DEFAULT_STYLE_DICT = {
    "approval.border": "#e85d26 bold",               # Orange éclatant UCHAMBUZI
    "approval.title": "#38bdf8 bold",                # Cyan éclatant
    "approval.label": "#94a3b8 bold",                # Ardoise soutenu
    "approval.tool": "#38bdf8 bold",                 # Cyan
    "approval.command": "#ffffff bold bg:#0d1b2a",   # Commande contrastée sur bleu nuit
    "approval.warning": "#f59e0b bold",              # Ambre / Précaution forensique
    "approval.question": "#ffffff bold",             # Blanc pur
    "approval.choice.normal": "#94a3b8",             # Ardoise standard
    "approval.choice.selected": "bold bg:#e85d26 fg:#ffffff",  # Surlignage orange officiel
    "approval.cursor": "#e85d26 bold",               # Curseur actif
    "approval.hint": "#64748b italic",               # Aide discrète
    "approval.divider": "#334155",                   # Ligne séparatrice discrète
}


# ============================================================================
# Utilitaires de Calibrage et de Découpage
# ============================================================================

def get_box_width(output: Any = None) -> int:
    """Calcule la largeur idéale pour l'encadré selon le terminal courant."""
    cols = 80
    try:
        if output is not None and hasattr(output, "get_size"):
            size = output.get_size()
            if getattr(size, "columns", None):
                cols = size.columns
        else:
            cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        cols = 80
    return max(60, min(cols - 4, 100))


def wrap_text_cwidth(text: str, max_width: int) -> list[str]:
    """Découpe un texte en lignes respectant une largeur visible maximale."""
    if max_width <= 4:
        return [text]
    paragraphs = text.split("\n")
    all_lines: list[str] = []
    for para in paragraphs:
        if not para:
            all_lines.append("")
            continue
        words = para.split(" ")
        curr_words: list[str] = []
        curr_width = 0
        for word in words:
            w_width = sum(get_cwidth(c) for c in word)
            if w_width > max_width:
                if curr_words:
                    all_lines.append(" ".join(curr_words))
                    curr_words = []
                    curr_width = 0
                while word:
                    chunk = ""
                    chunk_width = 0
                    for c in word:
                        cw = get_cwidth(c)
                        if chunk_width + cw > max_width:
                            break
                        chunk += c
                        chunk_width += cw
                    all_lines.append(chunk)
                    word = word[len(chunk):]
                continue

            space_width = 1 if curr_words else 0
            if curr_words and (curr_width + space_width + w_width > max_width):
                all_lines.append(" ".join(curr_words))
                curr_words = [word]
                curr_width = w_width
            else:
                curr_words.append(word)
                curr_width += space_width + w_width

        if curr_words:
            all_lines.append(" ".join(curr_words))

    return all_lines or [""]


# ============================================================================
# Construction Visuelle des Jetons PromptToolkit
# ============================================================================

def build_approval_tokens(
    question: str,
    *,
    command: str | None = None,
    details: str | None = None,
    tool: str | None = None,
    selected_index: int = DEFAULT_CHOICE_INDEX,
    width: int | None = None,
) -> list[tuple[str, str]]:
    """Construit les jetons FormattedText stylés pour l'encadré d'approbation."""
    box_width = width if (width and width >= 40) else 76
    inner_width = box_width - 4

    tokens: list[tuple[str, str]] = []

    # 1. Bordure supérieure avec titre
    title = " Approbation Forensique "
    title_w = sum(get_cwidth(c) for c in title)
    prefix_w = get_cwidth(BORDER_TOP_LEFT) + get_cwidth(BORDER_HORIZONTAL)
    suffix_w = get_cwidth(BORDER_TOP_RIGHT)
    fill_len = max(0, box_width - prefix_w - title_w - suffix_w)

    tokens.append(("class:approval.border", BORDER_TOP_LEFT + BORDER_HORIZONTAL))
    tokens.append(("class:approval.title", title))
    tokens.append(("class:approval.border", (BORDER_HORIZONTAL * fill_len) + BORDER_TOP_RIGHT + "\n"))

    def add_line(content_tokens: list[tuple[str, str]]) -> None:
        line_w = sum(get_cwidth(c) for _, text in content_tokens for c in text)
        pad = max(0, inner_width - line_w)
        tokens.append(("class:approval.border", BORDER_VERTICAL + " "))
        tokens.extend(content_tokens)
        if pad > 0:
            tokens.append(("", " " * pad))
        tokens.append(("class:approval.border", " " + BORDER_VERTICAL + "\n"))

    def add_divider() -> None:
        div_len = max(0, box_width - get_cwidth(BORDER_DIVIDER_LEFT) - get_cwidth(BORDER_DIVIDER_RIGHT))
        tokens.append(("class:approval.border", BORDER_DIVIDER_LEFT + (BORDER_HORIZONTAL * div_len) + BORDER_DIVIDER_RIGHT + "\n"))

    def add_field(label: str, value: str, label_style: str, value_style: str) -> None:
        lw = sum(get_cwidth(c) for c in label)
        avail = max(10, inner_width - lw)
        lines = wrap_text_cwidth(value, avail)
        if not lines:
            return
        add_line([(label_style, label), (value_style, lines[0])])
        indent = " " * lw
        for extra in lines[1:]:
            add_line([("", indent), (value_style, extra)])

    has_metadata = False

    # 2. Outil concerné (optionnel)
    if tool:
        add_field("  Outil        : ", tool, "class:approval.label", "class:approval.tool")
        has_metadata = True

    # 3. Commande préparée (optionnel)
    if command:
        add_field("  Commande     : ", command, "class:approval.label", "class:approval.command")
        has_metadata = True

    # 4. Précautions forensiques / avertissements (optionnel)
    if details:
        add_field("  Précautions  : ", details, "class:approval.label", "class:approval.warning")
        has_metadata = True

    # Séparateur après les métadonnées si présentes
    if has_metadata:
        add_divider()

    # 5. Question d'approbation
    q_lines = wrap_text_cwidth(question, inner_width - 2)
    for ql in q_lines:
        add_line([("class:approval.question", "  " + ql)])

    # Ligne vide de respiration
    add_line([])

    # 6. Choix interactifs (1 = Oui, 2 = Non)
    # RÈGLE FORENSIQUE : Non est à l'index 1, Oui à l'index 0
    if selected_index == 0:
        add_line([
            ("class:approval.cursor", "  › "),
            ("class:approval.choice.selected", f"(*) 1. {CHOICE_YES}"),
        ])
        add_line([
            ("", "    "),
            ("class:approval.choice.normal", f"( ) 2. {CHOICE_NO}"),
        ])
    else:
        add_line([
            ("", "    "),
            ("class:approval.choice.normal", f"( ) 1. {CHOICE_YES}"),
        ])
        add_line([
            ("class:approval.cursor", "  › "),
            ("class:approval.choice.selected", f"(*) 2. {CHOICE_NO}"),
        ])

    # Ligne vide avant l'aide
    add_line([])

    # 7. Barre d'aide
    hint_text = "  ↑↓ alterner · 1/o Oui · 2/n Non · Entrée valider · Échap refuser"
    add_line([("class:approval.hint", hint_text)])

    # 8. Bordure inférieure
    bot_fill = max(0, box_width - get_cwidth(BORDER_BOTTOM_LEFT) - get_cwidth(BORDER_BOTTOM_RIGHT))
    tokens.append(("class:approval.border", BORDER_BOTTOM_LEFT + (BORDER_HORIZONTAL * bot_fill) + BORDER_BOTTOM_RIGHT + "\n"))

    return tokens


def format_approval_text(
    question: str,
    *,
    command: str | None = None,
    details: str | None = None,
    tool: str | None = None,
    selected_index: int = DEFAULT_CHOICE_INDEX,
    width: int | None = None,
) -> str:
    """Renvoie la représentation textuelle brute de l'encadré d'approbation."""
    tokens = build_approval_tokens(
        question,
        command=command,
        details=details,
        tool=tool,
        selected_index=selected_index,
        width=width,
    )
    return "".join(text for _, text in tokens)


# ============================================================================
# Fonction Principale d'Approbation Forensique
# ============================================================================

def ask_approval(
    question: str,
    *,
    command: str | None = None,
    details: str | None = None,
    tool: str | None = None,
    style: Any = None,
    input: Any = None,
    output: Any = None,
    width: int | None = None,
    **kwargs: Any,
) -> bool:
    """Demande l'approbation explicite de l'enquêteur pour l'exécution d'une commande.

    RÈGLE DE SÉCURITÉ FORENSIQUE ABSOLUE :
    Le choix 'Non (Échap)' est TOUJOURS pré-sélectionné par défaut (index = 1).
    Toute interruption, exception, Échap ou validation directe sans sélection
    résulte en un refus strict (renvoie False).

    Arguments:
        question: Question d'approbation posée à l'enquêteur.
        command: Commande technique préparée (optionnel).
        details: Précautions forensiques ou avertissements (optionnel).
        tool: Nom de l'outil concerné (optionnel).
        style: Style PromptToolkit ou dictionnaire de styles personnalisés (optionnel).
        input: Stream d'entrée PromptToolkit (optionnel, injecté pour les tests).
        output: Stream de sortie PromptToolkit (optionnel, injecté pour les tests).
        width: Largeur imposée de l'encadré (optionnel).
        **kwargs: Arguments supplémentaires ignorés pour robustesse.

    Returns:
        True si l'utilisateur valide explicitement 'Oui' (choix 1),
        False dans tous les autres cas (refus strict).
    """
    selected = [DEFAULT_CHOICE_INDEX]  # 1 = Non par défaut

    keys = KeyBindings()

    @keys.add("up")
    @keys.add("left")
    def _move_up(event: Any) -> None:
        selected[0] = 0

    @keys.add("down")
    @keys.add("right")
    def _move_down(event: Any) -> None:
        selected[0] = 1

    @keys.add("tab")
    @keys.add("s-tab")
    @keys.add("c-i")
    def _tab_toggle(event: Any) -> None:
        selected[0] = 1 - selected[0]

    @keys.add("space")
    def _space_toggle(event: Any) -> None:
        selected[0] = 1 - selected[0]

    @keys.add("1")
    @keys.add("o")
    @keys.add("O")
    @keys.add("y")
    @keys.add("Y")
    def _select_yes(event: Any) -> None:
        selected[0] = 0

    @keys.add("2")
    @keys.add("n")
    @keys.add("N")
    def _select_no(event: Any) -> None:
        selected[0] = 1

    @keys.add("enter")
    def _accept(event: Any) -> None:
        event.app.exit(result=(selected[0] == 0))

    @keys.add("escape", eager=True)
    @keys.add("c-c")
    @keys.add("c-d")
    @keys.add("q")
    @keys.add("Q")
    def _cancel(event: Any) -> None:
        event.app.exit(result=False)

    # Résolution du style PromptToolkit
    pt_style: PtStyle
    if isinstance(style, PtStyle):
        pt_style = style
    elif isinstance(style, dict):
        pt_style = PtStyle.from_dict(style)
    elif hasattr(style, "pt_style") and isinstance(getattr(style, "pt_style"), PtStyle):
        pt_style = getattr(style, "pt_style")
    else:
        pt_style = PtStyle.from_dict(DEFAULT_STYLE_DICT)

    effective_width = width or get_box_width(output)

    def get_tokens():
        # Rich calcule lui-même les largeurs et les bordures à chaque rendu.
        import io
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
        from prompt_toolkit.formatted_text import ANSI
        content = Text()
        if tool:
            content.append(f"Outil : {tool}\n", style='bold #38BDF8')
        if command:
            content.append(f"Commande : {command}\n", style='#E2E8F0')
        if details:
            content.append(f"Précautions : {details}\n", style='#94A3B8')
        content.append(question + '\n\n', style='bold #E2E8F0')
        for index, label in enumerate((CHOICE_YES, CHOICE_NO)):
            content.append(('> ' if selected[0] == index else '  ') + label + '\n',
                           style='bold #E85D26' if selected[0] == index else '#94A3B8')
        content.append('↑↓ choisir · o/n · Entrée valider · Échap refuser', style='#94A3B8')
        capture = io.StringIO()
        cols = width or get_box_width(output)
        Console(file=capture, force_terminal=True, color_system='truecolor', width=cols).print(
            Panel(content, title='Approbation [o/N]', box=box.ROUNDED, border_style='#E85D26'))
        return ANSI(capture.getvalue().rstrip())

    layout = Layout(Window(FormattedTextControl(get_tokens)))

    app = Application(
        layout=layout,
        key_bindings=keys,
        full_screen=False,
        mouse_support=False,
        style=pt_style,
        erase_when_done=True,
        input=input,
        output=output,
    )

    try:
        result = app.run()
        return bool(result)
    except (KeyboardInterrupt, EOFError):
        return False
    except Exception:
        return False
