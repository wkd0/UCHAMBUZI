# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_textual.py
# Role          : Interface REPL réactive 2D basée sur Textual (style Codex / Claude Code)
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Moteur d'interface REPL moderne et réactif basé sur Textual pour UCHAMBUZI.

Offre une expérience utilisateur indestructible inspirée de Codex CLI et Claude Code,
conservant fidèlement la charte graphique et la présentation officielle d'UCHAMBUZI :
- Bannière d'accueil officielle avec logo vectoriel et grille des 4 pôles cyber
- Menu de commandes slash (/) s'ouvrant vers le haut au-dessus de la boîte de saisie
- Boîte de prompt délimitée par traits horizontaux et indicateur '❯'
- Ligne vide transparente d'espacement
- Barre d'état sombre pleine largeur collée au bas de l'écran
- Rendu Markdown Rich TrueColor et intégration complète des outils Kali et SHA-256
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import io
import os
import shutil
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from textual.widgets import Static, Input, OptionList, Select, Button
from textual.widgets.option_list import Option
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import events
from textual.drivers.linux_driver import LinuxDriver

from repl_theme import THEMES, DEFAULT_THEME_ID, UITheme, load_theme_preference, save_theme_preference
from repl_commands import (
    COMMAND_REGISTRY,
    COMMAND_DOCUMENTATION,
    ALIASES_MAP,
    ALL_SLASH_COMMANDS,
    resolve_command_prefix,
    OSINT_COMMANDS,
)
from repl_welcome import (
    VERSION,
    TAGLINE,
    build_banner_logo,
    render_teams_mini_grid,
)
from focus_teams import TEAMS, Team, active_teams, get_team, ASSIST_TEAM
from conversation import (
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_TIMEOUT,
    format_approval_preview,
    OllamaRuntime,
    ProviderManager,
    Session,
    TurnCancellation,
    RuntimeCancelled,
    RuntimeErrorLocal,
    safe_display,
    detect_prompt_injection,
)
from parcours import CaseManager
from focus_sessions import SessionManager, _SECRET
from focus_resume import ResumeSessions, conversation_messages
from installation import user_data_path
from focus_repl import FocusREPL
from focus_textual_prompt import InvestigationPrompt
from focus_textual_stream import StreamingAnswer, TranscriptScroll, SelectableStatic

CSS = """
Screen {
    background: transparent;
    color: #E2E8F0;
    overflow: hidden;
}

#transcript {
    height: 1fr;
    overflow-y: auto;
    padding: 0 1;
    scrollbar-gutter: stable;
}

#bottom-bar {
    dock: bottom;
    height: auto;
    width: 100%;
    background: transparent;
}

#slash-menu {
    display: none;
    position: absolute;
    overlay: screen;
    height: auto;
    max-height: 8;
    margin: 0;
    border: round #38BDF8;
    background: #0D1B2A;
    color: #E2E8F0;
}

#slash-menu > .option-list--option-highlighted {
    background: #1E293B;
    color: #38BDF8;
    text-style: bold;
}

#dialogue {
    display: none;
    height: auto;
    min-height: 100%;
    padding: 0 2;
}

#dialogue > StreamingAnswer {
    width: 100%;
    max-width: 110;
}

.user-message { margin-bottom: 1; }

#input-box {
    height: auto;
    border-top: solid #475569;
    border-bottom: solid #475569;
    background: transparent;
    padding: 0 1;
}

#shell-mode-hint {
    display: none;
    height: 1;
    text-align: right;
}

#prompt-row {
    height: auto;
    width: 100%;
}

#prompt-indicator {
    width: 2;
    color: #E85D26;
    text-style: bold;
}

#prompt-input {
    border: none;
    background: transparent;
    color: #FFFFFF;
    width: 1fr;
    padding: 0;
}

#prompt-input:focus {
    border: none;
}

#bottom-spacer {
    height: 1;
    background: transparent;
}

#status-bar {
    height: 1;
    width: 100%;
    background: #FFFFFF;
    color: #000000;
    text-style: bold;
    padding: 0 0;
}
"""


@dataclass
class SelectorItem:
    """Élément sélectionnable pour InteractiveSelectorModal."""
    id: str
    title: str
    description: str = ""
    badge: str = ""
    is_current: bool = False
    available: bool = True
    color: str | None = None
    text_only: bool = False
    raw: Any = None


class InteractiveSelectorModal(ModalScreen[SelectorItem | None]):
    """Écran modal réactif de sélection interactif inspiré de Codex CLI (TrueColor UCHAMBUZI)."""

    DEFAULT_CSS = """
    InteractiveSelectorModal {
        align: center middle;
        background: rgba(13, 27, 42, 0.75);
    }

    #selector-container {
        width: 82;
        max-width: 95%;
        height: auto;
        max-height: 28;
        background: #0D1B2A;
        border: round #38BDF8;
        padding: 1 2;
    }

    #selector-title {
        color: #FFFFFF;
        text-style: bold;
        height: 1;
    }

    InteractiveSelectorModal.theme-selector #selector-container {
        padding: 0 2;
    }

    #selector-subtitle {
        color: #94A3B8;
        margin-bottom: 1;
        height: 1;
    }

    #selector-list {
        height: auto;
        max-height: 14;
        overflow-y: hidden;
    }

    #selector-preview {
        height: auto;
        max-height: 7;
        margin-top: 1;
        border: round #38BDF8;
        padding: 0 1;
    }

    #selector-footer {
        color: #94A3B8;
        margin-top: 1;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annuler", show=False),
        Binding("enter", "select", "Sélectionner", show=False),
        Binding("up", "cursor_up", "Haut", show=False),
        Binding("down", "cursor_down", "Bas", show=False),
        Binding("k", "cursor_up", "Haut", show=False),
        Binding("j", "cursor_down", "Bas", show=False),
        Binding("home", "first", "Premier", show=False),
        Binding("end", "last", "Dernier", show=False),
        Binding("pageup", "page_up", "Page Haut", show=False),
        Binding("pagedown", "page_down", "Page Bas", show=False),
    ]

    def __init__(
        self,
        title: str,
        items: Sequence[SelectorItem],
        initial_index: int = 0,
        number_start: int = 1,
        on_preview: Any = None,
        subtitle: str = "",
        preview_renderer: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.selector_title = title
        self.subtitle = subtitle
        self.preview_renderer = preview_renderer
        self.items = list(items)
        self.number_start = number_start
        self.on_preview = on_preview
        if initial_index == 0:
            for i, it in enumerate(self.items):
                if it.is_current:
                    initial_index = i
                    break
        self.highlighted_index = max(0, min(len(self.items) - 1, initial_index)) if self.items else 0
        self.window_offset = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="selector-container"):
            yield Static(Text(self.selector_title, style="bold white"), id="selector-title")
            if self.subtitle:
                yield Static(Text(self.subtitle, style="#94A3B8"), id="selector-subtitle")
            yield Static(self._render_items(), id="selector-list")
            if self.preview_renderer is not None:
                yield Static(self._render_preview(), id="selector-preview")
            yield Static(self._render_footer(), id="selector-footer")

    def on_mount(self) -> None:
        theme = getattr(self.app, "ui_theme", None)
        if theme is not None:
            container = self.query_one("#selector-container")
            container.styles.background = theme.app_bg
            container.styles.border = ("round", theme.secondary)
            self.query_one("#selector-title").styles.color = theme.primary
            if self.preview_renderer is not None:
                self.query_one("#selector-preview").styles.border = ("round", theme.secondary)
        self._refresh_display()

    def _render_preview(self) -> Text:
        if self.preview_renderer is not None and self.items and 0 <= self.highlighted_index < len(self.items):
            return self.preview_renderer(self.items[self.highlighted_index])
        return Text()

    def _render_items(self) -> Text:
        if not self.items:
            return Text("Aucun élément disponible", style="#94A3B8")

        theme = getattr(self.app, "ui_theme", None)
        accent = getattr(theme, "primary", "#E85D26")
        foreground = getattr(theme, "text_main", "#FFFFFF")
        muted = getattr(theme, "text_dim", "#94A3B8")
        background = getattr(theme, "menu_meta_bg", "#1E293B")
        width = max(10, min(74, self.size.width - 8))
        # Les menus à deux lignes ont besoin de davantage de hauteur par entrée.
        detailed = self.number_start == 0
        reserved = 12 if self.preview_renderer is not None else 8
        available_height = max(1, self.size.height - reserved)
        max_visible = max(1, min(len(self.items), 10, available_height // (2 if detailed else 1)))
        if self.highlighted_index < self.window_offset:
            self.window_offset = self.highlighted_index
        elif self.highlighted_index >= self.window_offset + max_visible:
            self.window_offset = self.highlighted_index - max_visible + 1
        self.window_offset = min(self.window_offset, max(0, len(self.items) - max_visible))
        visible = self.items[self.window_offset:self.window_offset + max_visible]
        text = Text(no_wrap=True)
        for relative, item in enumerate(visible):
            index = self.window_offset + relative
            selected = index == self.highlighted_index
            prefix = "❯ " if selected else "  "
            number = f"{index + self.number_start}. "
            status = item.badge or ("✓ ACTIF" if item.is_current else "")
            line = Text(no_wrap=True)
            line.append(prefix, style=f"bold {accent}")
            line.append(number, style=muted)
            line.append(item.title, style=f"bold {foreground}" if item.available else muted)
            if status:
                line.append(f"  {status}", style=muted if not item.available else accent)
            if not detailed and item.description:
                line.append(f"  ·  {item.description}", style=muted)
            line.truncate(width, overflow="ellipsis")
            if selected:
                line.stylize(f"on {background}")
                if line.cell_len < width:
                    line.append(" " * (width - line.cell_len), style=f"on {background}")
            text.append_text(line)
            if detailed and item.description:
                description = Text("     " + item.description, style=muted, no_wrap=True)
                description.truncate(width, overflow="ellipsis")
                text.append("\n")
                text.append_text(description)
            if relative < len(visible) - 1:
                text.append("\n")
        return text

    def _render_footer(self) -> Text:
        return Text("↑↓ Choisir  ·  Entrée Valider  ·  Échap Fermer", style="#94A3B8", no_wrap=True)

    def on_resize(self, event: events.Resize) -> None:
        self.call_after_refresh(self._refresh_display)

    def _refresh_display(self) -> None:
        if self.on_preview is not None and self.items and 0 <= self.highlighted_index < len(self.items):
            self.on_preview(self.items[self.highlighted_index])
        try:
            list_widget = self.query_one("#selector-list", Static)
            list_widget.update(self._render_items())
            if self.preview_renderer is not None:
                preview_widget = self.query_one("#selector-preview", Static)
                preview_widget.update(self._render_preview())
        except Exception:
            pass

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        if self.items and 0 <= self.highlighted_index < len(self.items):
            self.dismiss(self.items[self.highlighted_index])
        else:
            self.dismiss(None)

    def action_cursor_up(self) -> None:
        if self.items:
            self.highlighted_index = (self.highlighted_index - 1) % len(self.items)
            self._refresh_display()

    def action_cursor_down(self) -> None:
        if self.items:
            self.highlighted_index = (self.highlighted_index + 1) % len(self.items)
            self._refresh_display()

    def action_first(self) -> None:
        if self.items:
            self.highlighted_index = 0
            self._refresh_display()

    def action_last(self) -> None:
        if self.items:
            self.highlighted_index = len(self.items) - 1
            self._refresh_display()

    def action_page_up(self) -> None:
        if self.items:
            self.highlighted_index = max(0, self.highlighted_index - 5)
            self._refresh_display()

    def action_page_down(self) -> None:
        if self.items:
            self.highlighted_index = min(len(self.items) - 1, self.highlighted_index + 5)
            self._refresh_display()

    def on_key(self, event: events.Key) -> None:
        if event.key in "0123456789" and len(event.key) == 1:
            index = int(event.key) - self.number_start
            if 0 <= index < len(self.items):
                event.stop()
                self.highlighted_index = index
                self.dismiss(self.items[self.highlighted_index])


class ApprovalModal(ModalScreen[bool]):
    """Choix explicite pour une seule opération ; le refus est présélectionné."""

    DEFAULT_CSS = """
    ApprovalModal { align: center middle; background: rgba(13, 27, 42, 0.75); }
    #approval-dialog { width: 88; max-width: 95%; height: auto; max-height: 95%;
        background: #0D1B2A; border: round #E85D26; padding: 1 2; }
    #approval-title { text-style: bold; height: auto; margin-bottom: 1; }
    #approval-details { height: auto; }
    #approval-question { text-style: bold; height: auto; margin: 1 0; }
    #approval-choices { height: auto; }
    #approval-help { height: auto; margin-top: 1; }
    """
    BINDINGS = [
        Binding("escape", "refuse", "Refuser", priority=True, show=False),
        Binding("up", "toggle", "Choisir", priority=True, show=False),
        Binding("down", "toggle", "Choisir", priority=True, show=False),
        Binding("enter", "confirm", "Valider", priority=True, show=False),
        Binding("o", "choose_yes", "Autoriser", priority=True, show=False),
        Binding("n", "choose_no", "Refuser", priority=True, show=False),
    ]

    def __init__(self, question: str, details: dict[str, Any]) -> None:
        super().__init__()
        self.question = question
        self.details = details
        self.approve_selected = False

    def compose(self) -> ComposeResult:
        details = Text()
        for key, label in (("tool", "Outil"), ("command", "Commande"), ("details", "Précautions")):
            if self.details.get(key):
                if details.plain:
                    details.append("\n")
                details.append(f"{label} : ", style="bold")
                details.append(str(self.details[key]))
        with VerticalScroll(id="approval-dialog"):
            yield Static("◈ Autorisation requise", id="approval-title")
            yield Static(details, id="approval-details")
            yield Static(self.question, id="approval-question")
            yield Static(id="approval-choices")
            yield Static("↑↓ choisir · Entrée valider · Échap refuser", id="approval-help")

    def on_mount(self) -> None:
        theme = self.app.ui_theme
        dialog = self.query_one("#approval-dialog")
        dialog.styles.background = theme.app_bg
        dialog.styles.border = ("round", theme.primary)
        self.query_one("#approval-title").styles.color = theme.primary
        self.query_one("#approval-help").styles.color = theme.text_dim
        self._update_choices()

    def _update_choices(self) -> None:
        theme = self.app.ui_theme
        text = Text()
        for decision, label in ((False, "Refuser"), (True, "Autoriser cette opération")):
            active = self.approve_selected == decision
            text.append(("❯ " if active else "  ") + label,
                        style=f"bold {theme.primary}" if active else theme.text_main)
            if not decision:
                text.append("\n")
        self.query_one("#approval-choices", Static).update(text)

    def action_toggle(self) -> None:
        self.approve_selected = not self.approve_selected
        self._update_choices()

    def action_choose_yes(self) -> None:
        self.approve_selected = True
        self._update_choices()

    def action_choose_no(self) -> None:
        self.approve_selected = False
        self._update_choices()

    def action_confirm(self) -> None:
        self.dismiss(self.approve_selected)

    def action_refuse(self) -> None:
        self.dismiss(False)


class SettingsModal(ModalScreen[dict | None]):
    """Édition isolée des réglages Ollama ; aucun champ ne rejoint le REPL."""

    AUTO_FOCUS = "#settings-model"

    DEFAULT_CSS = """
    SettingsModal {
        align: center middle;
        background: rgba(13, 27, 42, 0.75);
    }
    #settings-dialog {
        width: 76;
        max-width: 95%;
        height: auto;
        max-height: 95%;
        background: #0D1B2A;
        border: round #38BDF8;
        padding: 1 2;
    }
    #settings-title { color: #E85D26; text-style: bold; margin-bottom: 1; }
    SettingsModal .settings-label { color: #38BDF8; height: auto; }
    SettingsModal Input, SettingsModal Select { margin-bottom: 1; }
    #settings-actions { height: auto; }
    #settings-actions Button { margin-right: 1; min-width: 10; }
    #settings-status { height: auto; min-height: 1; margin: 1 0; }
    #settings-help { color: #94A3B8; height: auto; }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Fermer", priority=True),
        Binding("enter", "save", "Enregistrer", show=False),
    ]

    def compose(self) -> ComposeResult:
        from focus_settings import REMOTE_DEFAULTS
        owner = self.app.repl
        self._active_provider = owner.settings.values['provider']
        self._form_family = self._active_provider if self._active_provider != 'ollama' else 'openai'
        self._active_connection = owner.settings.values.get('connection_kind', 'direct')
        self._form_provider = 'external' if self._active_provider != 'ollama' and self._active_connection == 'external' else self._active_provider
        self._active_model = getattr(owner.adapter, 'model', None) or owner.settings.values['model']
        host = owner.host
        endpoint = f"[{host}]:{owner.port}" if ':' in host else f"{host}:{owner.port}"
        self._endpoint = endpoint
        from focus_provider_profiles import ProviderProfiles
        self._profiles = ProviderProfiles(owner.settings)
        with VerticalScroll(id="settings-dialog"):
            yield Static("◈ Configuration UCHAMBUZI & Moteur IA", id="settings-title")
            yield Static("Fournisseur IA", classes="settings-label")
            yield Select([('Ollama local', 'ollama'), ('Claude API', 'anthropic'),
                          ('OpenAI API', 'openai'), ('Grok API', 'grok'),
                          ('Fournisseur externe', 'external')],
                         value=self._form_provider, allow_blank=False, id='settings-provider')
            yield Static('Famille du modèle chez le fournisseur externe', id='settings-family-label', classes='settings-label')
            yield Select([('Claude · Claude Code', 'anthropic'), ('OpenAI · Responses', 'openai'),
                          ('Grok · Responses', 'grok')], value=self._active_provider if self._active_provider != 'ollama' else 'openai',
                         allow_blank=False, id='settings-family')
            yield Static("Clé API · laisser vide pour conserver la clé actuelle", id="settings-secret-label", classes="settings-label")
            yield Input(password=True, placeholder="Clé API", id="settings-secret")
            yield Static("Option 1 · Modèle actif (Ollama local)", id="settings-model-label", classes="settings-label")
            yield Select([(Text(self._active_model + "  ✓ ACTIF"), self._active_model)],
                         value=self._active_model, allow_blank=False, id="settings-model")
            yield Static("Option 2 · Hôte & Port", id="settings-endpoint-label", classes="settings-label")
            yield Input(endpoint, placeholder="127.0.0.1:11434", id="settings-endpoint")
            defaults = REMOTE_DEFAULTS.get(self._active_provider, REMOTE_DEFAULTS['openai'])
            yield Static('Modèle distant · suggestion provisoire, selon la passerelle', id='settings-remote-model-label', classes='settings-label')
            yield Input(self._active_model if self._active_provider != 'ollama' else defaults[2], id='settings-remote-model')
            yield Select([], prompt='Modèles récupérés', id='settings-remote-models')
            yield Button('Rechercher les modèles', id='settings-discover')
            yield Static('Adresse HTTPS du fournisseur', id='settings-api-url-label', classes='settings-label')
            yield Input(owner.settings.values.get('api_base_url') or defaults[0], id='settings-api-url')
            yield Static('Nom de variable contenant la clé (pas la clé)', id='settings-key-env-label', classes='settings-label')
            yield Input(owner.settings.values.get('api_key_env') or defaults[1], id='settings-key-env')
            yield Static("Option 3 · Test de connexion", id="settings-test-label", classes="settings-label")
            with Horizontal(id="settings-actions"):
                yield Button("Tester", id="settings-test")
                yield Button("Enregistrer", variant="primary", id="settings-save")
                yield Button("Fermer", id="settings-cancel")
            yield Static("Découverte des modèles locaux…", id="settings-status")
            yield Static("Tab : naviguer · Entrée : enregistrer · Échap : annuler", id="settings-help")

    def on_mount(self) -> None:
        theme = self.app.ui_theme
        dialog = self.query_one("#settings-dialog")
        dialog.styles.background = theme.app_bg
        dialog.styles.border = ("round", theme.secondary)
        self.query_one("#settings-title").styles.color = theme.primary
        for label in self.query(".settings-label"):
            label.styles.color = theme.secondary
        self._probe_worker = None
        self._show_provider_fields(self._form_provider)
        if self._active_provider == 'ollama':
            self.call_after_refresh(self.action_test_connection)
        else:
            self.query_one('#settings-status', Static).update('Aucun contact distant automatique.')

    def _show_provider_fields(self, provider):
        remote = provider != 'ollama'
        if provider == 'external' and self.query_one('#settings-family', Select).value == 'anthropic':
            self.query_one('#settings-remote-models', Select).set_options([
                ('Claude Sonnet · alias à vérifier', 'sonnet'), ('Claude Opus · alias à vérifier', 'opus'),
                ('Claude Haiku · alias à vérifier', 'haiku')])
        self.query_one('#settings-family-label').display = provider == 'external'
        self.query_one('#settings-family').display = provider == 'external'
        for selector in ('#settings-secret-label', '#settings-secret', '#settings-remote-models', '#settings-discover'):
            self.query_one(selector).display = remote
        for selector in ('#settings-remote-model-label', '#settings-remote-model', '#settings-api-url-label',
                         '#settings-api-url', '#settings-key-env-label', '#settings-key-env'):
            self.query_one(selector).display = remote
        for selector in ('#settings-model-label', '#settings-model', '#settings-endpoint-label',
                         '#settings-endpoint', '#settings-test-label', '#settings-test'):
            self.query_one(selector).display = not remote

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        if event.select.id == 'settings-remote-models':
            self.query_one('#settings-remote-model', Input).value = str(event.value)
            return
        if event.select.id == 'settings-family':
            if self.query_one('#settings-provider', Select).value == 'external' and str(event.value) != self._form_family:
                from focus_settings import REMOTE_DEFAULTS
                self.query_one('#settings-key-env', Input).value = REMOTE_DEFAULTS[str(event.value)][1]
                self.query_one('#settings-secret', Input).value = ''
                self.query_one('#settings-remote-model', Input).value = REMOTE_DEFAULTS[str(event.value)][2]
                self.query_one('#settings-remote-models', Select).set_options([])
                self._show_provider_fields('external')
            self._form_family = str(event.value)
            return
        if event.select.id != 'settings-provider':
            return
        from focus_settings import REMOTE_DEFAULTS
        provider = str(event.value)
        if provider != self._form_provider:
            self.query_one('#settings-secret', Input).value = ''
        if provider != self._form_provider and provider in REMOTE_DEFAULTS:
            url, key_env, model = REMOTE_DEFAULTS[provider]
            self.query_one('#settings-api-url', Input).value = url
            self.query_one('#settings-key-env', Input).value = key_env
            self.query_one('#settings-remote-model', Input).value = model
        elif provider != self._form_provider and provider == 'ollama':
            selector = self.query_one('#settings-model', Select)
            selector.set_options([('redsage-qwen3:8b-dpo · suggestion provisoire', 'redsage-qwen3:8b-dpo')])
            selector.value = 'redsage-qwen3:8b-dpo'
        elif provider != self._form_provider and provider == 'external':
            self.query_one('#settings-api-url', Input).value = ''
            self.query_one('#settings-secret', Input).value = ''
        self._form_provider = provider
        self._show_provider_fields(provider)

    def _values(self) -> dict:
        from focus_settings import validate_ia, SettingsError, PROVIDER_TIMEOUTS
        choice = self.query_one('#settings-provider', Select).value
        provider = self.query_one('#settings-family', Select).value if choice == 'external' else choice
        if provider != 'ollama':
            return validate_ia(dict(self.app.repl.settings.values, provider=provider,
                connection_kind='external' if choice == 'external' else 'direct',
                model=self.query_one('#settings-remote-model', Input).value.strip(),
                api_base_url=self.query_one('#settings-api-url', Input).value.strip(),
                api_key_env=self.query_one('#settings-key-env', Input).value.strip(),
                timeout=PROVIDER_TIMEOUTS[str(provider)]))
        raw = self.query_one('#settings-endpoint', Input).value.strip()
        host, separator, port = raw.rpartition(':')
        if not separator:
            raise SettingsError("Format attendu : hôte:port (IPv6 : [::1]:11434).")
        host = host.removeprefix('[').removesuffix(']')
        return validate_ia(dict(self.app.repl.settings.values,
            provider='ollama', connection_kind='direct', model=self.query_one('#settings-model', Select).value,
            host=host, port=int(port), api_base_url='', api_key_env='',
            timeout=PROVIDER_TIMEOUTS['ollama']))

    def action_test_connection(self) -> None:
        if not self.is_current:
            return
        if self.query_one('#settings-provider', Select).value != 'ollama':
            self.query_one('#settings-status', Static).update('Aucun contact distant automatique.')
            return
        try:
            values = self._values()
        except (ValueError, TypeError, OverflowError) as exc:
            self._show_error(exc)
            return
        if self._probe_worker is not None:
            self._probe_worker.cancel()
        self.query_one('#settings-status', Static).update("Test de connexion…")
        self._probe_worker = self.run_worker(self._probe(values), exclusive=True)

    async def _probe(self, values: dict) -> None:
        from focus_providers import ConfiguredOllamaRuntime
        if values['host'] not in ('127.0.0.1', 'localhost', '::1'):
            self.query_one('#settings-status', Static).update(
                'Découverte distante désactivée ; utilisez /settings model pour saisir le modèle.')
            return
        runtime = ConfiguredOllamaRuntime(port=values['port'], timeout=2.0, host=values['host'])
        try:
            models = await asyncio.to_thread(runtime.list_models)
        except Exception:
            self.query_one('#settings-status', Static).update(
                "[bold red]✗ Injoignable[/] · Vérifiez l’hôte, le port et le serveur Ollama.")
            return
        # Une réponse à un ancien endpoint ne doit pas écraser le formulaire courant.
        endpoint = self.query_one('#settings-endpoint', Input).value.strip()
        expected_host = f"[{values['host']}]" if ':' in values['host'] else values['host']
        if endpoint != f"{expected_host}:{values['port']}":
            return
        selector = self.query_one('#settings-model', Select)
        selected = selector.value
        names = list(dict.fromkeys(str(getattr(model, 'id', model)) for model in models))
        options = []
        for name in dict.fromkeys([*names, selected]):
            label = Text(name)
            if name == self._active_model:
                label.append("  ✓ ACTIF", style="bold green")
            if name not in names:
                label.append(" · absent de cet hôte", style="dim")
            options.append((label, name))
        selector.set_options(options)
        selector.value = selected
        self.query_one('#settings-status', Static).update(
            f"[bold green]✓ Connecté[/] · {len(names)} modèle(s) local(aux).")

    def _show_error(self, exc: Exception) -> None:
        self.query_one('#settings-status', Static).update(
            Text("✗ Réglages non enregistrés : " + safe_display(exc), style="bold red"))

    def action_save(self) -> None:
        if self.app._current_ai_task is not None:
            self._show_error(ValueError("Appuyez sur Échap ou Ctrl+C avant de modifier le moteur."))
            return
        try:
            values = self._values()
            key = self.query_one('#settings-secret', Input).value
            if values['provider'] != 'ollama' and key:
                values = self._profiles.save_active_key(values, key)
            self.app.repl.apply_ia_settings(values)
            self.query_one('#settings-secret', Input).value = ''
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            self._show_error(exc)
            return
        self.dismiss(values)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def discover(self) -> None:
        try:
            values = self._values()
            key = self.query_one('#settings-secret', Input).value or os.environ.get(values['api_key_env'], '')
            if values['provider'] == 'anthropic' and values['connection_kind'] == 'external':
                raise ValueError('Claude Code : choisissez un alias suggéré ou saisissez un identifiant.')
            if not key:
                raise ValueError('Saisissez la clé ou chargez un accès enregistré.')
        except (ValueError, OSError) as exc:
            self._show_error(exc)
            return
        destination = values['api_base_url']
        def decided(approved):
            if not approved:
                return
            try:
                current = self._values()
                current_key = self.query_one('#settings-secret', Input).value or os.environ.get(current['api_key_env'], '')
                if current != values or current_key != key:
                    raise ValueError('Configuration modifiée ; recommencez la recherche.')
                self.run_worker(self._discover_models(values, key), exclusive=True)
            except (ValueError, OSError) as exc:
                self._show_error(exc)
        self.app.push_screen(ApprovalModal('Autoriser la recherche des modèles ?', {
            'details': 'Destination : ' + destination + '/models. La clé API sera transmise ; aucune conversation envoyée.'}), decided)

    async def _discover_models(self, values, key):
        from focus_provider_profiles import discover_models
        self.query_one('#settings-status', Static).update('Recherche du catalogue…')
        try:
            models = await asyncio.to_thread(discover_models, values, key)
            if not self.is_mounted or self._values() != values:
                return
            self.query_one('#settings-remote-models', Select).set_options([(m, m) for m in models])
            self.query_one('#settings-status', Static).update(f'{len(models)} modèle(s) reçus. Sélectionnez un modèle ou saisissez son identifiant.')
        except (ValueError, OSError) as exc:
            if self.is_mounted:
                self._show_error(exc)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        if event.input.id == 'settings-endpoint' and event.value != self._endpoint:
            self._endpoint = event.value
            if getattr(self, '_probe_worker', None) is not None:
                self._probe_worker.cancel()
            self.query_one('#settings-status', Static).update("Connexion à vérifier avec Tester.")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == 'settings-discover':
            self.discover()
        elif event.button.id == 'settings-test':
            self.action_test_connection()
        elif event.button.id == 'settings-save':
            self.action_save()
        elif event.button.id == 'settings-cancel':
            self.action_cancel()


class ThinkingIndicator(Static):
    """Widget animé de réflexion affichant un spinner braille et un chronomètre actif."""

    SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, model_name: str = "Ollama"):
        super().__init__()
        self.model_name = model_name
        self.start_time = time.monotonic()
        self.frame_idx = 0
        self._timer = None
        self.complete = False
        self.interrupted = False
        self.elapsed = 0.0
        self.reasoning_text = ""

    def append_thinking(self, text: str) -> None:
        self.reasoning_text += text

    def finish(self) -> None:
        if self.complete or self.interrupted:
            return
        self.complete = True
        self.elapsed = time.monotonic() - self.start_time
        if self._timer is not None:
            self._timer.stop()
        self._update_text()

    def interrupt(self) -> None:
        if self.interrupted:
            return
        self.interrupted = True
        self.elapsed = time.monotonic() - self.start_time
        if self._timer is not None:
            self._timer.stop()
        self._update_text()

    def on_mount(self) -> None:
        self._update_text()
        self._timer = self.set_interval(0.08, self._tick)

    def _tick(self) -> None:
        if self.complete or self.interrupted:
            return
        self.frame_idx = (self.frame_idx + 1) % len(self.SPINNER_FRAMES)
        self._update_text()

    def _update_text(self) -> None:
        elapsed = self.elapsed if (self.complete or self.interrupted) else (time.monotonic() - self.start_time)
        t = Text()
        if self.interrupted:
            t.append("✕ Réflexion interrompue ", style="bold #EF4444")
            t.append(f"({elapsed:.1f}s)", style="dim #94A3B8")
        elif self.complete:
            t.append("○ Réflexion ", style="bold #64748B")
            t.append(f"({elapsed:.1f}s)", style="dim #94A3B8")
        else:
            spinner = self.SPINNER_FRAMES[self.frame_idx]
            t.append(f"{spinner} Réflexion en cours... ", style="bold #38BDF8")
            t.append(f"({elapsed:.1f}s)", style="dim #94A3B8")
            t.append(" · Échap interrompre", style="dim #64748B")
        self.update(t)

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()


class ResponsiveLinuxDriver(LinuxDriver):
    """Conserve le parseur natif avec un réveil adapté à l'arrêt au clavier.

    Le pilote Textual 8 attend 100 ms entre ses ticks : raccourcir ESCDELAY
    seul ne suffit donc pas pour livrer Échap en moins de 50 ms.
    """

    native_selection = True

    def set_native_selection(self, enabled: bool) -> None:
        """Laisse le terminal hôte sélectionner sans exiger OSC 52, même en SSH."""
        if enabled:
            self._disable_mouse_support()
        self.native_selection = enabled
        if not enabled:
            self._enable_mouse_support()

    def _enable_mouse_support(self) -> None:
        # Une reprise après suspend() doit conserver le choix de l'utilisateur.
        if not self.native_selection:
            super()._enable_mouse_support()

    def run_input_thread(self) -> None:
        import codecs
        import selectors
        from textual import constants
        from textual._parser import ParseError
        from textual._xterm_parser import XTermParser

        constants.ESCAPE_DELAY = min(constants.ESCAPE_DELAY, 0.02)
        parser = XTermParser(self._debug)
        decode = codecs.getincrementaldecoder('utf-8')().decode
        with selectors.SelectSelector() as selector:
            selector.register(self.fileno, selectors.EVENT_READ)
            try:
                while not self.exit_event.is_set():
                    for _, mask in selector.select(0.005):
                        if mask & selectors.EVENT_READ:
                            raw = os.read(self.fileno, 4096)
                            if not raw:
                                return
                            for event in parser.feed(decode(raw)):
                                self.process_message(event)
                    for event in parser.tick():
                        self.process_message(event)
            finally:
                try:
                    for _ in parser.feed(''):
                        pass
                except (EOFError, ParseError):
                    pass


class UchambuziApp(App):
    """Application TUI réactive 2D UCHAMBUZI."""
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+c", "quit_app", "Quitter", show=True),
        Binding("escape", "dismiss_menu", "Fermer menu", show=False),
        Binding("f2", "select_team", "Changer de Team", show=False),
        Binding("f7", "toggle_native_selection", "Sélection terminal", show=False),
    ]

    def __init__(
        self,
        *,
        model: str | None = None,
        port: int = 11434,
        timeout: float = DEFAULT_TIMEOUT,
        runtime: Any = None,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
        case_id: str | None = None,
        theme_id: str | None = None,
    ) -> None:
        super().__init__(driver_class=ResponsiveLinuxDriver if sys.platform == 'linux' else None)
        self.model = model
        self.port = port
        self.timeout = timeout
        self.context_budget = context_budget
        self._native_selection = True
        
        # Thème UCHAMBUZI
        active_theme_key = theme_id if theme_id in THEMES else load_theme_preference()
        self.ui_theme: UITheme = THEMES.get(active_theme_key, THEMES[DEFAULT_THEME_ID])
        
        # Moteur métier complet UCHAMBUZI (FocusREPL)
        self.repl = FocusREPL(
            model=model,
            port=port,
            timeout=timeout,
            runtime=runtime,
            context_budget=context_budget,
            case_id=case_id,
            theme_id=theme_id,
        )
        self.repl._in_textual = True
        self.case_manager = self.repl.case_manager
        self._resume = ResumeSessions(SessionManager(user_data_path()), self.case_manager)
        self._saved_session = None
        self._pending_restore = None
        self._sync_from_repl()
        # Chaque lancement commence en Assist, même avec un ancien active_team persisté.
        self.active_team_name = ASSIST_TEAM.name
        self._terminal_palette_active = False
        self._terminal_title = None
        self._quit_armed_at = None
        self._pending_approval: dict[str, Any] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._shell_input_mode = False
        self._command_busy = False
        self._current_ai_task: asyncio.Task | None = None
        self._ai_cancellation: TurnCancellation | None = None
        self._ai_worker_finished: threading.Event | None = None
        self.repl._confirm = self._confirm_from_worker
        self.repl._legal_panel = self._legal_panel_from_worker

    def compose(self) -> ComposeResult:
        with TranscriptScroll(id="transcript"):
            yield Static(self._build_welcome_group(), id="welcome-banner")
            yield Vertical(id="dialogue")

        with Vertical(id="bottom-bar"):
            with Container(id="input-box"):
                with Horizontal(id="prompt-row"):
                    yield Static("❯ ", id="prompt-indicator")
                    yield InvestigationPrompt(placeholder="Posez une question, entrez un indicateur (IP, domaine...) ou tapez /", id="prompt-input")
                yield Static("Shell mode · Entrée : exécuter · Échap : conversation", id="shell-mode-hint")
            yield Static("", id="bottom-spacer")
            yield Static(self._build_status_bar(), id="status-bar")
        yield OptionList(id="slash-menu")

    def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.prompt_input = self.query_one("#prompt-input", InvestigationPrompt)
        self.slash_menu = self.query_one("#slash-menu", OptionList)
        self.transcript = self.query_one("#transcript", TranscriptScroll)
        self.dialogue = self.query_one("#dialogue", Vertical)
        self.status_bar = self.query_one("#status-bar", Static)
        from focus_settings import Preferences, SettingsError
        try:
            self._tip_preferences = Preferences()
            tips_enabled = self._tip_preferences.values['tips']
        except (SettingsError, OSError):
            self._tip_preferences = None
            tips_enabled = True
        self._set_tip(tips_enabled)
        self._apply_theme(self.ui_theme)
        self.prompt_input.focus()
        self.set_interval(0.15, self.update_status)
        if self.case_manager.active_case_id:
            self.call_after_refresh(self._choose_conversation)

    def _set_tip(self, enabled: bool) -> None:
        self._tips_enabled = enabled
        if not self._shell_input_mode:
            self.prompt_input.placeholder = self._tip_text()

    def _tip_text(self) -> str:
        if not getattr(self, '_tips_enabled', True):
            return 'Posez une question'
        if self.active_team_name == 'OSINT Team':
            return 'Entrez un indicateur ou tapez /tools pour voir les outils'
        return 'Posez une question, entrez un indicateur ou tapez /'

    def _save_tips(self, enabled: bool) -> None:
        if self._tip_preferences is None:
            self._print_system('Préférences indisponibles : conseil inchangé.')
            return
        try:
            self._tip_preferences.set('tips', enabled)
        except (OSError, ValueError) as exc:
            self._print_system('Préférence non enregistrée : ' + safe_display(exc))
            return
        self._set_tip(enabled)
        self._print_system('Conseils activés.' if enabled else 'Conseils masqués.')

    def open_tips_selector(self) -> None:
        enabled = self._tips_enabled
        items = [
            SelectorItem('on', 'Afficher les conseils', is_current=enabled),
            SelectorItem('off', 'Masquer les conseils', is_current=not enabled),
        ]

        def selected(item: SelectorItem | None) -> None:
            if item is not None:
                self._save_tips(item.id == 'on')
            self.prompt_input.focus()

        self.slash_menu.display = False
        self.push_screen(InteractiveSelectorModal('Conseils de saisie', items), callback=selected)

    def _build_welcome_group(self) -> Group:
        """Construit le bandeau officiel et la grille des 4 pôles cyber conformes à la maquette."""
        logo_text = build_banner_logo(self.ui_theme)
        heading = Text("U C H A M B U Z I", style=f"bold {self.ui_theme.primary}")
        heading.append(f"   v{VERSION}", style=self.ui_theme.text_dim)
        tagline = Text(TAGLINE, style=self.ui_theme.text_dim)

        info = Text()
        info.append("Spécialité : ", style="bold white")
        info.append(f"{self.active_team_name}", style=f"bold {self.ui_theme.secondary}")
        tagline_mode = "Assistant d'investigation générale" if self.active_team_name == "Assist" else "Investigation numérique"
        info.append(f" — {tagline_mode}\n", style=self.ui_theme.text_dim)

        model = getattr(self.repl.adapter, 'model', None) or self.model or 'redsage-qwen3:8b-dpo'
        location = 'distant' if self.session and self.session._requires_external_consent() else 'local'
        ai_status = f"{model} ({location})" if self.session else 'désactivé'
        info.append("Moteur IA  : ", style="bold white")
        info.append(f"{ai_status}\n", style=f"bold {self.ui_theme.success}" if self.session else f"bold {self.ui_theme.warning}")

        active_case = self.case_manager.active_case_id
        case_label = f"Dossier #{active_case} (actif)" if active_case else "Session temporaire (hors dossier)"
        info.append("Enquête    : ", style="bold white")
        info.append(case_label, style="white")

        details = Group(tagline, Rule(style="#334155"), info)
        layout = Table.grid(padding=(0, 2))
        layout.add_column(width=22, no_wrap=True)
        layout.add_column(ratio=1)
        layout.add_row(logo_text, Group(heading, details))

        banner_width = min(96, max(32, (self.size.width or 100) - 4))
        panel = Panel(
            layout,
            width=banner_width,
            title=f"[bold {self.ui_theme.primary}]◈ UCHAMBUZI[/] [dim]· Terminal d'investigation[/]",
            subtitle="[dim][bold white]/help[/] commandes · [bold white]/team[/] pôles cyber · [bold white]Ctrl+D[/] quitter[/]",
            border_style=self.ui_theme.primary,
            box=box.ROUNDED,
            padding=(0, 1),
        )

        grid = render_teams_mini_grid(self.repl.active_profile)
        grid.width = banner_width
        return Group(Align.center(panel), Text(""), Align.center(grid))

    def _build_status_bar(self) -> Text:
        """Réserve d'abord la place aux informations actives, puis aux raccourcis."""
        bg, fg = self.ui_theme.toolbar_bg, self.ui_theme.toolbar_fg
        width = self.size.width or 100
        style = f"bold {fg} on {bg}"
        team = next((t for t in (ASSIST_TEAM, *TEAMS) if t.name == self.active_team_name), None)
        model = str(getattr(self.repl.adapter, 'model', None) or self.model or 'redsage-qwen3:8b-dpo')
        if len(model) > (18 if width < 100 else 28):
            model = model[:15 if width < 100 else 25] + '…'
        active = self.repl.session is not None
        case = self.case_manager.active_case_id
        case_label = f"#{case}" if case else 'aucun'
        max_case = max(6, min(22, width // 6))
        if len(case_label) > max_case:
            case_label = case_label[:max_case - 1] + '…'
        fields = [
            ("◈ UCHAMBUZI", style),
            (self.active_team_name, f"bold black on {team.color if team else '#38BDF8'}"),
            (f"IA: {model}" if active else "IA: OFF", style if active else "bold white on #B91C1C"),
            (f"Dossier: {case_label}", style),
        ]
        if width >= 85:
            hint = 'Ctrl+Maj+C/V · F7: souris app' if self._native_selection else 'F7: sélection terminal'
            if width >= 120:
                hint += ' · /help'
            fields.append((hint, style))
        # Préserver le dossier lorsque le terminal est étroit.
        if width < 85 and sum(Text(label).cell_len for label, _ in fields) + 13 > width:
            fields[3] = (case_label if case else 'Sans dossier', style)
        text = Text('', style=style, no_wrap=True)
        base_width = sum(Text(label).cell_len + 2 for label, _ in fields) + len(fields) - 1
        extra, remainder = divmod(max(0, width - base_width), len(fields))
        for index, (label, field_style) in enumerate(fields):
            if index:
                text.append('│', style=style)
            padding = extra + (index < remainder)
            left = padding // 2
            right = padding - left
            text.append(f"{' ' * (left + 1)}{label}{' ' * (right + 1)}", style=field_style)
        text.truncate(width, overflow='ellipsis')
        return text

    def update_status(self) -> None:
        if hasattr(self, "status_bar"):
            self.status_bar.update(self._build_status_bar())
            usage = getattr(self.repl.session, 'context_usage', {})
            if isinstance(usage, dict):
                qualifier = '~' if usage.get('tokens_estimated', True) else ''
                self.status_bar.tooltip = (
                    f"Contexte session : {usage.get('used_bytes', 0)} / "
                    f"{usage.get('budget_bytes', self.context_budget)} octets · "
                    f"{qualifier}{usage.get('used_tokens', 0)} tokens"
                )
            self._sync_terminal_title()

    def _sync_terminal_title(self) -> None:
        case = self.case_manager.active_case_id
        suffix = f"#{case}" if case else self.active_team_name
        title = 'UCHAMBUZI — ' + safe_display(suffix).replace('\n', ' ').replace('\t', ' ')
        if self.is_headless or self._driver is None or title == self._terminal_title:
            return
        if self._terminal_title is None:
            self._driver.write('\033[22;0t')
        self._driver.write(f'\033]0;{title}\007\033]2;{title}\007')
        self._driver.flush()
        self._terminal_title = title

    def _restore_terminal_title(self) -> None:
        if self._terminal_title is not None and self._driver is not None:
            self._driver.write('\033[23;0t')
            self._driver.flush()
            self._terminal_title = None

    def _position_slash_menu(self) -> None:
        if not self.slash_menu.display:
            return
        height = min(8, self.slash_menu.option_count + 2)
        self.slash_menu.styles.width = max(10, self.size.width - 2)
        self.slash_menu.styles.height = height
        self.slash_menu.styles.offset = (1, max(0, self.query_one('#input-box').region.y - height))

    def on_resize(self, event: events.Resize) -> None:
        if hasattr(self, 'slash_menu'):
            self.call_after_refresh(self._position_slash_menu)
            self.call_after_refresh(self._refresh_welcome)
            self.call_after_refresh(self.update_status)

    def _refresh_welcome(self) -> None:
        # App.size n'est définitif qu'après la propagation du Resize à l'écran.
        for banner in self.query('#welcome-banner'):
            banner.update(self._build_welcome_group())
        self.transcript.follow_end()

    def _command_visible(self, command: str) -> bool:
        return command not in OSINT_COMMANDS or self.repl._osint_enabled(self.active_team_name)

    def _apply_theme(self, theme: UITheme) -> None:
        """Applique la palette aux widgets présents, y compris pendant un aperçu."""
        self.ui_theme = self.repl.theme = theme
        # Tous les écrans empilés doivent suivre l’aperçu, y compris la racine
        # masquée par la modale ; sinon sa fermeture révèle l’ancien fond.
        for screen in self.screen_stack:
            screen.styles.background = theme.app_bg
            screen.styles.color = theme.text_main
        for parent in self.query('#main-container, #transcript, #bottom-bar'):
            parent.styles.background = theme.app_bg
        self._sync_terminal_palette(theme)
        if not hasattr(self, 'status_bar'):
            return
        self.status_bar.styles.background = theme.toolbar_bg
        self.status_bar.styles.color = theme.toolbar_fg
        self.update_status()
        self.slash_menu.styles.background = theme.menu_bg
        self.slash_menu.styles.border = ('round', theme.secondary)
        self.prompt_input.styles.color = theme.text_main
        self.query_one('#prompt-indicator', Static).styles.color = theme.primary
        self._render_input_mode()
        for banner in self.query('#welcome-banner'):
            banner.update(self._build_welcome_group())
        if isinstance(self.screen, InteractiveSelectorModal):
            for container in self.screen.query('#selector-container'):
                container.styles.background = theme.app_bg
                container.styles.border = ('round', theme.secondary)
            for preview in self.screen.query('#selector-preview'):
                preview.styles.border = ('round', theme.secondary)
                preview.styles.background = theme.menu_meta_bg
        # Rich conserve aussi le fond hérité dans ses visuels mis en cache.
        # Un simple refresh laisse des rectangles de l’ancienne palette.
        for screen in self.screen_stack:
            for widget in screen.walk_children():
                widget.notify_style_update()
                widget.refresh()
        self.refresh(layout=True)

    def _sync_terminal_palette(self, theme: UITheme) -> None:
        """Écrit sur le terminal via le pilote, hors capture stdout de Textual."""
        if self.is_headless or self._driver is None:
            return
        self._driver.write(f"\033]11;{theme.app_bg}\007\033]10;{theme.text_main}\007")
        self._driver.flush()
        self._terminal_palette_active = True

    def _restore_terminal_palette(self) -> None:
        """Restaure les couleurs par défaut à chaque sortie, une seule fois."""
        if self._terminal_palette_active and self._driver is not None:
            self._driver.write("\033]111\007\033]110\007")
            self._driver.flush()
            self._terminal_palette_active = False

    def open_tools_browser(self, query: str = '') -> None:
        if not self._routing_allowed('/tools'):
            return
        from tools_browser import ToolsBrowserModal
        self.slash_menu.display = False
        self.push_screen(ToolsBrowserModal(query=query), callback=self._on_tools_browser_choice)

    def _on_tools_browser_choice(self, choice) -> None:
        if choice is None:
            self.prompt_input.focus()
            return
        if not self._routing_allowed('/tools'):
            return
        if choice.action == 'shell':
            self._start_background(self._prepare_tool_shell(choice.tool_id, choice.target), 'Préparation shell')
        elif choice.action in ('install', 'verify'):
            self._start_background(self._tool_maintenance(choice.action, choice.tool_id), 'Outils')
        elif choice.action == 'prepare':
            self._start_background(self._run_approved_command_async('/tools',
                'run '+choice.tool_id+' '+choice.target), 'Recherche accompagnée')
        elif choice.action == 'help':
            from tool_guidance import guide_for
            from focus_tool_registry import _reference
            guide = guide_for(choice.tool_id)
            reference, reference_label = _reference(choice.tool_id)
            self._print_system(Text(guide['help_hint']+'\n\nExemple : '+guide['example']+
                                    ('\n\n'+reference_label+'\n'+reference if reference else '')))
        self.prompt_input.focus()

    async def _tool_maintenance(self, action: str, tool_id: str) -> None:
        await self._run_approved_command_async('/tools', action+' '+tool_id)
        self.open_tools_browser(tool_id)

    async def _prepare_tool_shell(self, tool_id: str, target: str) -> None:
        import shlex
        from tool_guidance import build_command, resolve_shell, guide_for
        from tools_catalog import load_catalog
        from tools_installer import ToolsInstaller
        installer = ToolsInstaller(load_catalog())
        def prepare():
            executable = resolve_shell(tool_id, installer)
            if not executable:
                raise ValueError('Exécutable vérifié indisponible ; consultez /tools.')
            if target.strip() and guide_for(tool_id)['guided']:
                return build_command(tool_id, target.strip(), installer)['display']
            return shlex.join([executable, '--help'])
        try:
            command = await asyncio.to_thread(prepare)
        except (OSError, ValueError) as exc:
            self._print_system(Text('Préparation shell impossible : '+safe_display(exc)))
            return
        self._set_shell_input_mode(True)
        self.prompt_input.value = command
        self.prompt_input.focus()
        self._print_system(Text('Commande prête à modifier. Entrée demandera l’approbation ; rien n’a été exécuté.'))

    def open_theme_selector(self) -> None:
        previous = self.ui_theme

        items: list[SelectorItem] = [
            SelectorItem(
                id=key,
                title=theme.label,
                description="",
                badge="✓" if key == previous.name else "",
                is_current=(key == previous.name),
                color=theme.primary,
                text_only=True,
            )
            for key, theme in THEMES.items()
        ]

        def render_diff_preview(item: SelectorItem) -> Text:
            th = THEMES.get(item.id, THEMES[DEFAULT_THEME_ID])
            p = Text(no_wrap=True)
            p.append(" ◈ UCHAMBUZI │ Assist │ IA : modèle local │ Dossier : aucun ",
                     style=f"bold {th.toolbar_fg} on {th.toolbar_bg}")
            p.append("\n\n❯ ", style=f"bold {th.primary}")
            p.append("Posez une question ou tapez /", style=th.text_main)
            p.append("\n  Réponse de l’assistant", style=th.text_dim)
            return p

        def on_theme_selected(item: SelectorItem | None) -> None:
            if item is None:
                self._apply_theme(previous)
            else:
                chosen = THEMES[item.id]
                self._apply_theme(chosen)
                save_theme_preference(item.id)
                self._print_system(Text.assemble(('✓ Palette activée : ', 'bold green'), chosen.label))
            self.prompt_input.focus()

        self.slash_menu.display = False
        modal = InteractiveSelectorModal(
            title="Thèmes visuels",
            classes="theme-selector",
            subtitle="Choisissez une palette adaptée à votre terminal",
            items=items,
            on_preview=lambda item: self._apply_theme(THEMES[item.id]),
            preview_renderer=render_diff_preview,
        )
        self.push_screen(modal, callback=on_theme_selected)

    def open_scenario_selector(self) -> None:
        """Scénarios du profil actif, sans démarrer de commande d'investigation."""
        if not self._routing_allowed('/scenario'):
            return
        profile = self.repl.active_profile
        scenarios = self.repl.catalog.scenarios(profile.id) if profile else []
        if not scenarios:
            self._print_system(f"Aucun scénario disponible pour {profile.name if profile else 'ce profil'}.")
            return
        current = self.repl.active_scenario
        items = [SelectorItem(
            id=scenario.id, title=getattr(scenario, 'title', scenario.id),
            description=getattr(scenario, 'description', ''),
            badge='✓ ACTIF' if current and current.id == scenario.id else '',
            is_current=bool(current and current.id == scenario.id),
        ) for scenario in scenarios]
        items.append(SelectorItem('off', 'Mode libre', 'Quitter le scénario guidé',
                                  badge='✓ ACTIF' if current is None else '',
                                  is_current=current is None))

        def selected(item: SelectorItem | None) -> None:
            if item is not None and self._routing_allowed('/scenario'):
                with self.repl.console.capture() as capture:
                    self.repl.handle_scenario(item.id)
                self._sync_from_repl()
                self.update_status()
                if capture.get().strip():
                    self._print_system(Text.from_ansi(capture.get().strip()))
            self.prompt_input.focus()

        self.slash_menu.display = False
        self.push_screen(InteractiveSelectorModal(f"Scénarios · {profile.name if profile else 'OSINT'}", items), callback=selected)

    def _conversation_busy(self) -> bool:
        return (self._current_ai_task is not None or
                (self._ai_worker_finished is not None and not self._ai_worker_finished.is_set()))

    def _choose_conversation(self) -> None:
        """Choix explicite, après ouverture et vérification du dossier."""
        case_id = self.case_manager.active_case_id
        if not case_id or self._conversation_busy():
            return
        try:
            saved = self._resume.list_sessions()
        except (OSError, ValueError, KeyError) as exc:
            self._print_system(Text('Reprise indisponible : ' + safe_display(exc)))
            return
        items = [SelectorItem(id=':none', title='Continuer sans sauvegarder',
                              description='Les prochains échanges restent temporaires'),
                 SelectorItem(id=':new', title='Nouvelle conversation sauvegardée',
                              description='Conversation enregistrée localement en texte non chiffré')]
        items.extend(SelectorItem(id=item['id'], title=safe_display(item['name']),
                                  description=('Intégrité non vérifiée · reprise refusée' if item['corrupt'] else
                                               'Reprendre · ' + str(item.get('updated') or '')),
                                  available=not item['corrupt'])
                     for item in sorted(saved, key=lambda x: x.get('updated') or '', reverse=True))

        def selected(item: SelectorItem | None) -> None:
            if item is None or item.id == ':none':
                return
            if not item.available:
                self._print_system('Reprise refusée : conversation non vérifiée. Les fichiers sont conservés.')
                return
            if self.case_manager.active_case_id != case_id or self._conversation_busy():
                self._print_system('Reprise annulée : le dossier ou la génération a changé.')
                return
            try:
                if item.id == ':new':
                    session = self._resume.create()
                else:
                    session = self._resume.open(item.id, recover_interrupted=True)
                messages, excluded = conversation_messages(session)
                self.repl._reset_sessions_for_case_change()
                self._saved_session = session
                self._pending_restore = messages
                self._restore_waiting()
                for message in session.data['messages']:
                    prefix = '❯ ' if message['role'] == 'user' else 'IA · '
                    suffix = '' if message['state'] == 'complete' else ' [' + message['state'] + ']'
                    self._print_system(Text(prefix + safe_display(message['text']) + suffix))
                self._print_system(Text('Conversation sauvegardée active. '
                                        'Aucune autorisation restaurée. '
                                        f'{excluded} élément(s) exclu(s) du contexte IA.'))
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                self._saved_session = None
                self._print_system(Text('Reprise impossible : ' + safe_display(exc)))

        self.push_screen(InteractiveSelectorModal(
            'Conversation du dossier ' + safe_display(case_id), items,
            subtitle='Reprise : vérifier qu’aucune autre instance ne traite cette session'), callback=selected)

    def _restore_waiting(self) -> None:
        messages = getattr(self, '_pending_restore', None)
        session = getattr(self, '_saved_session', None)
        runtime = getattr(self.repl, 'session', None)
        if messages is None or session is None or runtime is None:
            return
        try:
            self._resume.check(session)
            verified = self._resume.open(session.data['id'])
            if verified.data['revision'] != session.data['revision']:
                raise ValueError('Conversation modifiée depuis son ouverture')
            messages, _ = conversation_messages(verified)
            runtime.reset()
            runtime.messages = messages
            self._pending_restore = None
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            self._saved_session = self._pending_restore = None
            self._print_system(Text('Reprise IA impossible : ' + safe_display(exc)))

    def _persist_start(self, query: str):
        session = self._saved_session
        if session is None:
            return None
        try:
            self._resume.check(session)
            if _SECRET.search(query) or detect_prompt_injection(query):
                self._print_system('Échange non sauvegardé : contenu sensible ou injection détectée.')
                return None
            turn = uuid.uuid4().hex
            session.add_message('user', query, turn)
            return session, session.add_message('assistant', '', turn, state='running')
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            self._saved_session = None
            self._print_system(Text('Sauvegarde suspendue : ' + safe_display(exc)))
            return None

    def _persist_finish(self, pending, text: str, state: str) -> None:
        if pending is None:
            return
        session, message_id = pending
        try:
            self._resume.check(session)
            if state != 'complete' or _SECRET.search(text) or detect_prompt_injection(text):
                if state == 'complete':
                    self._print_system('Réponse non sauvegardée : contenu sensible ou injection détectée.')
                    state = 'failed'
                text = ''
            session.update_message(message_id, text, state)
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            self._saved_session = None
            self._print_system(Text('Sauvegarde suspendue : ' + safe_display(exc)))

    def open_case_selector(self) -> None:
        """Ouvre un dossier existant avec les contrôles de structure du moteur."""
        try:
            cases = self.case_manager.list_cases()
        except (OSError, ValueError) as exc:
            self._print_system(Text('Lecture impossible : ' + safe_display(exc), style=self.ui_theme.danger))
            return
        items = [SelectorItem(id=':create', title='Créer un dossier',
                              description='Choisir un identifiant et un titre pour une nouvelle enquête')]
        for case in cases:
            current = case['case_id'] == self.case_manager.active_case_id
            available = case.get('structure') == 'valid'
            status = 'Dossier inaccessible' if not available else ('Archivé' if case.get('archived_at') else ('Clôturé' if case.get('closed_at') else 'Ouvert'))
            items.append(SelectorItem(
                id=case['case_id'], title=safe_display(case['case_id']),
                description=f"{safe_display(case.get('title') or 'Sans titre')} · {status}",
                badge='✓ ACTIF' if current else '', is_current=current, available=available,
            ))

        def selected(item: SelectorItem | None) -> None:
            if item is not None:
                if item.id == ':create':
                    self.prompt_input.value = '/investigation create '
                    self.prompt_input.focus()
                    return
                if item.available:
                    self._start_background(self._run_approved_command_async('/investigation', f'open {item.id}'),
                                           "Ouverture du dossier")
                else:
                    self._print_system('Dossier non ouvert : vérifiez sa structure avec /investigation status.')
            self.prompt_input.focus()

        self.slash_menu.display = False
        self.push_screen(InteractiveSelectorModal("Dossiers d’enquête", items), callback=selected)

    def open_ai_selector(self) -> None:
        model = getattr(self.adapter, 'model', None) or self.model or 'redsage-qwen3:8b-dpo'
        active = self.repl.session is not None
        items = [
            SelectorItem('current', f'Modèle : {model}', f'Ollama {self.host}:{self.port}',
                         badge='✓ ACTIF' if active else 'IA: OFF', is_current=active),
            SelectorItem('models', 'Changer de modèle', 'Modèles disponibles sur Ollama'),
            SelectorItem('off', 'Désactiver le moteur IA', 'IA: OFF', is_current=not active),
            SelectorItem('settings', 'Paramètres de connexion', 'Hôte & Port'),
        ]

        def on_ai_selected(item: SelectorItem | None) -> None:
            if item is None:
                self.prompt_input.focus()
            elif item.id == 'off':
                self._interrupt_ai()
                self.handle_ai('off')
            elif item.id == 'current':
                if self._current_ai_task is None:
                    self.handle_ai('on')
                else:
                    self._print_system('Appuyez sur Échap ou Ctrl+C avant de changer le moteur.')
            elif item.id == 'models':
                self.open_model_selector()
            elif item.id == 'settings':
                self.open_settings()

        self.slash_menu.display = False
        self.push_screen(InteractiveSelectorModal('Moteur IA', items), callback=on_ai_selected)

    def _set_shell_input_mode(self, enabled: bool) -> None:
        self._shell_input_mode = enabled
        self.slash_menu.display = False
        self._render_input_mode()

    def _render_input_mode(self) -> None:
        """Distinguish the shell composer immediately, before any submission."""
        if not hasattr(self, 'prompt_input'):
            return
        active = getattr(self, '_shell_input_mode', False)
        theme = self.ui_theme
        indicator = self.query_one('#prompt-indicator', Static)
        indicator.update('! ' if active else '❯ ')
        indicator.styles.color = theme.danger if active else theme.primary
        self.query_one('#input-box').styles.background = theme.menu_meta_bg if active else theme.app_bg
        hint = self.query_one('#shell-mode-hint', Static)
        hint.display = active
        hint.styles.color = theme.danger
        self.prompt_input.placeholder = ('Commande Bash…' if active else
                                         self._tip_text())

    @on(InvestigationPrompt.Changed)
    def on_input_changed(self, event: InvestigationPrompt.Changed) -> None:
        if event.input is not self.prompt_input or isinstance(self.screen, ModalScreen):
            return
        self._quit_armed_at = None
        val = event.value
        if not self._shell_input_mode and val.startswith('!') and not self._pending_approval:
            self._set_shell_input_mode(True)
            self.prompt_input.value = val[1:]
            return
        if self._shell_input_mode:
            self.slash_menu.display = False
            return
        if self.prompt_input.browsing_history:
            self.slash_menu.display = False
            return
        self.call_after_refresh(self._position_slash_menu)
        if val.startswith("/") and not any(char.isspace() for char in val):
            prefix = val.lower()
            matches = []
            # Commandes principales en anglais uniquement
            for cmd in COMMAND_REGISTRY.all_commands():
                if not self._command_visible(cmd.name):
                    continue
                if cmd.name.lower().startswith(prefix):
                    matches.append((cmd.name, cmd.summary))

            if matches:
                self.slash_menu.clear_options()
                for name, summary in matches[:10]:
                    label = Text()
                    label.append(f"{name:<16}", style=f"bold {self.ui_theme.primary}")
                    label.append(summary, style=self.ui_theme.text_dim)
                    self.slash_menu.add_option(Option(prompt=label, id=name))
                self.slash_menu.highlighted = 0
                self.slash_menu.display = True
                return

        self.slash_menu.display = False

    async def on_event(self, event: events.Event) -> None:
        # Intercepter avant le composant ciblé : ni l'éditeur ni le menu ne
        # doivent absorber la molette destinée à l'historique de conversation.
        if isinstance(event, (events.InputEvent, events.Paste)) and not event.is_forwarded and not isinstance(self.screen, ModalScreen):
            if isinstance(event, (events.MouseScrollUp, events.MouseScrollDown)) and hasattr(self, 'transcript'):
                self.transcript.scroll_history(-1 if isinstance(event, events.MouseScrollUp) else 1)
                event.stop()
                event.prevent_default()
                return
            if isinstance(event, (events.Key, events.Paste)) and hasattr(self, 'prompt_input'):
                if isinstance(event, events.Key):
                    self.on_key(event)
                    if event._stop_propagation:
                        return
                # Sélectionner du texte reste possible ; la prochaine frappe
                # retrouve l'éditeur sans demander de cliquer dans le prompt.
                self.screen.set_focus(self.prompt_input, scroll_visible=False)
        elif isinstance(event, events.Key) and not event.is_forwarded:
            self.on_key(event)
            if event._stop_propagation:
                return
        await super().on_event(event)

    def on_text_selected(self, event: events.TextSelected) -> None:
        """Copie la sélection du dialogue au relâchement de la souris."""
        if isinstance(self.screen, ModalScreen):
            return
        selected = self.screen.get_selected_text()
        if selected:
            self.copy_to_clipboard(selected)

    def on_key(self, event: events.Key) -> None:
        if isinstance(self.screen, ModalScreen):
            if event.key == 'ctrl+c' and hasattr(self.screen, 'action_cancel'):
                event.stop()
                event.prevent_default()
                self.screen.action_cancel()
            return
        key = event.key
        if not self._pending_approval:
            if not self._shell_input_mode and event.character == '!' and not self.prompt_input.value:
                event.stop()
                event.prevent_default()
                self._set_shell_input_mode(True)
                return
            if self._shell_input_mode and (key == 'escape' or (key == 'backspace' and not self.prompt_input.value)):
                event.stop()
                event.prevent_default()
                self._set_shell_input_mode(False)
                return
        if key != 'ctrl+c':
            self._quit_armed_at = None
        action = None
        if key in ('ctrl+shift+c', 'f6'):
            action = self.action_copy_response
        elif key == 'f7':
            action = self.action_toggle_native_selection
        elif key == 'ctrl+c':
            action = self.action_quit_app
        elif key in ('escape', 'ctrl+u'):
            action = self.action_dismiss_menu if key == 'escape' else self.prompt_input.action_clear_prompt
        elif key == 'ctrl+l':
            action = lambda: self.run_worker(self._clear_display())
        elif key == 'ctrl+d':
            action = self.action_exit_app
        elif key == 'pageup':
            action = self.transcript.scroll_page_up
        elif key == 'pagedown':
            action = self.transcript.scroll_page_down
        elif self.slash_menu.display and key in ('up', 'down'):
            action = self.action_menu_up if key == 'up' else self.action_menu_down
        elif key == 'tab':
            # Le prompt reste l'éditeur actif même sans candidat de complétion.
            action = lambda: None
            if self.slash_menu.display and self.slash_menu.option_count:
                action = self.action_menu_select
            else:
                prefix = self.prompt_input.value.lower()
                if prefix.startswith('/') and not any(char.isspace() for char in prefix):
                    match, _ = COMMAND_REGISTRY.resolve_command_prefix(prefix)
                    if match is not None and self._command_visible(COMMAND_REGISTRY.resolve(match)):
                        action = lambda: self._insert_slash_option(match)
        if action is None:
            return
        event.stop()
        event.prevent_default()
        action()

    async def _clear_display(self) -> None:
        """Efface la vue, sans toucher aux messages IA ni à la saisie/historique."""
        self.slash_menu.display = False
        await self.transcript.query('#welcome-banner').remove()
        keep = {getattr(self, '_active_answer', None), getattr(self, '_active_thinking', None)}
        await self.dialogue.remove_children([child for child in self.dialogue.children if child not in keep])
        self.transcript.follow_output = True
        self.transcript.follow_end()
        self.prompt_input.focus()

    def _insert_slash_option(self, name: str) -> None:
        if any(char.isspace() for char in self.prompt_input.value):
            self.slash_menu.display = False
            return
        self.prompt_input.value = f"{name} "
        self.prompt_input.cursor_position = len(self.prompt_input.value)
        self.slash_menu.display = False
        self.prompt_input.focus()

    def action_menu_up(self) -> None:
        if self.slash_menu.display:
            idx = self.slash_menu.highlighted
            if idx is not None and idx > 0:
                self.slash_menu.highlighted = idx - 1
            elif idx is None and self.slash_menu.option_count > 0:
                self.slash_menu.highlighted = self.slash_menu.option_count - 1

    def action_menu_down(self) -> None:
        if self.slash_menu.display:
            idx = self.slash_menu.highlighted
            if idx is not None and idx < self.slash_menu.option_count - 1:
                self.slash_menu.highlighted = idx + 1
            elif idx is None and self.slash_menu.option_count > 0:
                self.slash_menu.highlighted = 0

    def action_menu_select(self) -> None:
        if self.slash_menu.display:
            opt = None
            if self.slash_menu.highlighted is not None:
                opt = self.slash_menu.get_option_at_index(self.slash_menu.highlighted)
            elif self.slash_menu.option_count > 0:
                opt = self.slash_menu.get_option_at_index(0)
            if opt and opt.id:
                self._insert_slash_option(opt.id)

    def action_dismiss_menu(self) -> None:
        if self._current_ai_task is not None:
            self._interrupt_ai()
        elif self.prompt_input.value:
            self.prompt_input.action_clear_prompt()
        self.slash_menu.display = False
        self.prompt_input.focus()

    def action_select_team(self) -> None:
        self.open_team_selector()

    def action_cycle_team(self) -> None:
        self.open_team_selector()

    def open_team_selector(self) -> None:
        """Ouvre le sélecteur interactif élégant des modes et pôles cyber (style Codex CLI)."""
        items = []
        is_assist_curr = (self.active_team_name == "Assist")
        items.append(SelectorItem(
            id="assist",
            title="Assist",
            description="Assistant d'investigation générale et dialogue IA",
            badge="✓ ACTIF" if is_assist_curr else "",
            is_current=is_assist_curr,
            available=True,
            raw=ASSIST_TEAM,
        ))
        for t in TEAMS:
            is_curr = (t.name == self.active_team_name)
            badge = "✓ ACTIF" if is_curr else ("" if t.available else "🔒 Bientôt disponible")
            items.append(SelectorItem(
                id=t.slug,
                title=t.name,
                description=t.description,
                badge=badge,
                is_current=is_curr,
                available=t.available,
                raw=t,
            ))

        def on_team_selected(item: SelectorItem | None) -> None:
            if item is None:
                if hasattr(self, "prompt_input"):
                    self.prompt_input.focus()
                return
            if item.id in ("assist", "assistant"):
                self._start_background(self._activate_team("assist"), "Mode Assist")
            else:
                team = item.raw if isinstance(item.raw, Team) else get_team(item.id)
                if not team:
                    if hasattr(self, "prompt_input"):
                        self.prompt_input.focus()
                    return
                self._start_background(self._activate_team(team.slug), "Changement de pôle")
            if hasattr(self, "prompt_input"):
                self.prompt_input.focus()

        modal = InteractiveSelectorModal(
            title="Équipes d’investigation",
            subtitle="Choisissez votre espace de travail",
            items=items,
            number_start=0,
        )
        self.push_screen(modal, callback=on_team_selected)

    def open_model_selector(self) -> None:
        """Ouvre le sélecteur interactif élégant des modèles IA locaux (style Codex CLI)."""
        if not self._routing_allowed("/models"):
            return
        if self._current_ai_task is not None:
            self._print_system('Appuyez sur Échap ou Ctrl+C avant de changer le modèle.')
            return
        self.run_worker(self._load_model_selector(), exclusive=True, group='model-discovery')

    async def _load_model_selector(self) -> None:
        try:
            models = await asyncio.to_thread(self._ollama_models)
        except Exception as exc:
            models = []
            self._print_system(f"[{self.ui_theme.warning}]Impossible de joindre le serveur Ollama local : {safe_display(exc)}[/{self.ui_theme.warning}]")
            return

        if not models:
            self._print_system(f"[{self.ui_theme.warning}]Aucun modèle local détecté sur le serveur Ollama. Lancez ollama serve ou téléchargez RedSage via le catalogue Ollama.[/{self.ui_theme.warning}]")
            return

        current_model = getattr(self.adapter, 'model', None) or getattr(self.repl.adapter, 'model', None) or self.model or 'redsage-qwen3:8b-dpo'

        items = []
        for m in models:
            m_str = getattr(m, 'id', str(m))
            is_curr = (m_str == current_model and self.repl.session is not None)
            items.append(SelectorItem(
                id=m_str,
                title=m_str,
                description="Modèle local Ollama",
                badge="✓ ACTIF" if is_curr else "",
                is_current=is_curr,
                available=True,
            ))

        def on_model_selected(item: SelectorItem | None) -> None:
            if item is None:
                if hasattr(self, "prompt_input"):
                    self.prompt_input.focus()
                return
            if self._current_ai_task is not None:
                self._print_system('Appuyez sur Échap ou Ctrl+C avant de changer le modèle.')
                return
            if self.handle_settings(f"model {item.id}", ollama=True):
                self._print_system(Text.assemble(('✓ Modèle IA activé : ', 'bold green'), item.id))
            self.update_status()
            if hasattr(self, "prompt_input"):
                self.prompt_input.focus()

        modal = InteractiveSelectorModal(
            title="Modèles IA locaux",
            subtitle="Choisissez un modèle disponible sur Ollama",
            items=items,
        )
        self.push_screen(modal, callback=on_model_selected)

    def _interrupt_ai(self, *, announce: bool = True) -> None:
        task = self._current_ai_task
        cancellation = self._ai_cancellation
        if task is not None and not task.done() and cancellation is not None and cancellation.cancel():
            task.cancel()
            if announce:
                self._print_system("[dim orange1]Génération interrompue.[/]")

    def action_exit_app(self) -> None:
        self._interrupt_ai(announce=False)
        self._restore_terminal_title()
        self._restore_terminal_palette()
        self.exit()

    def action_quit_app(self) -> None:
        selected = self.screen.get_selected_text()
        if selected:
            self.screen.clear_selection()
            if self._current_ai_task is not None:
                self._interrupt_ai()
            elif self.prompt_input.value:
                self.prompt_input.action_clear_prompt()
                self.slash_menu.display = False
            self._quit_armed_at = None
            return
        if self.prompt_input.value:
            self.prompt_input.action_clear_prompt()
            self.slash_menu.display = False
            self._quit_armed_at = None
        elif self._current_ai_task is not None:
            self._interrupt_ai()
            self._quit_armed_at = None
        else:
            now = time.monotonic()
            if self._quit_armed_at is not None and now - self._quit_armed_at < 3:
                self.action_exit_app()
            else:
                self._quit_armed_at = now
                self._print_system('Appuyez à nouveau pour quitter')

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list is not self.slash_menu or isinstance(self.screen, ModalScreen):
            return
        if event.option_id:
            self._insert_slash_option(event.option_id)

    def _sync_from_repl(self) -> None:
        """Synchronise l'état du runtime IA, modèle et session depuis FocusREPL."""
        previous = getattr(self, 'session', None)
        for name in ('settings', 'adapter', 'host', 'port', 'timeout', 'model', 'session', 'provider_manager'):
            if hasattr(self.repl, name):
                setattr(self, name, getattr(self.repl, name))
        if (previous is not getattr(self, 'session', None) and
                getattr(self, '_saved_session', None) is not None and
                self._pending_restore is None):
            self._pending_restore = conversation_messages(self._saved_session)[0]
        self._restore_waiting()

    def _ollama_models(self) -> list[str]:
        return self.repl._ollama_models()

    def open_settings(self) -> None:
        self.slash_menu.display = False
        self.push_screen(SettingsModal(), callback=self._on_settings_closed)

    def _on_settings_closed(self, values: dict | None) -> None:
        if values is not None:
            self._sync_from_repl()
            self.update_status()
            self._print_system("✓ Configuration IA enregistrée.")
        self.prompt_input.focus()

    def handle_settings(self, argument: str = "", **kwargs) -> bool:
        if not self._routing_allowed("/settings"):
            return False
        with self.repl.console.capture() as capture:
            result = self.repl.handle_settings(argument, **kwargs)
        out = capture.get().strip()
        if out:
            self._print_system(Text.from_ansi(out))
        if result:
            self._sync_from_repl()
        self.update_status()
        return result

    def handle_ai(self, argument: str = "") -> None:
        if argument.strip().lower() != "off" and not self._routing_allowed("/ai"):
            return
        with self.repl.console.capture() as capture:
            self.repl.handle_ai(argument)
        out = capture.get().strip()
        if out:
            self._print_system(Text.from_ansi(out))
        self._sync_from_repl()
        self.update_status()

    async def _dispatch_command(self, cmd_line: str) -> None:
        parts = cmd_line.split(maxsplit=1)
        raw_cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        canonical = ALIASES_MAP.get(raw_cmd, raw_cmd)
        await self._execute_canonical_command(canonical, arg)

    @on(InvestigationPrompt.Submitted)
    async def on_input_submitted(self, event: InvestigationPrompt.Submitted) -> None:
        if event.input is not self.prompt_input or isinstance(self.screen, ModalScreen):
            return
        raw_text = event.value.strip()
        if not raw_text and not self._pending_approval:
            return

        if self._shell_input_mode and not self._pending_approval:
            raw_text = '!' + raw_text
            self._set_shell_input_mode(False)
        self.prompt_input.value = ""

        if self.repl._development_team(self.active_team_name):
            if self._pending_approval:
                self._pending_approval['resolve'](False)
                self._pending_approval = None
            if not raw_text.startswith('/') and not getattr(self, '_pending_team_choice', False):
                self._routing_allowed()
                return

        # 0 bis. Approbation interactive si en attente
        if self._pending_approval:
            ans = raw_text.lower()
            resolve = self._pending_approval["resolve"]
            self._pending_approval = None
            approved = ans in ("o", "oui", "y", "yes")
            resolve(approved)
            if not approved:
                self._print_system("Exécution annulée par l'enquêteur.")
            return

        if self._command_busy:
            self._print_system("Une commande est en cours. Terminez l’approbation affichée avant d’en lancer une autre.")
            return

        # 0 ter. Choix direct de team après /team
        if getattr(self, '_pending_team_choice', False):
            self._pending_team_choice = False
            team = get_team(raw_text)
            if team:
                self._start_background(self._activate_team(team.slug), "Changement de pôle")
                self.update_status()
                return

        # 1. Sélection automatique du menu slash si ouvert (style Codex / Claude Code)
        text_to_exec = raw_text
        if self.slash_menu.display and not any(char.isspace() for char in raw_text):
            if self.slash_menu.highlighted is not None:
                opt = self.slash_menu.get_option_at_index(self.slash_menu.highlighted)
                if opt and opt.id:
                    text_to_exec = opt.id
            elif self.slash_menu.option_count > 0:
                opt = self.slash_menu.get_option_at_index(0)
                if opt and opt.id:
                    text_to_exec = opt.id
            self.slash_menu.display = False

        self.dialogue.display = True
        self.prompt_input.remember(text_to_exec)
        self.slash_menu.display = False
        self.transcript.follow_output = True

        # Affichage du prompt utilisateur dans le transcript
        user_line = Text()
        if text_to_exec.startswith('!'):
            user_line.append('! ', style=f'bold {self.ui_theme.danger}')
            user_line.append(text_to_exec[1:].lstrip(), style=self.ui_theme.text_main)
        else:
            user_line.append("❯ ", style="bold #E85D26")
            user_line.append(text_to_exec, style="bold white")
        await self.dialogue.mount(Static(user_line, classes="user-message"))
        self.transcript.scroll_end(animate=False)

        # 2. Résolution des commandes slash et des préfixes abrégés (/he -> /help, /se -> /settings)
        if text_to_exec.startswith('/'):
            parts = text_to_exec.split(maxsplit=1)
            raw_token = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            resolved_cmd, matches = COMMAND_REGISTRY.resolve_command_prefix(raw_token)
            if resolved_cmd:
                canonical_cmd = COMMAND_REGISTRY.resolve(resolved_cmd)
                await self._execute_canonical_command(canonical_cmd, arg)
            elif len(matches) > 1:
                matches_str = ", ".join(matches)
                self._print_system(f"Commande ambiguë '{raw_token}' : correspond à {matches_str}")
            else:
                self._print_system(f"Commande inconnue : {raw_token}. Tapez /help pour l'aide.")
        elif text_to_exec.startswith('!'):
            self._start_background(self._shell_turn(text_to_exec[1:].strip()), 'Shell libre')
        else:
            await self._dispatch_ai(text_to_exec)

        self.update_status()

    def _print_system(self, content: Any) -> None:
        if not hasattr(self, "transcript"):
            return
        if isinstance(content, str):
            try:
                renderable = Text.from_markup(content)
            except Exception:
                renderable = Text(content, style="#94A3B8")
        else:
            renderable = content
        self.dialogue.display = True
        widget = SelectableStatic(renderable, classes="system-response")
        self.dialogue.mount(widget)
        # Les dimensions ne sont fiables qu'après le montage et la mise en page.
        self.call_after_refresh(self._reveal_response, widget, renderable)

    def _reveal_response(self, widget: Static, content: Any) -> None:
        if widget.parent is not self.dialogue:
            return
        if not self.transcript.follow_output:
            return
        if widget.size.height > self.transcript.scrollable_content_region.height:
            widget.update(Group(content, Text(
                "↓ Suite du contenu (utilisez PageDown ou la molette pour défiler)",
                style="dim cyan",
            )))
            self.call_after_refresh(
                self.transcript.scroll_to_widget, widget, top=True, animate=False,
            )
        elif widget.size.height > 1:
            self.transcript.scroll_to_widget(widget, top=True, animate=False)
        else:
            self.transcript.scroll_end(animate=False)

    def _emit_system(self, content: Any) -> None:
        import threading
        if getattr(self, '_thread_id', None) == threading.get_ident():
            self._print_system(content)
        else:
            self.call_from_thread(self._print_system, content)

    def _routing_allowed(self, command=None) -> bool:
        with self.repl.console.capture() as capture:
            allowed = (self.repl._command_allowed(command, self.active_team_name)
                       if command is not None else
                       not self.repl._intercept_development_team(self.active_team_name))
        output = capture.get().strip()
        if output:
            self._print_system(Text.from_ansi(output))
        return allowed

    async def _execute_canonical_command(self, cmd: str, arg: str) -> None:
        """Route et exécute les commandes canoniques avec capture complète du moteur FocusREPL."""
        if cmd == '/investigation' and self._conversation_busy() and (not arg or arg.split()[0].lower() in ('list', 'menu', 'open', 'create', 'close', 'archive', 'delete')):
            self._print_system('Terminez ou interrompez la génération avant de changer de dossier.')
            return
        if not self._routing_allowed(cmd):
            return
        if cmd == '/tips':
            option = arg.strip().lower()
            if option in ('on', 'off'):
                self._save_tips(option == 'on')
            else:
                self.open_tips_selector()
            return
        if cmd == '/tools':
            from tools_catalog import SPECIALTIES, load_catalog
            key = arg.strip().lower()
            tool_ids = {row['id'] for row in load_catalog()}
            if key in ('', 'menu') or key in SPECIALTIES or key in tool_ids:
                self.open_tools_browser(key)
                return
        if cmd == '/terminal':
            self._start_background(self._shell_turn(None), 'Terminal libre')
            return
        if cmd == '/copy':
            if arg.strip().lower() in ('native', 'terminal'):
                self.action_toggle_native_selection()
            elif arg.strip().lower() in ('commande', 'command'):
                command = getattr(self, '_last_prepared_command', None)
                if command:
                    self.copy_to_clipboard(command)
                    self.notify('Commande copiée.')
                else:
                    self.notify('Aucune commande préparée à copier.')
            else:
                self.action_copy_response()
            return
        if cmd == '/theme' and arg.lower() in ('', 'list', 'liste', 'menu'):
            self.open_theme_selector()
            return
        if cmd == '/scenario' and arg.lower() in ('', 'list', 'liste', 'menu'):
            self.open_scenario_selector()
            return
        if cmd == '/investigation' and arg.lower() in ('', 'list', 'menu'):
            self.open_case_selector()
            return
        if cmd in ('/exit', '/quit'):
            self.action_exit_app()
            return

        if cmd == '/clear':
            await self._clear_display()
            await self.transcript.mount(Static(self._build_welcome_group(), id='welcome-banner'), before=self.dialogue)
            if self._current_ai_task is None:
                self.dialogue.display = False
                self.transcript.scroll_home(animate=False)
            return

        if cmd == '/settings':
            if arg:
                if arg.lower() in ('model', 'models'):
                    self.open_model_selector()
                    return
                self.handle_settings(arg)
            else:
                self.open_settings()
            self.update_status()
            return

        if cmd == '/ai':
            if not arg:
                self.open_ai_selector()
                return
            if arg.lower() in ('model', 'models'):
                self.open_model_selector()
                return
            if arg.lower() == 'config':
                self.open_settings()
                self.update_status()
                return
            self.handle_ai(arg)
            return

        if cmd == '/theme':
            if not arg:
                self.open_theme_selector()
            else:
                key = arg.strip().lower()
                keys = list(THEMES)
                if key.isdigit() and 1 <= int(key) <= len(keys):
                    key = keys[int(key) - 1]
                if key not in THEMES:
                    self._print_system('Palette inconnue. Tapez /theme pour choisir une palette.')
                    return
                self._apply_theme(THEMES[key])
                save_theme_preference(key)
                self._print_system(Text.assemble(('✓ Palette activée : ', 'bold green'), THEMES[key].label))
            return

        if cmd in ('/pseudo', '/domaine', '/email', '/archive', '/photo', '/prepare', '/tools', '/methods', '/investigation', '/scenario', '/target'):
            self._start_background(self._run_approved_command_async(cmd, arg), "Commande")
            return

        if cmd == '/team':
            if arg and arg.lower() not in ('list', 'liste', 'menu'):
                team = get_team(arg)
                if team:
                    self._start_background(self._activate_team(team.slug), "Changement de pôle")
                else:
                    self._print_system(f"Pôle inconnu '{arg}'. Tapez /team pour la liste.")
                self.update_status()
            else:
                self.open_team_selector()
            return

        if cmd == '/models':
            self.open_model_selector()
            return

        renderable = None
        with self.repl.console.capture() as capture:
            if cmd == '/help':
                self.repl.handle_help()
            elif cmd == '/tools':
                self.repl.handle_tools(arg)
            elif cmd == '/status':
                self.repl.handle_status()
            elif cmd == '/investigation':
                self.repl.handle_case(arg)
            elif cmd == '/indicator':
                renderable = self.repl.handle_indicator(arg)
            elif cmd == '/target':
                self.repl.handle_target(arg)
            elif cmd == '/audit':
                self.repl.handle_audit(arg)
            elif cmd == '/details':
                self.repl.transcript.details(arg)
            elif cmd == '/scenario':
                self.repl.handle_scenario(arg)
            elif cmd == '/models':
                self.repl.handle_models()
            elif cmd == '/context':
                self.repl.handle_context(arg)
            elif cmd == '/history':
                self.repl.handle_history()
            elif cmd == '/usage':
                self.repl.handle_usage()
            elif cmd == '/report':
                self.repl.handle_report(arg)
            elif cmd == '/methods':
                self.repl.handle_methods(arg)
            elif cmd == '/search':
                self.repl.handle_search(arg)
            elif cmd == '/analyze':
                renderable = self.repl.handle_analyze(arg)
            elif cmd == '/reset':
                if self.repl.session:
                    self.repl.session.reset()
                self._saved_session = self._pending_restore = None
                self.repl.console.print(f"[bold {self.ui_theme.success}]✓ Contexte de conversation réinitialisé.[/bold {self.ui_theme.success}]\n")
            else:
                self.repl.console.print(f"Commande '{cmd}' non reconnue. Tapez /help pour la liste.")

        self._sync_from_repl()
        self.update_status()

        output = capture.get().strip()
        if renderable is not None:
            self._print_system(renderable)
        elif output:
            self._print_system(Text.from_ansi(output))

    async def _shell_turn(self, command):
        from free_shell import execute_shell
        if self._current_ai_task is not None:
            self._print_system('Interrompez la génération avant d’ouvrir le terminal.')
            return
        with self.repl.console.capture() as capture:
            directory = self.repl.shell_directory()
        if directory is None:
            self._print_system(Text.from_ansi(capture.get()))
            return
        if command is not None and not command.strip():
            self._print_system('Usage : ! commande Bash ; /terminal ouvre une session interactive.')
            return
        approved = await self._request_approval(self.repl.shell_question(command), {
            'command': command or '/bin/bash -i',
            'details': 'Shell libre, droits de votre utilisateur, réseau et modifications possibles. '
                       'Répertoire : '+str(directory / 'workspace')+'. exit pour revenir.',
        })
        if not approved:
            return
        # Native terminal ownership is essential for sudo, editors and full-screen tools.
        with self.suspend():
            result = execute_shell(command, directory)
        with self.repl.console.capture() as capture:
            self.repl.finish_shell(result)
        self._print_system(Text.from_ansi(capture.get()))

    def action_toggle_native_selection(self):
        """Bascule vers la sélection du terminal, indépendante du clipboard distant."""
        self._native_selection = not self._native_selection
        driver = self._driver
        if isinstance(driver, ResponsiveLinuxDriver):
            driver.set_native_selection(self._native_selection)
        self.screen.clear_selection()
        self.update_status()
        if self._native_selection:
            self.notify('Sélection terminal : glissez sur le texte puis Ctrl+Maj+C. '
                        'F7 réactive les clics et la molette de l’application.', timeout=8)
        else:
            self.notify('Souris de l’application réactivée : menus et défilement.')

    def copy_to_clipboard(self, text):
        super().copy_to_clipboard(text)
        # Copie explicite seulement : la sélection native reste gérée par le
        # terminal ; le repli graphique sert F6 et /copy sous qterminal.
        from focus_clipboard import copy_text
        copy_text(text)

    def action_copy_response(self):
        selected = self.screen.get_selected_text()
        if selected:
            self.copy_to_clipboard(selected)
            return
        answers = list(self.query(StreamingAnswer))
        text = next((answer.text for answer in reversed(answers) if answer.text), '')
        if not text and self.repl.transcript.records:
            text = self.repl.transcript.records[-1].output
        if text:
            self.copy_to_clipboard(text)
            self.notify('Copie demandée. Collez avec Ctrl+Maj+V. '
                        'La sélection du terminal permet aussi Ctrl+Maj+C.', timeout=8)
        else:
            self.notify('Aucune réponse ou sortie à copier.')

    def _run_approved_command(self, command: str, argument: str) -> str | Panel:
        """Exécute les handlers synchrones dans un worker ; l'approbation revient à Textual."""
        with self.repl.console.capture() as capture:
            allowed = self.repl._command_allowed(command, self.active_team_name)
        if not allowed:
            return capture.get().strip()
        renderable = None
        with self.repl.console.capture() as capture:
            if command == '/prepare':
                self.repl.handle_prepare(argument)
            elif command == '/tools':
                self.repl.handle_tools(argument)
            elif command == '/methods':
                self.repl.handle_methods(argument)
            elif command == '/investigation':
                renderable = self.repl.handle_case(argument)
            elif command == '/scenario':
                self.repl.handle_scenario(argument)
            elif command == '/target':
                self.repl.handle_target(argument)
            else:
                self.repl.handle_quick(command, argument)
        # Un panneau déjà rendu en ANSI se replie dans la zone de dialogue,
        # plus étroite que le terminal. Garder l'objet pour le layout et resize.
        return renderable if isinstance(renderable, Panel) else capture.get().strip()

    async def _activate_team(self, slug: str) -> None:
        if slug in ("assist", "assistant", "0"):
            self.repl.handle_team("assist")
            self.active_team_name = "Assist"
            self._render_input_mode()
            self.session = self.repl.session
            self.update_status()
            self._print_system("[bold green]✓ Mode activé :[/] Assist (Assistant d'investigation générale)")
            return

        team = get_team(slug)
        if team is None:
            return

        def activate_and_capture() -> str:
            with self.repl.console.capture() as capture:
                self.repl.handle_team(team.slug)
            return capture.get().strip()
        output = await asyncio.to_thread(activate_and_capture)
        self.active_team_name = team.name
        self._render_input_mode()
        self.session = self.repl.session
        self.update_status()
        if output:
            self._print_system(Text.from_ansi(output))
        if not team.available:
            self._print_system(Panel(Text(team.development_notice),
                                     title=f"{team.name} · En développement",
                                     border_style=team.color, box=box.ROUNDED))
        else:
            self._print_system(f"[bold green]✓ Pôle activé :[/] {team.name} ({team.tools_hint})")

    def _start_background(self, task: Any, label: str) -> None:
        if self._command_busy:
            if hasattr(task, 'close'):
                task.close()
            self._print_system("Une commande est déjà en cours.")
            return
        self._command_busy = True
        self.run_worker(self._finish_background(task, label), group="uchambuzi-command",
                        exclusive=False, exit_on_error=False)

    async def _finish_background(self, task: Any, label: str) -> None:
        try:
            await task
        except Exception as exc:
            self._print_system(f"{label} : {safe_display(exc)}")
        finally:
            self._command_busy = False
            self.update_status()

    async def _run_approved_command_async(self, command: str, argument: str) -> None:
        action = argument.split(maxsplit=1)[0].lower() if argument.strip() else ''
        case_action = command == '/investigation' and action in ('open', 'create', 'close', 'archive', 'delete')
        if case_action and self._conversation_busy():
            self._print_system('Terminez ou interrompez la génération avant de changer de dossier.')
            return
        old_case = self.case_manager.active_case_id
        old_state = self.case_manager.state
        output = await asyncio.to_thread(self._run_approved_command, command, argument)
        self.session = self.repl.session
        changed = case_action and (self.case_manager.active_case_id != old_case or
                                   (action in ('open', 'create') and self.case_manager.state is not old_state))
        if changed:
            self._saved_session = None
            self._pending_restore = None
            await self._clear_display()
            self.prompt_input.prompt_history.clear()
            self.prompt_input.remember('')
        if output:
            self._print_system(Text.from_ansi(output) if isinstance(output, str) else output)
        if changed and action in ('open', 'create') and self.case_manager.active_case_id:
            self.call_after_refresh(self._choose_conversation)

    def _legal_panel_from_worker(self, message: str) -> None:
        """Monte le Panel natif avant que le worker ne demande l'approbation."""
        self._emit_system(Panel(Text(message, style="#E2E8F0"), title="Cadre légal OSINT",
                                border_style="#38BDF8", box=box.ROUNDED))

    def _confirm_from_worker(self, question: str, **details: Any) -> bool:
        """Demande un oui explicite via le prompt Textual, avec refus par défaut."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return False
        if getattr(self, '_thread_id', None) == threading.get_ident():
            return False
        try:
            return bool(asyncio.run_coroutine_threadsafe(
                self._request_approval(question, details), loop
            ).result())
        except (RuntimeError, asyncio.CancelledError, concurrent.futures.CancelledError):
            return False

    async def _request_approval(self, question: str, details: dict[str, Any]) -> bool:
        if self._pending_approval is not None:
            return False
        if details.get('command'):
            self._last_prepared_command = str(details['command'])
        future = asyncio.get_running_loop().create_future()
        def resolve(decision: bool) -> None:
            if not future.done():
                future.set_result(decision)
        self._pending_approval = {"resolve": resolve}
        content = Text()
        if details.get("tool"):
            content.append(f"Outil : {details['tool']}\n", style="bold #38BDF8")
        if details.get("command"):
            content.append(f"Commande : {details['command']}\n", style="#E2E8F0")
        if details.get("details"):
            content.append(f"Précautions : {details['details']}\n", style="#94A3B8")
        content.append(question + "\n\n", style="bold #E2E8F0")
        content.append("Choisissez une réponse dans la fenêtre de confirmation.", style="#94A3B8")
        self._print_system(Panel(content, title=Text("Approbation [o/N]"), border_style="#E85D26", box=box.ROUNDED))
        modal = ApprovalModal(question, details)
        self.push_screen(modal, callback=lambda decision: resolve(decision is True))
        try:
            approved = bool(await future)
            self._print_system("Autorisation accordée pour cette opération." if approved
                               else "Opération refusée par l'enquêteur.")
            return approved
        finally:
            self._pending_approval = None
            if modal.is_mounted and self.screen is modal:
                self.pop_screen()
            if self.is_running:
                self.prompt_input.focus()

    async def _request_ai_approval(self, query, session, context, instructions):
        """Présente tout le contenu préparé et lie l'accord à son empreinte."""
        preview = None
        try:
            preview = session.preview_external(query, context, system_instructions=instructions)
            if 'payload' not in preview:
                raise RuntimeError('Aperçu complet indisponible.')
            shown = {key: preview.get(key) for key in ('destination', 'port', 'model', 'payload')}
            body = format_approval_preview(shown)
            if getattr(session.runtime, 'model_family', '') == 'anthropic':
                body += '\nClaude Code peut ajouter des métadonnées propres à son client.'
            if isinstance(session.runtime, OllamaRuntime):
                body += '\nAttention : connexion Ollama distante en HTTP non chiffré.'
        except (ValueError, TypeError, RuntimeError, RuntimeErrorLocal) as exc:
            if preview is not None and 'fingerprint' in preview:
                session.cancel_external_approval(preview['fingerprint'])
            self._print_system(Text('Aucun envoi : ' + safe_display(exc)))
            return
        approved = False
        try:
            approved = await self._request_approval('Autoriser cet envoi distant ?',
                                                    {'details': 'Contenu préparé :\n' + body})
        finally:
            if not approved:
                session.cancel_external_approval(preview['fingerprint'])
        if not approved:
            return
        if self.repl.session is not session:
            session.cancel_external_approval(preview['fingerprint'])
            self._print_system('Session modifiée ; aucun envoi.')
            return
        await self._dispatch_ai(query, _prepared=(session, context, instructions, preview['fingerprint']))

    def on_unmount(self) -> None:
        self._restore_terminal_title()
        self._restore_terminal_palette()
        self._interrupt_ai(announce=False)
        self.repl._operation_cancel.set()
        pending = self._pending_approval
        if pending is not None:
            pending["resolve"](False)
            self._pending_approval = None

    async def _dispatch_ai(self, query: str, *, _prepared=None) -> None:
        """Gère une question en langage naturel ou un indice via le moteur IA."""
        if not self._routing_allowed():
            return

        import indices_outils
        raw_kind = indices_outils.detect_indice_type(query)
        quick_command = {'username': '/pseudo', 'domain': '/domaine', 'email': '/email',
                         'url': '/archive', 'image': '/photo'}.get(raw_kind)
        if self.repl._osint_enabled(self.active_team_name) and quick_command:
            self._start_background(self._run_approved_command_async(quick_command, query), "Commande OSINT")
            return

        # S'assurer que la session IA est initialisée
        active_session = self.repl.session
        self._restore_waiting()
        if not active_session:
            self._print_system(
                "[bold yellow]◈ Moteur IA désactivé.[/] "
                "Tapez [bold white]/ai[/] pour choisir et réactiver le modèle, "
                "ou [bold white]/team 1[/] pour investiguer avec l’OSINT Team."
            )
            return

        if self._current_ai_task is not None:
            self._print_system("Une génération est déjà en cours.")
            return
        if self._ai_worker_finished is not None and not self._ai_worker_finished.is_set():
            self._print_system("Le transport interrompu se ferme. Réessayez dans un instant.")
            return

        if _prepared is None:
            try:
                context, instructions = self.repl._prepare_ai_context(query, self.active_team_name)
                from focus_repl import evidence_scope_notice
                notice = evidence_scope_notice(context)
                if notice:
                    self._print_system(Text(notice))
            except (ValueError, TypeError, RuntimeError, RuntimeErrorLocal) as exc:
                self._print_system(Text('Aucun envoi : ' + safe_display(exc)))
                return
            if active_session._requires_external_consent():
                self._start_background(self._request_ai_approval(query, active_session, context, instructions),
                                       'Approbation du fournisseur IA')
                return
            approval = None
        else:
            approved_session, context, instructions, approval = _prepared
            if active_session is not approved_session:
                self._print_system('Session modifiée ; aucun envoi.')
                return

        from focus_tool_registry import osint_availability_notice
        availability = osint_availability_notice(context)
        if availability:
            self._print_system(Text(availability))
        pending_save = self._persist_start(query)
        self.dialogue.display = True
        thinking = ThinkingIndicator(model_name=getattr(self.adapter, 'model', 'Ollama'))
        answer = self._active_answer = StreamingAnswer()
        self._active_thinking = thinking
        await self.dialogue.mount(thinking, answer)
        self.transcript.scroll_end(animate=False)

        cancellation = self._ai_cancellation = TurnCancellation()

        def receive(text: str, *, reasoning: bool = False) -> None:
            # Les callbacks réseau tardifs ne doivent jamais modifier un autre tour.
            if self._ai_cancellation is not cancellation:
                return
            try:
                cancellation.check()
            except RuntimeCancelled:
                return
            if reasoning:
                thinking.append_thinking(text)
            else:
                if not thinking.complete:
                    thinking.finish()
                answer.append_text(text)
            self.transcript.follow_end()
            self.update_status()

        def on_chunk(text: str) -> None:
            self._loop.call_soon_threadsafe(receive, text)

        def on_thinking(text: str) -> None:
            from functools import partial
            self._loop.call_soon_threadsafe(partial(receive, text, reasoning=True))

        def do_query():
            return active_session.respond(query, context=context, system_instructions=instructions,
                                          cancellation=cancellation, on_chunk=on_chunk,
                                          on_thinking=on_thinking, approval=approval)

        finished = self._ai_worker_finished = threading.Event()

        def network_query():
            try:
                return True, do_query()
            except Exception as exc:
                # Python 3.14 signale les exceptions d'un Future shieldé même
                # après annulation : transmettre le résultat sans lever ici.
                return False, exc
            finally:
                finished.set()

        # Annuler la tâche UI ne doit pas annuler le suivi du thread réseau.
        # Le marqueur empêche le chevauchement de deux tours sur une même Session.
        network = self._loop.run_in_executor(None, network_query)

        async def wait_network():
            success, result = await asyncio.shield(network)
            if not success:
                raise result
            return result

        task = self._current_ai_task = asyncio.create_task(wait_network())
        self.run_worker(self._show_ai_result(task, thinking, answer, pending_save), exit_on_error=False)

    async def _show_ai_result(self, task: asyncio.Task, thinking: ThinkingIndicator, answer: StreamingAnswer, pending_save=None) -> None:
        save_state = 'failed'
        try:
            response = await asyncio.shield(task)
            save_state = 'complete'
            # Le retour validé fait foi, y compris pour les adaptateurs sans streaming.
            answer.text = response
            answer._dirty = True
            answer.flush()
        except asyncio.CancelledError:
            save_state = 'cancelled'
            self._interrupt_ai(announce=False)
        except Exception as exc:
            self._print_system(f"Erreur IA : {safe_display(exc)}")
        finally:
            self._persist_finish(pending_save, answer.text, save_state)
            if thinking.reasoning_text:
                thinking.finish()
            else:
                await thinking.remove()
            answer.finish()
            self.update_status()
            if not answer.text:
                await answer.remove()
            if self._current_ai_task is task:
                self._current_ai_task = None
                self._ai_cancellation = None
                self._active_answer = self._active_thinking = None


def run_textual_app(
    *,
    model: str | None = None,
    port: int = 11434,
    timeout: float = DEFAULT_TIMEOUT,
    runtime: Any = None,
    context_budget: int = DEFAULT_CONTEXT_BUDGET,
    case_id: str | None = None,
    theme_id: str | None = None,
) -> int:
    """Lance l'application TUI réactive 2D Textual."""
    app = UchambuziApp(
        model=model,
        port=port,
        timeout=timeout,
        runtime=runtime,
        context_budget=context_budget,
        case_id=case_id,
        theme_id=theme_id,
    )
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(run_textual_app())
