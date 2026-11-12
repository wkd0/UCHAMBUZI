# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_input.py
# Role          : Gestionnaire de saisie encadree, raccourcis reactifs et session REPL
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Gestionnaire d'entrée interactive pour l'expérience REPL Claude Code / Aider.

Fournit :
- Session PromptSession avec encadré arrondi (╭, ╮, ╰, ╯, │, ─) et invite '> '
- Suppression des menus flottants par défaut (FloatContainer.floats)
- Rendu du menu de complétion SOUS la boîte de saisie via repl_menu
- Intégration de la barre d'état inférieure blanche conservée à 100%
- Raccourcis clavier ultra-réactifs avec zéro latence (timeoutlen=0.05s)
- File d'attente (queued messages) avec retour visuel '↳ en attente : ...'
"""
from __future__ import annotations

import collections
import shutil
import time
from typing import Any, Callable, Sequence

from prompt_toolkit import PromptSession
from prompt_toolkit.filters import has_completions
from prompt_toolkit.formatted_text import FormattedText, to_plain_text
from prompt_toolkit.key_binding import KeyBindings, key_bindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.layout.containers import FloatContainer

key_bindings.KEY_ALIASES.setdefault('backtab', 's-tab')
ANSI_SEQUENCES.setdefault('\x1b[Z', Keys.BackTab)
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style as PtStyle
from prompt_toolkit.utils import get_cwidth

from repl_commands import resolve_command_prefix
from repl_menu import (
    COLOR_CYAN,
    COLOR_GRAY,
    COLOR_ORANGE,
    COLOR_WHITE,
    render_menu_from_buffer,
)


# ============================================================================
# Délimiteurs d'Encadré Arrondi (Style REPL Moderne)
# ============================================================================
class Border:
    """Caractères Unicode pour bordures épurées et arrondies."""
    TOP_LEFT = '╭'
    TOP_RIGHT = '╮'
    BOTTOM_LEFT = '╰'
    BOTTOM_RIGHT = '╯'
    HORIZONTAL = '─'
    VERTICAL = '│'


# Pôles cyber UCHAMBUZI pour rotation rapide Shift+Tab
CYBER_POLES: list[tuple[str, str, str]] = [
    ('osint', 'OSINT Team', 'Renseignement & investigation'),
    ('red', 'Red Team', 'Sécurité offensive & audits'),
    ('blue', 'Blue Team', 'Sécurité défensive & réponse incidents'),
    ('purple', 'Purple Team', 'Évaluation continue & émulation ATT&CK'),
    ('assist', 'Assist', 'Assistant IA généraliste'),
]


# Style par défaut PromptToolkit
DEFAULT_STYLE = PtStyle.from_dict({
    '': f'bold {COLOR_CYAN}',
    'prompt.border': f'fg:{COLOR_CYAN}',
    'prompt.arrow': f'bold fg:{COLOR_CYAN}',
    'prompt.queued': f'bold fg:{COLOR_CYAN}',
    'auto-suggestion': f'fg:{COLOR_GRAY} italic',
    'placeholder': f'fg:{COLOR_GRAY} italic',
    'bottom-toolbar': 'noreverse',
    'bottom-toolbar.text': f'noreverse fg:{COLOR_GRAY}',
    'tb-line': f'noreverse fg:{COLOR_CYAN}',
    'tb-bar': 'bg:#ffffff fg:#000000 bold',
    'tb-mode': 'bold fg:#000000',
    'tb-model': 'bold fg:#000000',
})


def is_completion_menu(content: Any) -> bool:
    """Vérifie si un contenu de Float correspond à un menu de complétion natif Prompt_Toolkit."""
    if content is None:
        return False
    from prompt_toolkit.layout.menus import CompletionsMenu, MultiColumnCompletionsMenu
    if isinstance(content, (CompletionsMenu, MultiColumnCompletionsMenu)):
        return True
    cls_name = getattr(content, '__class__', None).__name__ if content else ''
    return 'CompletionsMenu' in cls_name or 'CompletionMenu' in cls_name


def strip_floating_menus(container: Any, seen: set[int] | None = None) -> None:
    """Supprime les menus flottants par défaut (FloatContainer.floats).

    Parcourt récursivement tous les conteneurs (Layout, DynamicContainer, FloatContainer,
    HSplit, VSplit, Window, ConditionalContainer) et vide les floats de type menu,
    permettant au menu d'autocomplétion d'apparaître proprement SOUS la boîte de
    saisie via repl_menu sans aucune superposition opaque sur l'écran.
    """
    if seen is None:
        seen = set()
    if container is None or id(container) in seen:
        return
    seen.add(id(container))

    # Support de l'objet Layout directement
    if hasattr(container, 'container') and container.container is not None:
        strip_floating_menus(container.container, seen)

    # Vider les floats dans FloatContainer
    if isinstance(container, FloatContainer) or hasattr(container, 'floats'):
        if isinstance(container.floats, list):
            container.floats.clear()

    # Traverser les enfants via get_children() si disponible
    if hasattr(container, 'get_children') and callable(container.get_children):
        try:
            for child in container.get_children():
                strip_floating_menus(child, seen)
        except Exception:
            pass

    # Traverser la liste explicite d'enfants (HSplit, VSplit)
    if hasattr(container, 'children') and isinstance(container.children, (list, tuple)):
        for child in container.children:
            strip_floating_menus(child, seen)

    # Traverser content (Window, ConditionalContainer, ScrollablePane)
    if hasattr(container, 'content') and container.content is not None:
        strip_floating_menus(container.content, seen)

    # Traverser alternative_content (ConditionalContainer)
    if hasattr(container, 'alternative_content') and container.alternative_content is not None:
        strip_floating_menus(container.alternative_content, seen)

    # Traverser DynamicContainer
    if hasattr(container, 'get_container') and callable(container.get_container):
        try:
            strip_floating_menus(container.get_container(), seen)
        except Exception:
            pass


class ReplInputManager:
    """Gestionnaire d'état de saisie, file d'attente et raccourcis clavier."""

    def __init__(
        self,
        *,
        is_busy: Callable[[], bool] | None = None,
        on_interrupt: Callable[[], None] | None = None,
        on_pole_changed: Callable[[str, str], None] | None = None,
        on_details: Callable[[], None] | None = None,
        on_quit_requested: Callable[[], None] | None = None,
        status_provider: Callable[[], dict[str, str]] | None = None,
        initial_pole: str = 'osint',
    ) -> None:
        self.is_busy_fn = is_busy or (lambda: False)
        self.on_interrupt = on_interrupt
        self.on_pole_changed = on_pole_changed
        self.on_details = on_details
        self.on_quit_requested = on_quit_requested
        self.status_provider = status_provider

        # File d'attente pour messages soumis pendant busy
        self.message_queue: collections.deque[str] = collections.deque()
        self.last_queued_message: str | None = None

        # Dernier message soumis (pour Échap Échap)
        self.last_submitted_message: str = ''

        # Détection double Ctrl+C (< 2s)
        self.last_ctrl_c_time: float = 0.0
        self.quit_pending: bool = False

        # Pôle cyber actif
        self.current_pole_idx: int = 0
        for i, (p_id, _, _) in enumerate(CYBER_POLES):
            if p_id.lower() == initial_pole.lower():
                self.current_pole_idx = i
                break

    def is_busy(self) -> bool:
        """Indique si le moteur IA ou une opération d'investigation est en cours."""
        return bool(self.is_busy_fn())

    def enqueue_message(self, message: str) -> None:
        """Ajoute un message à la file d'attente."""
        msg = message.strip()
        if msg:
            self.message_queue.append(msg)
            self.last_queued_message = msg

    def pop_queued_message(self) -> str | None:
        """Récupère et retire le prochain message en attente."""
        if self.message_queue:
            msg = self.message_queue.popleft()
            self.last_queued_message = self.message_queue[-1] if self.message_queue else None
            return msg
        self.last_queued_message = None
        return None

    def has_queued_messages(self) -> bool:
        """Vérifie si des messages sont en attente de traitement."""
        return len(self.message_queue) > 0

    def get_queued_messages(self) -> list[str]:
        """Retourne la liste des messages en attente."""
        return list(self.message_queue)

    def cycle_pole(self) -> tuple[str, str]:
        """Bascule vers le pôle cyber suivant (OSINT -> Red -> Blue -> Purple -> Assist)."""
        self.current_pole_idx = (self.current_pole_idx + 1) % len(CYBER_POLES)
        pole_id, pole_name, _ = CYBER_POLES[self.current_pole_idx]
        if self.on_pole_changed:
            self.on_pole_changed(pole_id, pole_name)
        return pole_id, pole_name

    @property
    def current_pole(self) -> tuple[str, str, str]:
        """Pôle cyber actuellement sélectionné."""
        return CYBER_POLES[self.current_pole_idx]


def build_box_top(width: int, title: str = "UCHAMBUZI") -> str:
    """Construit la bordure supérieure arrondie de la boîte de saisie."""
    prefix = f"{Border.TOP_LEFT}{Border.HORIZONTAL} {title} {Border.HORIZONTAL}"
    remaining = max(0, width - get_cwidth(prefix) - 1)
    return prefix + (Border.HORIZONTAL * remaining) + Border.TOP_RIGHT


def build_box_bottom(width: int) -> str:
    """Construit la bordure inférieure arrondie de la boîte de saisie."""
    remaining = max(0, width - 2)
    return f"{Border.BOTTOM_LEFT}{Border.HORIZONTAL * remaining}{Border.BOTTOM_RIGHT}"


def build_prompt_message(
    manager: ReplInputManager,
    width: int = 80,
    title: str = "UCHAMBUZI",
) -> FormattedText:
    """Génère l'invite encadrée avec bordure supérieure et préfixe '> '."""
    fragments: list[tuple[str, str]] = []

    # Affichage visuel d'attente si des messages sont en file
    if manager.has_queued_messages():
        for queued in manager.get_queued_messages():
            fragments.append((f'bold fg:{COLOR_CYAN}', '↳ en attente : '))
            fragments.append((f'fg:{COLOR_WHITE}', f'{queued}\n'))

    # Bordure supérieure arrondie
    top_line = build_box_top(width, title)
    fragments.append((f'fg:{COLOR_CYAN}', top_line + '\n'))

    # Invite de saisie
    fragments.append((f'bold fg:{COLOR_CYAN}', f"{Border.VERTICAL} > "))
    return FormattedText(fragments)


def prompt_continuation(width: int, line_number: int, is_soft_wrap: bool) -> FormattedText:
    """Continuation pour la saisie multiligne avec délimiteur vertical."""
    if is_soft_wrap:
        return FormattedText([(f'fg:{COLOR_CYAN}', f"{Border.VERTICAL}   ")])
    return FormattedText([
        (f'fg:{COLOR_CYAN}', f"{Border.VERTICAL} "),
        (f'fg:{COLOR_GRAY}', '· '),
    ])


def build_bottom_toolbar(
    manager: ReplInputManager,
    buffer: Any,
    width: int = 80,
    status_dict: dict[str, str] | None = None,
) -> FormattedText:
    """Génère le pied de la boîte de saisie : bordure basse, menu slash et barre d'état blanche."""
    fragments: list[tuple[str, str]] = []

    # 1. Bordure inférieure arrondie de la boîte
    bottom_line = build_box_bottom(width)
    fragments.append((f'fg:{COLOR_CYAN}', bottom_line + '\n'))

    # 2. Rendu du menu de complétion slash SOUS la boîte (ou aide '?')
    menu_ft = render_menu_from_buffer(buffer, width=width, max_items=8)
    if menu_ft:
        fragments.extend(menu_ft)

    # 3. Notification visuelle des messages en file d'attente
    if manager.has_queued_messages() and not buffer.text.startswith('/'):
        queued_count = len(manager.message_queue)
        latest = manager.message_queue[-1]
        fragments.append((f'bold fg:{COLOR_CYAN}', f" ↳ en attente ({queued_count}) : "))
        fragments.append((f'fg:{COLOR_WHITE}', f"{latest}\n"))

    # 4. Barre d'état inférieure blanche (conservée à 100% selon la directive WKD)
    info = status_dict or (manager.status_provider() if manager.status_provider else {})
    mode_label = info.get('mode', manager.current_pole[1])
    model_name = info.get('model', 'sans-IA')
    case_id = info.get('case_id', 'aucun')

    labels = [
        f" ◈ UCHAMBUZI │ Mode: {mode_label} │ IA: {model_name} │ Dossier: {case_id} │ Aide: /help │ Quitter: Ctrl+D ",
        f" ◈ UCHAMBUZI │ Mode: {mode_label} │ IA: {model_name} │ Dossier: {case_id} │ Quitter: Ctrl+D ",
        f" ◈ UCHAMBUZI │ Mode: {mode_label} │ IA: {model_name} │ {case_id} ",
        f" ◈ UCHAMBUZI │ Mode: {mode_label} ",
        f" ◈ UCHAMBUZI ",
    ]
    label = next((v for v in labels if get_cwidth(v) <= width), labels[-1])
    while get_cwidth(label) > width:
        label = label[:-1]

    # Astuce contextuelle
    hint = (
        'Saisie conservée en attente · envoi automatique' if manager.is_busy() else
        'Entrée envoyer · Alt+Entrée ligne · / commandes · Ctrl+T détails'
    )
    if get_cwidth(label + "  │  " + hint) <= width:
        label += "  │  " + hint

    # Espacement pour remplir 100% de la largeur du terminal
    padding = max(0, width - get_cwidth(label))
    fragments.append(('class:tb-bar', label + (' ' * padding)))

    return FormattedText(fragments)


def build_key_bindings(manager: ReplInputManager) -> KeyBindings:
    """Construit l'ensemble des raccourcis clavier interactifs."""
    bindings = KeyBindings()

    # --- ÉCHAP : Annule la complétion si active, sinon déclenche l'interruption ---
    @bindings.add('escape', filter=has_completions)
    def _handle_escape_completion(event):
        """Ferme les suggestions d'autocomplétion sans interrompre."""
        event.current_buffer.cancel_completion()

    @bindings.add('escape', filter=~has_completions)
    def _handle_escape_interrupt(event):
        """Interrompt la tâche en cours ou déclenche le callback d'interruption."""
        if manager.on_interrupt:
            manager.on_interrupt()
        else:
            event.app.exit(exception=KeyboardInterrupt())

    # --- ÉCHAP ÉCHAP : Recharge le dernier message saisi pour édition rapide ---
    @bindings.add('escape', 'escape')
    def _handle_double_escape(event):
        """Restaure le dernier message validé."""
        if manager.last_submitted_message:
            b = event.current_buffer
            b.text = manager.last_submitted_message
            b.cursor_position = len(b.text)
            event.app.invalidate()

    # --- SHIFT+TAB : Rotation rapide du pôle cyber (OSINT -> Red -> Blue -> Purple -> Assist) ---
    @bindings.add('s-tab', filter=has_completions)
    @bindings.add('backtab', filter=has_completions)
    def _handle_shift_tab_completion(event):
        """Navigation arrière dans les suggestions de complétion."""
        event.current_buffer.complete_previous()

    @bindings.add('s-tab', filter=~has_completions)
    @bindings.add('backtab', filter=~has_completions)
    def _handle_shift_tab_pole(event):
        """Rotation instantanée de la posture cyber."""
        manager.cycle_pole()
        event.app.invalidate()

    # --- CTRL+O et CTRL+T : Raccourci pour /details ---
    @bindings.add('c-o')
    @bindings.add('c-t')
    def _handle_details(event):
        """Développe la dernière sortie d'outil (/details)."""
        if not manager.is_busy():
            b = event.current_buffer
            b.text = '/details'
            b.validate_and_handle()
        else:
            manager.enqueue_message('/details')
            event.app.invalidate()

    # --- CTRL+C : Vide le tampon ; un second Ctrl+C rapide (< 2s) demande à quitter ---
    @bindings.add('c-c')
    def _handle_ctrl_c(event):
        """Gestion ergonomique de Ctrl+C."""
        b = event.current_buffer
        if b.text:
            b.text = ''
            manager.last_ctrl_c_time = 0.0
            event.app.invalidate()
        else:
            now = time.monotonic()
            if now - manager.last_ctrl_c_time < 2.0:
                manager.quit_pending = True
                if manager.on_quit_requested:
                    manager.on_quit_requested()
                event.app.exit(exception=KeyboardInterrupt())
            else:
                manager.last_ctrl_c_time = now
                event.app.invalidate()

    # --- ALT+ENTRÉE et CTRL+N : Saut de ligne (saisie multiligne) ---
    @bindings.add('escape', 'enter')
    @bindings.add('c-n')
    def _handle_multiline_newline(event):
        """Insère une nouvelle ligne sans soumettre le formulaire."""
        event.current_buffer.insert_text('\n')

    # --- ENTRÉE : Validation avec gestion de file d'attente (queued messages) ---
    @bindings.add('enter')
    def _handle_enter(event):
        """Valide la complétion ou envoie le message (ou le met en attente si occupé)."""
        b = event.current_buffer

        text = b.text.strip()
        if text.startswith('/'):
            # 1. Complétion active sélectionnée par l'utilisateur
            if b.complete_state and b.complete_state.current_completion:
                b.apply_completion(b.complete_state.current_completion)
            # 2. Complétion unique disponible
            elif b.complete_state and getattr(b.complete_state, 'completions', None) and len(b.complete_state.completions) == 1:
                b.apply_completion(b.complete_state.completions[0])
            # 3. Résolution directe de préfixe unique (ex: /ex -> /exit)
            else:
                cmd_token = text.split(maxsplit=1)[0]
                resolved, _ = resolve_command_prefix(cmd_token)
                if resolved:
                    tokens = text.split(maxsplit=1)
                    arg = (" " + tokens[1]) if len(tokens) > 1 else ""
                    b.text = f"{resolved}{arg}"
                    b.cursor_position = len(b.text)
                    if b.complete_state:
                        b.cancel_completion()

        if manager.is_busy():
            text_to_queue = b.text.strip()
            if text_to_queue:
                manager.enqueue_message(text_to_queue)
                b.text = ''
                event.app.invalidate()
            return

        text = b.text
        if text.strip():
            manager.last_submitted_message = text
        b.validate_and_handle()

    # --- TAB et Flèches : Navigation intuitive ---
    @bindings.add('tab')
    def _handle_tab(event):
        """Sélectionne la première suggestion ou passe à la suivante."""
        b = event.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=True)

    @bindings.add('down', filter=has_completions)
    def _handle_down(event):
        event.current_buffer.complete_next()

    @bindings.add('up', filter=has_completions)
    def _handle_up(event):
        event.current_buffer.complete_previous()

    return bindings


def create_repl_session(
    manager: ReplInputManager | None = None,
    completer: Any = None,
    auto_suggest: Any = None,
    history: Any = None,
    input: Any = None,
    output: Any = None,
    style: Any = None,
    **kwargs: Any,
) -> tuple[PromptSession, ReplInputManager]:
    """Construit et configure une session PromptSession REPL avancée.

    Garantit :
    - Encadré arrondi autour de la zone de saisie avec invite >
    - Suppression des menus flottants par défaut (FloatContainer.floats)
    - Configuration sans latence (timeoutlen = 0.05, ttimeoutlen = 0.05)
    - Barre d'état inférieure blanche intégrée
    """
    mgr = manager or ReplInputManager()
    kb = build_key_bindings(mgr)
    active_style = style or DEFAULT_STYLE

    def _get_width() -> int:
        if output and hasattr(output, 'get_size'):
            try:
                cols = output.get_size().columns
                if cols and cols > 0:
                    return cols
            except Exception:
                pass
        return shutil.get_terminal_size(fallback=(80, 24)).columns

    def _prompt_message_fn() -> FormattedText:
        return build_prompt_message(mgr, width=_get_width())

    def _bottom_toolbar_fn() -> FormattedText:
        buf = session.default_buffer if 'session' in locals() else None
        return build_bottom_toolbar(mgr, buf, width=_get_width())

    session_kwargs: dict[str, Any] = {
        'multiline': True,
        'complete_while_typing': True,
        'key_bindings': kb,
        'style': active_style,
        'prompt_continuation': prompt_continuation,
        'mouse_support': False,
        'complete_style': CompleteStyle.COLUMN,
        'reserve_space_for_menu': 0,
    }
    if completer is not None:
        session_kwargs['completer'] = completer
    if auto_suggest is not None:
        session_kwargs['auto_suggest'] = auto_suggest
    if history is not None:
        session_kwargs['history'] = history
    if input is not None:
        session_kwargs['input'] = input
    if output is not None:
        session_kwargs['output'] = output

    session_kwargs.update(kwargs)
    session = PromptSession(**session_kwargs)

    # Élimination des menus flottants par défaut pour affichage sous la boîte
    strip_floating_menus(session.layout)

    # Réactivité instantanée de la touche Échap (50 ms au lieu de 1 s)
    session.app.timeoutlen = 0.05
    session.app.ttimeoutlen = 0.05

    return session, mgr
