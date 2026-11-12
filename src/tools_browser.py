# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : tools_browser.py
# Role          : Catalogue interactif OSINT avec fiches et actions explicites
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Browse verified capabilities; opening a card never starts an investigation."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, Select, Static
from textual.widgets.option_list import Option

from tool_guidance import OBJECTIVES, guide_for
from tools_catalog import discover_tools, load_catalog


@dataclass(frozen=True)
class ToolBrowserChoice:
    action: str
    tool_id: str = ''
    target: str = ''


class ToolsBrowserModal(ModalScreen[ToolBrowserChoice | None]):
    """A task-oriented catalogue whose actions return to the owning REPL."""

    DEFAULT_CSS = """
    ToolsBrowserModal { align: center middle; background: rgba(13, 27, 42, 0.75); }
    #tools-browser { width: 95%; height: 95%; border: round #38BDF8; padding: 0 1; }
    #tools-browser-title { height: 1; text-style: bold; }
    #tools-objective { height: 3; margin: 0; }
    #tools-body { height: 1fr; min-height: 3; }
    #tools-list { width: 1fr; height: 100%; margin-right: 1; }
    #tools-card-scroll { width: 2fr; height: 100%; }
    #tools-card { height: auto; }
    #tools-target { height: 3; margin: 0; }
    #tools-actions { height: 3; }
    #tools-actions Button { width: 1fr; min-width: 8; margin: 0; padding: 0; }
    #tools-browser-footer { height: 1; }
    """
    BINDINGS = [Binding('escape', 'cancel', 'Fermer', show=False)]

    def __init__(self, query: str = '', **kwargs):
        super().__init__(**kwargs)
        self.initial_query = query.strip().casefold()
        self.tools = list(load_catalog())
        self.states = {}
        self.selected_tool_id = next((row['id'] for row in self.tools
                                      if self.initial_query in (row['id'], row['name'].casefold())), '')
        self.objective = self.initial_query if any(row['id'] == self.initial_query for row in OBJECTIVES) else 'all'
        self.visible_tools = []
        self._loading = True
        self._load_error = ''
        self._showing_help = False

    def compose(self) -> ComposeResult:
        with Vertical(id='tools-browser'):
            yield Static('Outils OSINT — choisir selon l’objectif', id='tools-browser-title')
            yield Select([('Tous les objectifs', 'all')] + [(row['title'], row['id']) for row in OBJECTIVES],
                         value=self.objective, allow_blank=False, id='tools-objective')
            with Horizontal(id='tools-body'):
                yield OptionList(id='tools-list')
                with VerticalScroll(id='tools-card-scroll'):
                    yield Static('', markup=False, id='tools-card')
            yield Input(placeholder='Choisir un outil pour renseigner sa cible', id='tools-target')
            with Horizontal(id='tools-actions'):
                yield Button('Préparer', id='tools-prepare', disabled=True)
                yield Button('Shell', id='tools-shell', disabled=True)
                yield Button('Aide', id='tools-help')
                yield Button('Installer', id='tools-install', disabled=True)
                yield Button('Vérifier', id='tools-verify', disabled=True)
                yield Button('Retour', id='tools-back')
            yield Static('↑↓ outil · Tab naviguer · Entrée choisir · Échap fermer', id='tools-browser-footer')

    def on_mount(self):
        theme = getattr(self.app, 'ui_theme', None)
        if theme is not None:
            self.query_one('#tools-browser').styles.background = theme.app_bg
            self.query_one('#tools-browser').styles.border = ('round', theme.secondary)
            self.query_one('#tools-card').styles.color = theme.text_main
            self.query_one('#tools-browser-title').styles.color = theme.primary
            self.query_one('#tools-browser-footer').styles.color = theme.text_dim
        self._refresh_tools()
        self.query_one('#tools-list', OptionList).focus()
        self.run_worker(self._load_states(), group='tools-browser-discovery', exclusive=True)

    async def _load_states(self):
        try:
            states = await asyncio.to_thread(discover_tools, self.tools)
        except (ValueError, OSError) as exc:
            self._load_error = str(exc)
            states = {}
        if not self.is_mounted:
            return
        self.states = states
        self._loading = False
        self._refresh_tools()

    def _tool(self):
        return next((row for row in self.tools if row['id'] == self.selected_tool_id), None)

    def _ready(self, tool):
        state = self.states.get(tool['id'])
        return bool(state and state.state == 'installed')

    def _status(self, tool):
        if tool['source'] == 'vendored' and not tool.get('artifact'):
            return 'indisponible — copie vérifiée absente'
        if self._loading:
            return 'vérification en cours'
        state = self.states.get(tool['id'])
        if self._ready(tool):
            return 'prêt'
        if tool['source'] == 'vendored' and tool.get('artifact'):
            return 'à installer ou à réparer'
        if state and state.state == 'missing_dependency':
            return 'dépendance manquante'
        return 'outil système absent ou non vérifié'

    def _refresh_tools(self):
        self.visible_tools = [row for row in self.tools
                              if self.objective == 'all' or self.objective in row['specialties']]
        options = self.query_one('#tools-list', OptionList)
        options.clear_options()
        for row in self.visible_tools:
            title = Text(row['name'], style='bold')
            title.append('\n' + self._status(row), style='dim')
            options.add_option(Option(title, id=row['id']))
        index = next((i for i, row in enumerate(self.visible_tools)
                      if row['id'] == self.selected_tool_id), 0)
        if self.visible_tools:
            self.selected_tool_id = self.visible_tools[index]['id']
            options.highlighted = index
        else:
            self.selected_tool_id = ''
        self._render_card()

    def _render_card(self):
        tool = self._tool()
        if not tool:
            self.query_one('#tools-card', Static).update('Aucun outil pour cet objectif.')
            return
        guide = guide_for(tool['id'])
        state = self.states.get(tool['id'])
        activity = 'actif' if tool['activity'] == 'active' else 'passif'
        lines = [tool['name'], '', 'À quoi sert-il ?', guide['purpose'], '',
                 'Pourquoi le choisir ?', guide['why'], '',
                 'Ce qu’il faut fournir', guide['input_label'], '',
                 'Ce que tu obtiendras', guide['outputs'], '',
                 'Limites', guide['limits'], '',
                 'Disponibilité : ' + self._status(tool),
                 'Version : ' + (getattr(state, 'version', None) or tool.get('version_pin') or 'non vérifiée'),
                 'Réseau : ' + ('nécessaire' if tool['needs_network'] else 'non requis'),
                 'Niveau du catalogue : ' + activity,
                 'Action individuelle depuis cette fiche : ' + ('disponible — exécution limitée à 30 s' if guide.get('guided') else 'non proposée ; consulter les parcours indiqués dans l’aide'),
                 '', 'Exemple de syntaxe native', guide['example'],
                 '', 'Options et documentation', guide['help_hint']]
        if tool['source'] == 'vendored' and tool.get('artifact') and not self._loading and not self._ready(tool):
            lines += ['', 'Si une version existe mais sa vérification échoue :',
                      '/tools remove '+tool['id']+' puis /tools install '+tool['id']+
                      ' (deux approbations séparées). Aucun remplacement automatique.']
        if self._load_error:
            lines += ['', 'Découverte locale incomplète : ' + self._load_error]
        if state and state.diagnostic:
            lines += ['', 'Diagnostic : ' + state.diagnostic]
        if self._showing_help:
            lines += ['', 'Référence locale', self._local_help(tool)]
        self.query_one('#tools-card', Static).update('\n'.join(lines))
        example = guide.get('input_example', '')
        target = self.query_one('#tools-target', Input)
        target.disabled = not guide.get('guided', False)
        target.placeholder = (guide['input_label'] + (' · ex. ' + example if example else '')
                              if guide.get('guided') else 'Autres options : consulter l’aide puis modifier la commande dans le shell')
        self._refresh_actions()

    def _local_help(self, tool):
        root = Path(__file__).resolve().parents[1] / 'data/documentation'
        for name in (tool['id'] + '.md', tool['id'] + '-kali.md'):
            source = root / name
            if source.is_file() and not source.is_symlink():
                return source.read_text(encoding='utf-8', errors='replace')[:16000]
        return 'Pas de fiche locale détaillée. Utiliser le shell avec --help après vérification de l’exécutable.'

    def _refresh_actions(self):
        tool = self._tool()
        if not tool:
            return
        ready = self._ready(tool)
        guided = guide_for(tool['id']).get('guided', False)
        target = self.query_one('#tools-target', Input).value.strip()
        self.query_one('#tools-prepare', Button).disabled = not (ready and guided and target)
        self.query_one('#tools-shell', Button).disabled = not (ready and tool['source'] != 'builtin')
        self.query_one('#tools-install', Button).disabled = not (
            tool['source'] == 'vendored' and tool.get('artifact') and not ready and not self._loading)
        self.query_one('#tools-verify', Button).disabled = not (
            tool['source'] == 'vendored' and tool.get('artifact') and not self._loading)

    @on(Select.Changed, '#tools-objective')
    def objective_changed(self, event):
        if event.value is Select.BLANK:
            return
        self.objective = str(event.value)
        self._showing_help = False
        self._refresh_tools()

    @on(OptionList.OptionHighlighted, '#tools-list')
    def tool_highlighted(self, event):
        visible = {row['id'] for row in self.visible_tools}
        if event.option.id in visible and event.option.id != self.selected_tool_id:
            self.selected_tool_id = event.option.id
            self._showing_help = False
            self.query_one('#tools-target', Input).value = ''
            self._render_card()

    @on(OptionList.OptionSelected, '#tools-list')
    def tool_selected(self, event):
        self.selected_tool_id = event.option.id
        self._render_card()
        self.query_one('#tools-card-scroll').scroll_home(animate=False)
        if not self.query_one('#tools-target', Input).disabled:
            self.query_one('#tools-target', Input).focus()

    @on(Input.Changed, '#tools-target')
    def target_changed(self):
        self._refresh_actions()

    @on(Input.Submitted, '#tools-target')
    def target_submitted(self):
        if not self.query_one('#tools-prepare', Button).disabled:
            self._choose('prepare')

    @on(Button.Pressed)
    def button_pressed(self, event):
        action = (event.button.id or '').removeprefix('tools-')
        if action == 'back':
            self.action_cancel()
        elif action == 'help':
            self._showing_help = True
            self._render_card()
            self.query_one('#tools-card-scroll').scroll_end(animate=False)
        elif action in ('prepare', 'shell', 'install', 'verify') and not event.button.disabled:
            self._choose(action)

    def _choose(self, action):
        self.dismiss(ToolBrowserChoice(action, self.selected_tool_id,
                                      self.query_one('#tools-target', Input).value))

    def action_cancel(self):
        self.dismiss(None)
