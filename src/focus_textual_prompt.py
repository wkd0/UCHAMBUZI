# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_textual_prompt.py
# Role          : Mini-editeur multiligne du prompt et historique de session
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Saisie terminal multiligne conservant les raccourcis d'edition usuels."""
from __future__ import annotations

from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.widgets import TextArea


class InvestigationPrompt(TextArea):
    """TextArea avec soumission explicite, historique et compatibilite Input.

    ``value`` et ``cursor_position`` utilisent respectivement le texte complet et
    un index Unicode, comme Input. Les messages Changed et Submitted exposent
    ``input`` et ``value`` ; ils se routent avec ``@on`` ou avec les handlers
    ``on_investigation_prompt_changed`` / ``on_investigation_prompt_submitted``.
    """

    DEFAULT_CSS = """
    InvestigationPrompt {
        height: auto;
        min-height: 1;
        max-height: 6;
        border: none;
        padding: 0;
        background: transparent;
        scrollbar-size-vertical: 0;
        scrollbar-size-horizontal: 0;
    }
    InvestigationPrompt:focus { border: none; }
    """

    BINDINGS = [
        Binding("enter", "submit", show=False),
        Binding("shift+enter,ctrl+j", "newline", show=False),
        Binding("ctrl+u", "clear_prompt", show=False),
        Binding("ctrl+k", "kill_line_tail", show=False),
        Binding("ctrl+a", "logical_line_start", show=False),
        Binding("ctrl+e", "logical_line_end", show=False),
    ]

    class Changed(TextArea.Changed):
        """Modification du prompt ; value est la saisie au moment du message."""

        def __init__(self, text_area: InvestigationPrompt) -> None:
            super().__init__(text_area)
            self.input = text_area
            self.value = text_area.text

    class Submitted(Message):
        """Saisie validee par Entree, sans perte des retours a la ligne."""

        def __init__(self, input: InvestigationPrompt, value: str) -> None:
            super().__init__()
            self.input = input
            self.value = value

        @property
        def control(self) -> InvestigationPrompt:
            return self.input

    def __init__(self, value: str = "", *, placeholder: str = "", **kwargs) -> None:
        self.prompt_history: list[str] = []
        self._history_index: int | None = None
        self._history_draft = ""
        self._history_cursor = 0
        self._history_edits: dict[int, tuple[str, int]] = {}
        self._browsing_history = False
        super().__init__(value, placeholder=placeholder, show_line_numbers=False,
                         highlight_cursor_line=False, compact=True, **kwargs)

    @property
    def value(self) -> str:
        return self.text

    @value.setter
    def value(self, text: str) -> None:
        self._reset_history_navigation()
        self._load_history_text(text)

    def _load_history_text(self, text: str, cursor: int | None = None) -> None:
        self._browsing_history = False
        self.load_text(text)
        self.cursor_position = len(text) if cursor is None else cursor

    def _reset_history_navigation(self) -> None:
        self._history_index = None
        self._history_draft = ""
        self._history_cursor = 0
        self._history_edits.clear()
        self._browsing_history = False

    def _save_history_edit(self) -> None:
        if self._history_index is not None and self._history_index < len(self.prompt_history):
            self._history_edits[self._history_index] = (self.text, self.cursor_position)

    def _show_history_entry(self) -> None:
        index = self._history_index
        text, cursor = self._history_edits.get(index, (self.prompt_history[index], None))
        self._load_history_text(text, cursor)
        self._browsing_history = text == self.prompt_history[index]

    @property
    def browsing_history(self) -> bool:
        """Vrai pour un rappel intact, afin de suspendre le menu de completion."""
        return self._browsing_history

    def edit(self, edit):
        # Toutes les insertions/suppressions clavier, collage compris, passent
        # ici. La navigation dans l'historique utilise load_text, pas edit.
        self._browsing_history = False
        return super().edit(edit)

    def undo(self) -> None:
        self._browsing_history = False
        super().undo()

    def redo(self) -> None:
        self._browsing_history = False
        super().redo()

    @property
    def cursor_position(self) -> int:
        return self.document.get_index_from_location(self.cursor_location)

    @cursor_position.setter
    def cursor_position(self, offset: int) -> None:
        offset = max(0, min(len(self.text), offset))
        self.move_cursor(self.document.get_location_from_index(offset))

    def remember(self, text: str) -> None:
        """Ajoute une commande acceptee ; les approbations peuvent etre exclues."""
        if text.strip() and (not self.prompt_history or self.prompt_history[-1] != text):
            self.prompt_history.append(text)
        self._reset_history_navigation()

    def action_submit(self) -> None:
        self.post_message(self.Submitted(self, self.text))

    async def _on_key(self, event: events.Key) -> None:
        # Traiter dans la même file que Paste et les caractères : un binding
        # remonté à Screen peut arriver après les touches suivantes d'une rafale.
        actions = {
            'enter': self.action_submit,
            'shift+enter': self.action_newline,
            'ctrl+j': self.action_newline,
            'ctrl+a': self.action_logical_line_start,
            'ctrl+e': self.action_logical_line_end,
            'ctrl+k': self.action_kill_line_tail,
            'ctrl+u': self.action_clear_prompt,
            'up': self.action_cursor_up,
            'down': self.action_cursor_down,
        }
        if event.key in actions:
            event.stop()
            event.prevent_default()
            actions[event.key]()
            return
        await super()._on_key(event)

    def action_newline(self) -> None:
        self._replace_via_keyboard("\n", *self.selection)

    def action_clear_prompt(self) -> None:
        self.value = ""

    def action_kill_line_tail(self) -> None:
        row, column = self.cursor_location
        self._delete_via_keyboard((row, column), (row, len(self.document.get_line(row))))

    def action_logical_line_start(self) -> None:
        self.move_cursor((self.cursor_location[0], 0))

    def action_logical_line_end(self) -> None:
        row = self.cursor_location[0]
        self.move_cursor((row, len(self.document.get_line(row))))

    def action_cursor_up(self, select: bool = False) -> None:
        if select or (self.cursor_location[0] > 0 and self._history_index is None):
            super().action_cursor_up(select)
            return
        if not self.prompt_history:
            return
        if self._history_index is None:
            self._history_draft = self.text
            self._history_cursor = self.cursor_position
            self._history_index = len(self.prompt_history)
        if self._history_index > 0:
            self._save_history_edit()
            self._history_index -= 1
            self._show_history_entry()

    def action_cursor_down(self, select: bool = False) -> None:
        if select or self._history_index is None:
            super().action_cursor_down(select)
            return
        if self._history_index + 1 < len(self.prompt_history):
            self._save_history_edit()
            self._history_index += 1
            self._show_history_entry()
        else:
            self._save_history_edit()
            self._history_index = None
            self._load_history_text(self._history_draft, self._history_cursor)

    def on_investigation_prompt_changed(self, event: Changed) -> None:
        self._fit_height()

    def on_resize(self) -> None:
        # Le handler prive de TextArea recalcule ensuite le document replie.
        self.call_after_refresh(self._fit_height)

    def _fit_height(self) -> None:
        self.styles.height = min(6, max(1, self.wrapped_document.height))

    async def _on_paste(self, event: events.Paste) -> None:
        if self.read_only:
            return
        event.stop()
        event.prevent_default()
        text = event.text.replace("\r\n", "\n").replace("\r", "\n")
        result = self._replace_via_keyboard(text, *self.selection)
        if result is not None:
            self.move_cursor(result.end_location)
            self.focus()
