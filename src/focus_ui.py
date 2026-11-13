# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_ui.py
# Role          : Moteur TUI conversationnel Focus, etats, disposition et extensions
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Moteur TUI conversationnel UCHAMBUZI Focus ; points de raccordement pour missions 03, 04 et 05."""
from __future__ import annotations

import parcours
import asyncio
from dataclasses import dataclass, field
from enum import Enum
import os
import secrets
import select
import shutil
import sys
import time
import unicodedata
from typing import Callable, Protocol, Sequence

from conversation import (
    DEFAULT_CONTEXT_BUDGET,
    DEFAULT_TIMEOUT,
    OllamaRuntime,
    RuntimeErrorLocal,
    RuntimeIncomplete,
    Session,
    safe_display,
)
from focus_contracts import (
    Catalog,
    ConfirmationDecision,
    ConfirmationRequest,
    ConfirmationService,
    ConversationEngine,
    Message,
    Model,
    Profile,
    Role,
    Scenario,
    SessionSnapshot,
    SessionStore,
    Settings,
    TextDelta,
    ToolRequest,
    ToolResult,
    TurnFinished,
    TurnStarted,
    TurnState,
    approved_for,
)
from focus_legacy_adapter import LegacyConversation
from focus_view import ConversationRenderer, graphemes, cluster_width
from focus_branding import BrandLogo, terminal_options
from focus_editor import FocusEditor
from focus_assembly import ToolUI
from focus_settings_catalog import InteractiveCatalog
from focus_terminal_keys import TerminalKeys


def journal_description(entry):
    """Présente le résumé enregistré sans exposer les types techniques."""
    summary = str(entry.get('summary', ''))
    if entry.get('event_type') == 'conversation_snapshot':
        summary = 'Conversation enregistrée.'
    elif entry.get('event_type') == 'command_prepared':
        translations = {'Préparation enregistrée (prepared).': 'Préparation enregistrée (commande prête).',
                        'Préparation enregistrée (refused).': 'Préparation enregistrée (commande refusée).'}
        summary = translations.get(summary, summary)
    elif entry.get('event_type') == 'security_audit':
        for suffix, replacement in ((' (injection=True).', ' (motif suspect détecté).'),
                                    (' (injection=False).', ' (aucun motif suspect détecté).')):
            if summary.startswith('Audit anti-injection sur ') and summary.endswith(suffix):
                summary = summary[:-len(suffix)] + replacement
                break
    return safe_display(summary)


def audit_description(report):
    result = 'Motifs suspects détectés' if report['injection_detected'] else 'Aucun motif suspect détecté'
    extent = 'lecture partielle' if report['truncated'] else 'lecture complète'
    labels = {'override_instruction': 'tentative de remplacement des consignes',
              'role_delimiter': 'délimiteur de rôle', 'fake_execution': 'fausse exécution',
              'forced_conclusion': 'conclusion imposée', 'jailbreak_persona': 'contournement des restrictions',
              'bidi_or_format_control': 'caractère de contrôle de direction'}
    patterns = ', '.join(labels.get(code, 'autre motif suspect') for code in report['detected_patterns']) or 'aucun'
    return (f"Fichier : {safe_display(report['path'])}\n"
            f"Analyse heuristique anti-injection : {result}.\n"
            f"Motifs relevés : {patterns}\n"
            f"Contenu examiné : {report['bytes_inspected']} octets ({extent}).\n"
            "La détection recherche des motifs connus ; elle ne garantit pas l’absence d’injection.")


def render_preparation_readable(result):
    """Affiche la commande et ses avertissements sans les métadonnées internes."""
    command = result.get('command', result)
    if command.get('status') != 'prepared':
        error = command.get('error') or {}
        print(safe_display('Préparation refusée : ' + str(error.get('message', 'raison indisponible'))))
        return
    print(safe_display('Commande préparée : ' + str(command.get('display', ''))))
    operation = {'local': 'locale', 'active': 'active', 'passive': 'passive'}.get(command.get('operation_type'), command.get('operation_type', ''))
    risk = {'moderate': 'modéré', 'low': 'faible', 'high': 'élevé'}.get(command.get('risk'), command.get('risk', ''))
    print(safe_display(f"Opération : {operation} ; risque : {risk} ; réseau requis : {'oui' if command.get('network_required') else 'non'}"))
    recommendation = result.get('recommendation') or {}
    for key, label in [('safety', 'Précaution'), ('restrictions', 'Restriction'), ('uncertainties', 'Incertitude')]:
        for value in recommendation.get(key, []):
            print(safe_display(f'{label} : {value}'))
    for item in command.get('parameter_explanations', []):
        print(safe_display(f"  {item['argument']} : {item['explanation']}"))
    for label, key in [('Prérequis', 'prerequisites'), ('Limite', 'limitations')]:
        for value in command.get(key, []):
            value = value.replace(' ; aucune garantie de chaîne de conservation', '').replace('; aucune garantie de chaîne de conservation', '')
            print(safe_display(f'{label} : {value}'))
    print('Approbation humaine requise avant toute exécution.')


class UIState(str, Enum):
    """États explicites de la machine d'état du moteur TUI Focus."""
    WELCOME = 'welcome'
    CONVERSATION = 'conversation'
    RUNNING = 'running'
    CONFIRMATION = 'confirmation'
    ERROR = 'error'
    MODE_SWITCH = 'mode_switch'
    CLOSING = 'closing'


MIN_TERMINAL_WIDTH = 28
MIN_TERMINAL_HEIGHT = 10
COMPACT_TERMINAL_WIDTH = 64
COMPACT_TERMINAL_HEIGHT = 16
SPLIT_VIEW_MIN_WIDTH = 120
SPLIT_VIEW_MIN_HEIGHT = 18
MIN_STREAM_RENDER_INTERVAL = 1.0 / 30.0  # Budget <= 30 rendus/s (~33.3 ms) en streaming
MAX_TRANSCRIPT_ENTRIES = 500             # Bornage mémoire documenté par région


# ============================================================================
# Points de raccordement (extensions propres pour les missions 03, 04 et 05)
# ============================================================================

class EditorExtension(Protocol):
    """Point de raccordement pour l'éditeur de saisie (Mission 03)."""
    @property
    def buffer(self) -> str: ...
    @property
    def cursor(self) -> int: ...
    @property
    def history(self) -> Sequence[str]: ...
    def set_text(self, value: str) -> None: ...
    def handle_key(self, key: int | str) -> str | None: ...
    def render_lines(self, width: int, *, active: bool = True) -> Sequence[str]: ...
    def clear(self) -> None: ...


class MarkdownRendererExtension(Protocol):
    """Point de raccordement pour le rendu Markdown et conversationnel (Mission 04)."""
    def render_message(self, message: Message, width: int, *, streaming: bool = False) -> Sequence[str]: ...
    def render_panel(self, title: str, content: str, width: int) -> Sequence[str]: ...


class BrandLogoExtension(Protocol):
    """Point de raccordement pour le logo et l'identité visuelle (Mission 04)."""
    def render_logo(self, width: int, height: int) -> Sequence[str]: ...


class ModelProviderExtension(Protocol):
    """Point de raccordement pour les modèles IA et le moteur de streaming (Mission 05)."""
    def list_models(self) -> Sequence[Model]: ...
    def create_engine(self, model: Model | None, profile: Profile, scenario: Scenario | None,
                      *, timeout: float = DEFAULT_TIMEOUT,
                      context_budget: int = DEFAULT_CONTEXT_BUDGET) -> ConversationEngine | None: ...


class SelectorExtension(Protocol):
    """Point de raccordement pour les sélecteurs modaux (modes, scénarios, modèles)."""
    def render_selector(self, title: str, items: Sequence[tuple[str, str, str]],
                        selected_index: int, width: int) -> Sequence[str]: ...


# ============================================================================
# Implémentations par défaut autonomes (remplaçables par injection)
# ============================================================================

DEFAULT_PROFILES: tuple[Profile, ...] = (
    Profile('assist', 'Assist', 'Réponds comme assistant généraliste ; clarifie les besoins et distingue faits et hypothèses.'),
    Profile('trace', 'Trace', 'Privilégie intégrité des preuves, chronologie, copies de travail et limites de conservation.'),
    Profile('intel', 'Intel', 'Distingue sources, dates, fiabilité, corrélations et hypothèses ; précise les accès réseau.'),
    Profile('defend', 'Defend', 'Privilégie surveillance, détection, qualification, confinement et reprise.'),
    Profile('assess', 'Assess', 'Précise autorisation, périmètre et limites avant toute évaluation de sécurité.'),
    Profile('validate', 'Validate', 'Relie une technique contrôlée aux signaux de détection et aux résultats mesurés.'),
    Profile('engineer', 'Engineer', 'Privilégie administration sûre, durcissement, changements réversibles et vérification.'),
    Profile('coordinate', 'Coordinate', 'Privilégie gouvernance, coordination, objectifs, rôles et suivi des décisions.'),
)

DEFAULT_SCENARIOS: dict[str, tuple[Scenario, ...]] = {
    'assist': (
        Scenario('troubleshooting', 'Diagnostic progressif', 'Diagnostique progressivement et propose des vérifications réversibles.'),
    ),
    'trace': (
        Scenario('timeline', 'Chronologie forensique', 'Construis une chronologie avec sources, fuseaux et incertitudes.'),
        Scenario('malware', 'Analyse de malwares', 'Analyse les indices de logiciel malveillant dans un environnement isolé.'),
    ),
    'intel': (
        Scenario('indicators', 'Qualification d’indicateurs', 'Qualifie les indicateurs et leur contexte sans présumer une compromission.'),
        Scenario('osint', 'Sources ouvertes', 'Organise la recherche en sources ouvertes et évalue leur provenance.'),
    ),
    'defend': (
        Scenario('incident', 'Réponse à incident', 'Propose un triage et une réponse graduée avec préservation des traces.'),
        Scenario('hunting', 'Chasse aux menaces', 'Formule des hypothèses de chasse et des critères de validation.'),
    ),
    'assess': (
        Scenario('audit', 'Audit de configuration', 'Structure un audit selon le périmètre autorisé et documente les constats.'),
        Scenario('pentest', 'Test d’intrusion autorisé', 'Planifie une évaluation autorisée avec garde-fous et preuve des résultats.'),
    ),
    'validate': (
        Scenario('detection', 'Validation de détection', 'Définis critères de détection, simulation autorisée et collecte de résultats.'),
        Scenario('emulation', 'Émulation contrôlée', 'Prépare une émulation bornée et réversible avec conditions d’arrêt.'),
    ),
    'engineer': (
        Scenario('hardening', 'Durcissement système', 'Évalue le durcissement, les effets de bord et le retour arrière.'),
        Scenario('automation', 'Automatisation sûre', 'Conçois une automatisation vérifiable avec permissions minimales.'),
    ),
    'coordinate': (
        Scenario('exercise', 'Exercice de crise', 'Structure un exercice avec règles, rôles, contrôles et retour d’expérience.'),
        Scenario('governance', 'Gouvernance et risques', 'Documente décisions, responsabilités, risques et actions de suivi.'),
    ),
}


class DefaultCatalog(Catalog):
    """Catalogue par défaut des profils et scénarios Focus."""
    def __init__(self, profiles: Sequence[Profile] = DEFAULT_PROFILES,
                 scenarios_by_profile: dict[str, tuple[Scenario, ...]] | None = None):
        self._profiles = tuple(profiles)
        self._scenarios_by_profile = dict(scenarios_by_profile or DEFAULT_SCENARIOS)

    def profiles(self) -> Sequence[Profile]:
        return self._profiles

    def scenarios(self, profile_id: str | None = None) -> Sequence[Scenario]:
        if profile_id is not None:
            return self._scenarios_by_profile.get(profile_id, ())
        all_scenarios: list[Scenario] = []
        for items in self._scenarios_by_profile.values():
            all_scenarios.extend(items)
        return tuple(all_scenarios)

    def get_profile(self, profile_id: str) -> Profile | None:
        key = profile_id.strip().lower()
        for profile in self._profiles:
            if profile.id == key or profile.name.lower() == key:
                return profile
        return None

    def get_scenario(self, profile_id: str, scenario_id: str) -> Scenario | None:
        key = scenario_id.strip().lower()
        for scenario in self.scenarios(profile_id):
            if scenario.id == key or scenario.title.lower() == key:
                return scenario
        return None


_BIDI_CONTROLS = frozenset('\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')


def terminal_display(text: str) -> str:
    """Neutralise les contrôles terminaux et bidirectionnels sans altérer l'Unicode utile (ZWJ, emojis, accents)."""
    if not isinstance(text, str):
        text = str(text)
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        # Neutralise les séquences d'échappement ANSI/CSI/OSC commençant par ESC (\x1b)
        if ch == '\x1b':
            i += 1
            if i < n and text[i] == '[':
                i += 1
                while i < n and not ('@' <= text[i] <= '~'):
                    i += 1
                if i < n:
                    i += 1
            elif i < n and text[i] == ']':
                i += 1
                while i < n and text[i] not in ('\x07', '\x1b'):
                    i += 1
                if i < n:
                    if text[i] == '\x1b' and i + 1 < n and text[i + 1] == '\\':
                        i += 2
                    else:
                        i += 1
            continue
        if ch in _BIDI_CONTROLS or (unicodedata.category(ch) in ('Cc', 'Cs') and ch not in '\n\t'):
            out.append('')
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


def _char_display_width(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch) or unicodedata.category(ch) in ('Mn', 'Me', 'Cf'):
        return 0
    if unicodedata.east_asian_width(ch) in ('W', 'F'):
        return 2
    codepoint = ord(ch)
    if 0x1F300 <= codepoint <= 0x1FAFF or 0x2600 <= codepoint <= 0x27BF:
        return 2
    return 1


def display_width(text: str) -> int:
    return sum(cluster_width(g) for g in graphemes(terminal_display(text)))


def clip_to_width(text: str, max_cols: int) -> str:
    out, cols = [], 0
    for cluster in graphemes(terminal_display(text).replace('\t', '    ')):
        width = cluster_width(cluster)
        if cols + width > max(0, max_cols):
            break
        out.append(cluster)
        cols += width
    return ''.join(out)


def wrap_line(text: str, width: int) -> list[str]:
    from focus_view import wrap_exact
    return wrap_exact(terminal_display(text), max(1, width))


class DefaultBrandLogo:
    """Rendu adaptatif du logo d'accueil UCHAMBUZI Focus."""
    def render_logo(self, width: int, height: int) -> Sequence[str]:
        if width >= 64 and height >= 16:
            return (
                '          ·──────── ◉ ────────·',
                '            U C H A M B U Z I',
                '     INVESTIGATION NUMÉRIQUE LOCALE',
                '          [ MOTEUR TUI FOCUS ]',
            )
        if width >= 34:
            return (
                '    ·──── ◉ ────·',
                '    U C H A M B U Z I',
                '  Focus — Investigation locale',
            )
        return ('UCHAMBUZI Focus',)


class DefaultMarkdownRenderer:
    """Rendu structuré des messages et blocs Markdown sans exécution de séquences terminales."""
    ROLE_LABELS = {
        Role.USER: 'Enquêteur',
        Role.ASSISTANT: 'UCHAMBUZI',
    }

    def render_message(self, message: Message, width: int, *, streaming: bool = False) -> Sequence[str]:
        inner = max(8, width - 2)
        label = self.ROLE_LABELS.get(message.role, str(message.role))
        prefix = '› ' if message.role == Role.USER else '◆ '
        suffix = ' ▍' if streaming else ''
        header = clip_to_width(f'{prefix}{label}{suffix}', inner)
        output: list[str] = [header]
        in_code = False
        raw_text = terminal_display(message.text)
        for raw_line in raw_text.split('\n'):
            stripped = raw_line.strip()
            if stripped.startswith('```'):
                lang = stripped[3:].strip()
                in_code = not in_code
                fence_label = f'── code {lang} ──' if (in_code and lang) else ('── code ──' if in_code else '──────────')
                output.append('  ' + clip_to_width(fence_label, max(1, inner - 2)))
                continue
            if in_code:
                for part in wrap_line(raw_line, max(1, inner - 4)):
                    output.append('  │ ' + part)
            elif stripped.startswith('# '):
                for part in wrap_line(stripped[2:].upper(), max(1, inner - 4)):
                    output.append('  ══ ' + part)
            elif stripped.startswith(('## ', '### ')):
                title = stripped.lstrip('#').strip()
                for part in wrap_line(title, max(1, inner - 4)):
                    output.append('  ── ' + part)
            elif stripped in ('---', '***', '___'):
                output.append('  ' + ('─' * max(4, min(inner - 2, 48))))
            elif stripped.startswith('> '):
                for part in wrap_line(stripped[2:], max(1, inner - 4)):
                    output.append('  ▎ ' + part)
            elif stripped.startswith(('- ', '* ')):
                for idx, part in enumerate(wrap_line(stripped[2:], max(1, inner - 4))):
                    bullet = '  • ' if idx == 0 else '    '
                    output.append(bullet + part)
            else:
                for part in wrap_line(raw_line, max(1, inner - 2)):
                    output.append('  ' + part)
        if in_code and streaming:
            output.append('  │ …')
        return tuple(output)

    def render_panel(self, title: str, content: str, width: int) -> Sequence[str]:
        width = max(12, width)
        clean_title = terminal_display(title).replace('\n', ' ').strip()
        clean_body = terminal_display(content).expandtabs(4)
        if width < 24:
            out = [clip_to_width(f'[{clean_title}]', width)]
            for line in clean_body.split('\n'):
                out.extend(wrap_line(line, width))
            return tuple(out)
        inner = min(width, 100) - 4
        wrapped: list[str] = []
        for line in clean_body.split('\n') or ['']:
            wrapped.extend(wrap_line(line, inner))
        header = clip_to_width(f' {clean_title} ', inner + 2)
        header_cols = display_width(header)
        top = '┌' + header + '─' * max(0, inner + 2 - header_cols) + '┐'
        bottom = '└' + '─' * (inner + 2) + '┘'
        middle = ['│ ' + pad_to_width(line, inner) + ' │' for line in wrapped]
        return tuple([top, *middle, bottom])


class DefaultSelector:
    """Rendu du sélecteur interactif pour changement de mode, scénario ou modèle."""
    def render_selector(self, title: str, items: Sequence[tuple[str, str, str]],
                        selected_index: int, width: int) -> Sequence[str]:
        inner = max(16, min(width - 4, 86))
        lines = [f'Sélection : {terminal_display(title)} (↑/↓ choisir, Entrée valider, Échap annuler)', '']
        if not items:
            lines.append('  (Aucun élément disponible)')
        for idx, (item_id, name, desc) in enumerate(items):
            marker = '▸ ' if idx == selected_index else '  '
            head = f'{marker}{name} [{item_id}]'
            if desc:
                head += f' — {desc}'
            for sub_idx, wrapped in enumerate(wrap_line(head, inner)):
                lines.append(('' if sub_idx == 0 else '    ') + wrapped)
        return tuple(lines)


class DefaultEditor:
    """Éditeur de saisie interactif avec support multiligne, retour visuel, Unicode, collage et historique."""
    def __init__(self) -> None:
        self._buffer: str = ''
        self._cursor: int = 0
        self._history: list[str] = []
        self._history_index: int | None = None
        self._draft: str = ''
        self._cursor_row: int = 0

    @property
    def buffer(self) -> str:
        return self._buffer

    @property
    def cursor(self) -> int:
        return self._cursor

    @cursor.setter
    def cursor(self, value: int) -> None:
        self._cursor = max(0, min(len(self._buffer), int(value)))
        self._cursor_row = self._buffer[:self._cursor].count('\n')

    @property
    def cursor_row(self) -> int:
        return self._cursor_row

    @property
    def history(self) -> Sequence[str]:
        return tuple(self._history)

    @staticmethod
    def _clean_input(value: str) -> str:
        normalized = str(value).replace('\r\n', '\n').replace('\r', '\n').replace('\t', '    ')
        return ''.join(
            c for c in normalized
            if c == '\n' or (
                c not in _BIDI_CONTROLS
                and unicodedata.category(c) not in ('Cc', 'Cs')
            )
        )

    def set_text(self, value: str, *, cursor: int | None = None) -> None:
        clean = self._clean_input(value)
        self._buffer = clean
        if cursor is None:
            self._cursor = len(clean)
        else:
            self._cursor = max(0, min(len(clean), int(cursor)))
        self._cursor_row = self._buffer[:self._cursor].count('\n')

    def insert_text(self, value: str) -> None:
        clean = self._clean_input(value)
        if not clean:
            return
        self._buffer = self._buffer[:self._cursor] + clean + self._buffer[self._cursor:]
        self._cursor += len(clean)
        self._cursor_row = self._buffer[:self._cursor].count('\n')

    def insert_newline(self) -> None:
        self.insert_text('\n')

    def clear(self) -> None:
        self._buffer = ''
        self._cursor = 0
        self._cursor_row = 0
        self._history_index = None

    def _cursor_line_col(self) -> tuple[list[str], int, int]:
        lines = self._buffer.split('\n')
        remaining = max(0, min(self._cursor, len(self._buffer)))
        for idx, line in enumerate(lines):
            if remaining <= len(line):
                return lines, idx, remaining
            remaining -= len(line) + 1
        return lines, len(lines) - 1, len(lines[-1])

    def handle_key(self, key: int | str) -> str | None:
        import curses
        if key in ('\x1b\n', '\x1b\r', 'SHIFT_ENTER', '\x0e'):
            self.insert_newline()
            return None
        if key in ('\n', '\r', curses.KEY_ENTER):
            # Continuation multiligne par antislash final explicite
            if self._buffer.endswith('\\') and self._cursor == len(self._buffer):
                self._buffer = self._buffer[:-1] + '\n'
                self._cursor_row = self._buffer[:self._cursor].count('\n')
                return None
            submitted = self._buffer
            if submitted.strip():
                if not self._history or self._history[-1] != submitted:
                    self._history.append(submitted)
            self.clear()
            return submitted
        if key in ('\b', '\x7f', curses.KEY_BACKSPACE):
            if self._cursor > 0:
                self._buffer = self._buffer[:self._cursor - 1] + self._buffer[self._cursor:]
                self._cursor -= 1
                self._cursor_row = self._buffer[:self._cursor].count('\n')
            return None
        if key == curses.KEY_DC:
            if self._cursor < len(self._buffer):
                self._buffer = self._buffer[:self._cursor] + self._buffer[self._cursor + 1:]
                self._cursor_row = self._buffer[:self._cursor].count('\n')
            return None
        if key == curses.KEY_LEFT:
            self._cursor = max(0, self._cursor - 1)
            self._cursor_row = self._buffer[:self._cursor].count('\n')
            return None
        if key == curses.KEY_RIGHT:
            self._cursor = min(len(self._buffer), self._cursor + 1)
            self._cursor_row = self._buffer[:self._cursor].count('\n')
            return None
        if key in (curses.KEY_HOME, '\x01'):
            lines, line_idx, _ = self._cursor_line_col()
            self._cursor = sum(len(l) + 1 for l in lines[:line_idx])
            self._cursor_row = line_idx
            return None
        if key in (curses.KEY_END, '\x05'):
            lines, line_idx, _ = self._cursor_line_col()
            self._cursor = sum(len(l) + 1 for l in lines[:line_idx]) + len(lines[line_idx])
            self._cursor_row = line_idx
            return None
        if key == '\x15':  # Ctrl+U
            self._buffer = self._buffer[self._cursor:]
            self._cursor = 0
            self._cursor_row = 0
            return None
        if key == '\x0b':  # Ctrl+K
            self._buffer = self._buffer[:self._cursor]
            self._cursor_row = self._buffer[:self._cursor].count('\n')
            return None
        if key == curses.KEY_UP:
            lines, line_idx, col = self._cursor_line_col()
            if len(lines) > 1 and line_idx > 0:
                prev_len = len(lines[line_idx - 1])
                self._cursor = sum(len(l) + 1 for l in lines[:line_idx - 1]) + min(col, prev_len)
                self._cursor_row = line_idx - 1
                return None
            if self._history:
                if self._history_index is None:
                    self._draft = self._buffer
                    self._history_index = len(self._history) - 1
                elif self._history_index > 0:
                    self._history_index -= 1
                self.set_text(self._history[self._history_index])
            return None
        if key == curses.KEY_DOWN:
            lines, line_idx, col = self._cursor_line_col()
            if len(lines) > 1 and line_idx < len(lines) - 1:
                next_len = len(lines[line_idx + 1])
                self._cursor = sum(len(l) + 1 for l in lines[:line_idx + 1]) + min(col, next_len)
                self._cursor_row = line_idx + 1
                return None
            if self._history_index is not None:
                if self._history_index < len(self._history) - 1:
                    self._history_index += 1
                    self.set_text(self._history[self._history_index])
                else:
                    self._history_index = None
                    self.set_text(self._draft)
            return None
        if isinstance(key, str) and len(key) >= 1:
            if '\n' in key or '\r' in key or len(key) > 1:
                self.insert_text(key)
            elif c_ok := self._clean_input(key):
                self._buffer = self._buffer[:self._cursor] + c_ok + self._buffer[self._cursor:]
                self._cursor += len(c_ok)
                self._cursor_row = self._buffer[:self._cursor].count('\n')
        return None

    def render_lines(self, width: int, *, active: bool = True) -> Sequence[str]:
        width = max(1, width)
        first_prompt = 'uchambuzi> ' if active else '·········> '
        cont_prompt = '         … ' if active else '           '
        wrap_prompt = '         ↪ ' if active else '           '
        if width < 18:
            first_prompt = '> ' if active else ': '
            cont_prompt = '… '
            wrap_prompt = '↪ '
        prefix_cols = display_width(first_prompt)
        avail = max(2, width - prefix_cols - 1)
        cursor_glyph = '█' if active else ''

        raw_lines, cursor_line, cursor_col = self._cursor_line_col()
        out: list[str] = []
        self._cursor_row = 0

        for idx, raw_line in enumerate(raw_lines):
            base_prefix = first_prompt if idx == 0 else cont_prompt
            clean_line = terminal_display(raw_line)
            is_cur_line = (idx == cursor_line)

            # Construction des jetons (caractères + curseur éventuel) pour un retour visuel exact
            tokens: list[tuple[str, bool]] = []
            for ch_idx, ch in enumerate(clean_line):
                if is_cur_line and ch_idx == cursor_col and cursor_glyph:
                    tokens.append((cursor_glyph, True))
                tokens.append((ch, False))
            if is_cur_line and cursor_col >= len(clean_line) and cursor_glyph:
                tokens.append((cursor_glyph, True))

            if not tokens:
                if is_cur_line:
                    self._cursor_row = len(out)
                out.append(clip_to_width(base_prefix, width))
                continue

            seg_chars: list[str] = []
            seg_cols = 0
            sub_idx = 0
            for tok, is_cursor in tokens:
                w = _char_display_width(tok)
                if seg_cols + w > avail and seg_chars:
                    cur_prefix = base_prefix if sub_idx == 0 else wrap_prompt
                    out.append(clip_to_width(cur_prefix + ''.join(seg_chars), width))
                    seg_chars = []
                    seg_cols = 0
                    sub_idx += 1
                if is_cursor:
                    self._cursor_row = len(out)
                seg_chars.append(tok)
                seg_cols += w

            if seg_chars or sub_idx == 0:
                cur_prefix = base_prefix if sub_idx == 0 else wrap_prompt
                out.append(clip_to_width(cur_prefix + ''.join(seg_chars), width))

        return tuple(out) or (clip_to_width(first_prompt + cursor_glyph, width),)


class StreamProtocolError(Exception):
    """Violation du protocole d'événements ConversationEngine.stream."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.user_message = message


class DefaultSessionEngine:
    """Adaptateur conforme à ConversationEngine encapsulant Session et LegacyConversation."""
    def __init__(self, session: Session) -> None:
        self.session = session
        self._legacy = LegacyConversation(session)
        self._lock = self._legacy._lock
        self.context_supplier: Callable[[], dict | None] | None = None
        self.on_injection_alerts: Callable[[Sequence[str]], None] | None = None

    async def stream(self, turn_id: str, message: Message):
        if message.role != Role.USER or not message.text.strip():
            raise ValueError('Un message utilisateur non vide est requis.')
        ctx = self.context_supplier() if self.context_supplier is not None else None
        async with self._lock:
            yield TurnStarted(turn_id, message.id)
            try:
                if ctx is not None:
                    task = asyncio.create_task(asyncio.to_thread(self.session.respond, message.text, ctx))
                else:
                    task = asyncio.create_task(asyncio.to_thread(self.session.respond, message.text))
                try:
                    answer = await asyncio.shield(task)
                except asyncio.CancelledError:
                    try:
                        await task
                    except Exception:
                        pass
                    raise
            except RuntimeIncomplete as exc:
                if exc.partial:
                    yield TextDelta(turn_id, exc.partial)
                yield TurnFinished(turn_id, TurnState.FAILED, 'engine_unavailable', safe_display(exc))
            except RuntimeErrorLocal as exc:
                yield TurnFinished(turn_id, TurnState.FAILED, 'engine_unavailable', safe_display(exc))
            except Exception:
                yield TurnFinished(turn_id, TurnState.FAILED, 'internal_error', 'Erreur interne du moteur.')
            else:
                alerts = getattr(self.session, 'last_injection_alerts', None)
                if alerts and self.on_injection_alerts is not None:
                    self.on_injection_alerts(tuple(alerts))
                yield TextDelta(turn_id, answer)
                yield TurnFinished(turn_id, TurnState.COMPLETE)


class DefaultModelProvider:
    """Adaptateur de modèles IA vers OllamaRuntime et DefaultSessionEngine."""
    def __init__(self, runtime=None, *, model: str | None = None, port: int = 11434,
                 timeout: float = DEFAULT_TIMEOUT, context_budget: int = DEFAULT_CONTEXT_BUDGET):
        self.runtime = runtime
        self.default_model = model
        self.port = port
        self.timeout = timeout
        self.context_budget = context_budget
        self._engine_cache: dict[tuple[str | None, str, str | None], ConversationEngine] = {}
        self._sessions: dict[tuple[str | None, str, str | None], Session] = {}

    def adapter_for(self, model_id: str | None = None):
        if self.runtime is not None:
            return self.runtime
        chosen = model_id if model_id is not None else self.default_model
        return OllamaRuntime(chosen, self.port, self.timeout)

    def list_models(self) -> Sequence[Model]:
        adapter = self.adapter_for()
        names = adapter.list_models()
        return tuple(Model(provider='ollama', id=str(name), local=True) for name in names)

    def get_session(self, model: Model | None, profile: Profile, scenario: Scenario | None) -> Session | None:
        model_id = model.id if model is not None else self.default_model
        if self.runtime is None and not model_id:
            return None
        key = (model_id, profile.id, scenario.id if scenario else None)
        if key not in self._sessions:
            adapter = self.adapter_for(model_id)
            self._sessions[key] = Session(adapter, self.context_budget)
        return self._sessions[key]

    def reset_sessions(self) -> None:
        for session in self._sessions.values():
            session.reset()

    def create_engine(self, model: Model | None, profile: Profile, scenario: Scenario | None,
                      *, timeout: float = DEFAULT_TIMEOUT,
                      context_budget: int = DEFAULT_CONTEXT_BUDGET) -> ConversationEngine | None:
        model_id = model.id if model is not None else self.default_model
        if self.runtime is None and not model_id:
            return None
        key = (model_id, profile.id, scenario.id if scenario else None)
        if key not in self._engine_cache:
            session = self.get_session(model, profile, scenario)
            if session is None:
                return None
            self._engine_cache[key] = DefaultSessionEngine(session)
        return self._engine_cache[key]


class InMemorySessionStore(SessionStore):
    """Stockage de session en mémoire conforme au contrat SessionStore."""
    def __init__(self) -> None:
        self._snapshots: dict[str, SessionSnapshot] = {}

    def load(self, session_id: str) -> SessionSnapshot:
        if session_id not in self._snapshots:
            self._snapshots[session_id] = SessionSnapshot(id=session_id)
        return self._snapshots[session_id]

    def save(self, snapshot: SessionSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot


@dataclass
class FocusExtensions:
    """Conteneur des extensions injectables pour les missions 03, 04 et 05."""
    editor: EditorExtension = field(default_factory=FocusEditor)
    markdown: MarkdownRendererExtension = field(default_factory=ConversationRenderer)
    logo: BrandLogoExtension = field(default_factory=lambda: BrandLogo(unicode=terminal_options()[0]))
    models: ModelProviderExtension | None = None
    selector: SelectorExtension = field(default_factory=DefaultSelector)
    catalog: Catalog = field(default_factory=InteractiveCatalog)
    store: SessionStore = field(default_factory=InMemorySessionStore)
    tool_service: ToolService | None = None
    confirmation_service: ConfirmationService | None = None


@dataclass
class TranscriptEntry:
    """Élément affiché dans le fil conversationnel ou d'activité."""
    kind: str  # 'message', 'panel', 'notice', 'error'
    message: Message | None = None
    title: str = ''
    body: str = ''
    streaming: bool = False
    complete: bool = True
    profile_id: str = 'assist'
    scenario_id: str | None = None


# ============================================================================
# Contrôleur et machine d'état du moteur TUI UCHAMBUZI Focus
# ============================================================================

class FocusTUIController:
    """Gère les états, régions défilantes, validations, modes et commandes métier."""
    SECTIONS = ('Conversation', 'Enquête', 'Aide')

    def __init__(
        self,
        *,
        model: str | None = None,
        port: int = 11434,
        timeout: float = DEFAULT_TIMEOUT,
        runtime=None,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
        case_id: str | None = None,
        extensions: FocusExtensions | None = None,
        engine: ConversationEngine | None = None,
        command_handler: Callable[[str], None] | None = None,
        max_transcript_entries: int = MAX_TRANSCRIPT_ENTRIES,
    ) -> None:
        self.extensions = extensions or FocusExtensions()
        if self.extensions.models is None:
            self.extensions.models = DefaultModelProvider(
                runtime=runtime,
                model=model,
                port=port,
                timeout=timeout,
                context_budget=context_budget,
            )
        self.catalog = self.extensions.catalog if isinstance(self.extensions.catalog, InteractiveCatalog) else InteractiveCatalog(self.extensions.catalog)
        self.profile: Profile = self.catalog.get_profile('assist') or DEFAULT_PROFILES[0]
        self.scenario: Scenario | None = None
        self.active_model: Model | None = (
            Model(provider='ollama', id=model, local=True)
            if model else (
                Model(provider='custom', id=str(getattr(runtime, 'model', 'local') or 'local'), local=True)
                if runtime is not None else None
            )
        )
        self._explicit_engine = engine
        self.timeout = timeout
        self.context_budget = context_budget
        self.port = port
        self.case_id = case_id
        self.custom_command_handler = command_handler
        self.max_transcript_entries = max(20, int(max_transcript_entries))

        # État UI, défilements et cache de rendu
        self.state: UIState = UIState.WELCOME
        self.previous_state: UIState = UIState.WELCOME
        self.active_section: int = 0  # 0: Conversation, 1: Enquête, 2: Aide
        self.scroll_offsets: list[int] = [0, 0, 0]
        self._region_positions = {}
        self._region_heights = {}
        self.editor_scroll_offset: int = 0
        self._bracketed_paste = False
        self._last_region_line_counts: list[int] = [0, 0, 0]
        self._render_cache: dict[tuple[int, int, int], tuple[Message, bool, tuple[str, ...]]] = {}

        # Journaux par région défilante
        self.entries: dict[int, list[TranscriptEntry]] = {0: [], 1: [], 2: []}
        self._profiles_entries: dict[tuple[str, str | None], list[TranscriptEntry]] = {
            (self.profile.id, None): self.entries[0]
        }

        # Suivi d'opération / streaming / corrélation / confirmation / erreur
        self.active_turn_id: str | None = None
        self.active_turn_state: TurnState = TurnState.IDLE
        self._active_assistant_entry: TranscriptEntry | None = None
        self._active_user_entry: TranscriptEntry | None = None
        self._running_task: asyncio.Task | None = None
        self._cancelled_turn_ids: set[str] = set()
        self._closed_turn_ids: set[str] = set()
        self.status_notice: str = 'Prêt — Tapez un message ou /help (Tab : régions, Ctrl+P : modes, Ctrl+D : quitter).'
        self.last_error_code: str | None = None
        self.last_error_message: str | None = None

        self.pending_confirmation: ConfirmationRequest | None = None
        self._confirmation_callback: Callable[[ConfirmationDecision], None] | None = None
        self._prompt_queue: list[tuple[str, Callable[[str], None]]] = []
        self._active_prompt: tuple[str, Callable[[str], None]] | None = None

        # Sélecteur de changement de mode / scénario / modèle
        self.selector_kind: str = 'mode'  # 'mode', 'scenario', 'model'
        self.selector_items: list[tuple[str, str, str]] = []
        self.selector_index: int = 0

        # Intégration métier UCHAMBUZI
        import conversation as conv_mod
        import parcours
        self.cases = parcours.CaseManager()
        initial_case = self.cases.open_case(case_id) if case_id is not None else None
        self.case_id = self.cases.active_case_id
        self.analysis: dict = (initial_case.get('latest_analysis') or {'choices': []}) if initial_case else {'choices': []}
        self.latest_analysis: dict | None = (
            self.analysis if self.analysis.get('choices') and not self.analysis.get('errors') else None
        )
        self.selected_context: dict | None = None
        self.context_enabled: bool = False
        adapter = self.extensions.models.adapter_for() if isinstance(self.extensions.models, DefaultModelProvider) else runtime
        self.provider_manager = conv_mod.ProviderManager(adapter)

        self.tool_ui = ToolUI(self)
        self._init_help_view()
        from focus_settings_ui import SettingsUI
        self.settings_ui = SettingsUI(self, use_ai=engine is None and runtime is None
                                      and isinstance(self.extensions.models, DefaultModelProvider),
                                      model=model, port=port)

    def _init_help_view(self) -> None:
        help_body = (
            '/mode [NOM] — changer de spécialité Focus (Assist, Trace, Intel, Defend, Assess, Validate, Engineer, Coordinate)\n'
            '/scenario [NOM|off] — activer un scénario métier ou revenir en mode libre\n'
            '/help — afficher cette aide\n'
            '/analyze TEXTE — détecter les indices et consulter les sources locales\n'
            '/indicator TYPE VALEUR — analyser un indice explicite (ip, domain, url, email, file)\n'
            '/target N — examiner l’hôte dérivé d’une URL ou d’un e-mail\n'
            '/prepare N — préparer une commande bornée sans exécution automatique\n'
            '/investigation [create ID|open ID|status|list|rename TITRE|archive|delete|close] — gérer les dossiers d’enquête isolés\n'
            '/methods [list|approve|reject|stage] — méthodes éprouvées et quarantaine documentaire\n'
            '/audit CHEMIN — auditer un fichier suspect contre l’injection de prompt\n'
            '/search REQUÊTE — recherche documentaire locale pondérée\n'
            '/tools — inventaire local des outils ; /models — modèles locaux disponibles\n'
            '/context [N|off] — sélectionner le contexte pour l’IA ; /reset — réinitialiser la session\n'
            '/ai — fournisseurs ; /settings [show|set NOM VALEUR] — paramètres ; /exit — quitter\n'
            '/context sessions · /context directory ; Ctrl+S ouvre les paramètres pendant le streaming\n'
            'Raccourcis TUI : Tab/Maj+Tab (régions), PgUp/PgDn (défiler), Ctrl+P (modes), Ctrl+C (interrompre), Ctrl+D (quitter).'
        )
        self.entries[2] = [TranscriptEntry(kind='panel', title='Commandes et raccourcis UCHAMBUZI Focus', body=help_body)]

    def _trim_entries(self, section: int) -> None:
        items = self.entries[section]
        if len(items) > self.max_transcript_entries:
            del items[:len(items) - self.max_transcript_entries]

    def current_engine(self) -> ConversationEngine | None:
        if hasattr(self, 'settings_ui') and self.settings_ui.use_ai:
            ui = self.settings_ui
            if ui.ai.model_id or ui.requested_model:
                return ui.engine
            return None
        if self._explicit_engine is not None:
            return self._explicit_engine
        if self.extensions.models is None:
            return None
        return self.extensions.models.create_engine(
            self.active_model,
            self.profile,
            self.scenario,
            timeout=self.timeout,
            context_budget=self.context_budget,
        )

    def add_panel(self, section: int, title: str, body: str, *, reset_scroll: bool = True) -> None:
        self.entries[section].append(
            TranscriptEntry(
                kind='panel',
                title=terminal_display(title),
                body=terminal_display(body),
                profile_id=self.profile.id,
                scenario_id=self.scenario.id if self.scenario else None,
            )
        )
        self._trim_entries(section)
        if reset_scroll:
            self.scroll_offsets[section] = 0

    def add_notice(self, section: int, text: str, *, reset_scroll: bool = True) -> None:
        self.entries[section].append(
            TranscriptEntry(
                kind='notice',
                body=terminal_display(text),
                profile_id=self.profile.id,
                scenario_id=self.scenario.id if self.scenario else None,
            )
        )
        self._trim_entries(section)
        if reset_scroll:
            self.scroll_offsets[section] = 0

    def set_error(self, code: str, message: str, *, section: int | None = None) -> None:
        self.last_error_code = terminal_display(code)
        self.last_error_message = terminal_display(message)
        self.state = UIState.ERROR
        target_section = self.active_section if section is None else section
        self.entries[target_section].append(
            TranscriptEntry(
                kind='error',
                title=f'Erreur [{self.last_error_code}]',
                body=self.last_error_message,
                profile_id=self.profile.id,
                scenario_id=self.scenario.id if self.scenario else None,
            )
        )
        self._trim_entries(target_section)
        self.status_notice = f'Erreur ({self.last_error_code}) : {self.last_error_message} — Tapez Entrée ou une commande pour continuer.'

    def clear_error(self) -> None:
        if self.state == UIState.ERROR:
            self.last_error_code = None
            self.last_error_message = None
            self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
            self.status_notice = 'Prêt.'

    def request_confirmation(self, action: str, details: str,
                             on_decision: Callable[[ConfirmationDecision], None]) -> ConfirmationRequest:
        req = ConfirmationRequest(
            id='confirm-' + secrets.token_hex(6),
            action=terminal_display(action),
            details=terminal_display(details),
        )
        self.previous_state = self.state if self.state != UIState.CONFIRMATION else UIState.CONVERSATION
        self.pending_confirmation = req
        self._confirmation_callback = on_decision
        self.state = UIState.CONFIRMATION
        self.status_notice = f'Validation requise [{req.action}] : tapez oui (ou y) pour approuver, non (ou n/Échap) pour refuser.'
        self.add_panel(self.active_section, f'Demande de validation — {req.action}', req.details + '\n\nConfirmer ? (oui / non)')
        return req

    def resolve_confirmation(self, approved: bool) -> ConfirmationDecision | None:
        if self.pending_confirmation is None:
            return None
        req = self.pending_confirmation
        decision = ConfirmationDecision(request_id=req.id, approved=bool(approved))
        callback = self._confirmation_callback
        self.pending_confirmation = None
        self._confirmation_callback = None
        is_valid = approved_for(req, decision)
        if not self._active_prompt and not self._prompt_queue:
            self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
        self.status_notice = 'Validation accordée.' if is_valid else 'Opération annulée (validation refusée).'
        if callback is not None:
            callback(decision)
        return decision

    def open_mode_selector(self, kind: str = 'mode') -> None:
        self.settings_ui.open_modes(kind)

    def handle_selector_key(self, key: int | str) -> bool:
        return self.settings_ui.key(key)

    def switch_profile(self, profile_id: str) -> bool:
        target = self.catalog.get_profile(profile_id)
        if target is None:
            self.set_error('unknown_mode', f'Mode inconnu : {profile_id}. Utilisez /mode pour lister les choix.')
            return False
        if self.settings_ui.busy:
            self.status_notice = 'Changement de mode après la fin du tour IA.'
            return False
        self.tool_ui.invalidate()
        self.settings_ui.select_mode(target.id)
        self.profile = target
        self.scenario = None
        key = (self.profile.id, None)
        if key not in self._profiles_entries:
            self._profiles_entries[key] = []
        self.entries[0] = self._profiles_entries[key]
        self.selected_context = None
        self.context_enabled = False
        self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
        self.active_section = 0
        self.scroll_offsets[0] = 0
        self._last_region_line_counts[0] = 0
        msg = f'Mode : {self.profile.name} — {self.profile.instructions} (contexte conversationnel isolé, aucun droit supplémentaire).'
        self.add_notice(0, msg)
        self.state = UIState.CONVERSATION
        self.status_notice = f'Mode actif : {self.profile.name}'
        return True

    def switch_scenario(self, scenario_id: str | None) -> bool:
        if self.settings_ui.busy:
            self.status_notice = 'Changement de scénario après la fin du tour IA.'
            return False
        if scenario_id is None or scenario_id.strip().lower() == 'off':
            target = None
        else:
            target = self.catalog.get_scenario(self.profile.id, scenario_id)
            if target is None:
                self.set_error('unknown_scenario', f'Scénario inconnu pour {self.profile.name} : {scenario_id}.')
                return False
        self.tool_ui.invalidate()
        self.settings_ui.select_scenario(target)
        self.scenario = target
        key = (self.profile.id, self.scenario.id if self.scenario else None)
        if key not in self._profiles_entries:
            self._profiles_entries[key] = []
        self.entries[0] = self._profiles_entries[key]
        self.selected_context = None
        self.context_enabled = False
        self.active_section = 0
        self.scroll_offsets[0] = 0
        self._last_region_line_counts[0] = 0
        label = self.scenario.id if self.scenario else 'libre'
        self.add_notice(0, f'Scénario : {label} (contexte de conversation isolé).')
        self.state = UIState.CONVERSATION
        self.status_notice = f'Mode : {self.profile.name} ({label}) · /scenario parameters pour régler les valeurs'
        return True

    def close(self) -> None:
        self.tool_ui.close()
        self.state = UIState.CLOSING
        self.status_notice = 'Fermeture de la session…'

    def scroll_up(self, steps: int = 5) -> None:
        self.scroll_offsets[self.active_section] += max(1, steps)

    def scroll_down(self, steps: int = 5) -> None:
        self.scroll_offsets[self.active_section] = max(0, self.scroll_offsets[self.active_section] - max(1, steps))

    def next_section(self) -> None:
        self.active_section = (self.active_section + 1) % len(self.SECTIONS)
        self.scroll_offsets[self.active_section] = 0

    def prev_section(self) -> None:
        self.active_section = (self.active_section - 1) % len(self.SECTIONS)
        self.scroll_offsets[self.active_section] = 0

    def interrupt_running_turn(self) -> bool:
        """Interrompt le tour IA actif sans altérer ni effacer le brouillon de l'éditeur."""
        turn_id = self.active_turn_id
        has_active = turn_id is not None or self.state == UIState.RUNNING or (
            self._running_task is not None and not self._running_task.done()
        )
        if not has_active:
            return False
        self.settings_ui.cancel_turn(turn_id)
        if turn_id is not None:
            self._cancelled_turn_ids.add(turn_id)
            self._closed_turn_ids.add(turn_id)
        if self._active_assistant_entry is not None:
            self._active_assistant_entry.streaming = False
            self._active_assistant_entry.complete = False
            if self._active_assistant_entry.message is not None and not self._active_assistant_entry.message.text:
                if self._active_assistant_entry in self.entries[0]:
                    self.entries[0].remove(self._active_assistant_entry)
        if self._active_user_entry is not None:
            self._active_user_entry.complete = False
        self.active_turn_id = None
        self.active_turn_state = TurnState.CANCELLED
        self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
        self.add_notice(
            0,
            'Interrompu par l’utilisateur : réponse partielle non certifiée et non enregistrée dans la session.',
            reset_scroll=False,
        )
        self.status_notice = 'Inférence interrompue ; brouillon et session conservés.'
        if self._running_task is not None and not self._running_task.done():
            self._running_task.cancel()
        return True

    def handle_key(
        self,
        key: int | str,
        *,
        page_step: int = 18,
        on_render: Callable[[], None] | None = None,
    ) -> str | None:
        """Traite une touche clavier dans tous les états, y compris pendant le streaming IA (RUNNING)."""
        import curses
        is_running = (
            self.state == UIState.RUNNING
            or self.active_turn_id is not None
            or (self._running_task is not None and not self._running_task.done())
        )

        # Le texte d'un collage bracketé ne doit pas déclencher les raccourcis.
        if key == '\x1b[200~':
            self._bracketed_paste = True
        if self._bracketed_paste:
            paste_editor = self.settings_ui.value_editor or self.extensions.editor
            paste_editor.handle_key(key)
            if key == '\x1b[201~':
                self._bracketed_paste = False
            if on_render:
                on_render()
            return None

        # Mission 11: panels have their own lifetime, independent of TurnFinished.
        if key == '\x13':  # Ctrl+S opens settings even during a stream.
            self.settings_ui.open_settings()
            return None
        if self.settings_ui.panel is not None:
            if key == '\x03' and is_running:
                self.settings_ui.close()
                self.interrupt_running_turn()
            else:
                self.settings_ui.key(key)
            if on_render:
                on_render()
            return None

        # 1. Interruption Ctrl+C : en cours de streaming, arrête le flux SANS effacer le brouillon
        if key == '\x03':
            if hasattr(self, 'tool_ui') and self.tool_ui.cancel():
                return None
            if is_running:
                self.interrupt_running_turn()
            elif self.state == UIState.CONFIRMATION:
                self.resolve_confirmation(False)
            elif self.state == UIState.MODE_SWITCH:
                self.state = self.previous_state if self.previous_state != UIState.MODE_SWITCH else UIState.CONVERSATION
                self.status_notice = 'Sélection annulée.'
            elif self._active_prompt is not None:
                self._active_prompt = None
                self._prompt_queue.clear()
                self.status_notice = 'Saisie de paramètre annulée.'
            else:
                self.extensions.editor.clear()
                self.editor_scroll_offset = 0
                self.status_notice = 'Saisie effacée (Ctrl+D ou /exit pour quitter).'
            if on_render:
                on_render()
            return None

        # 2. Fermeture rapide Ctrl+D sur tampon vide hors streaming
        if key == '\x04':
            if not self.extensions.editor.buffer and not is_running:
                self.close()
                if on_render:
                    on_render()
            return None

        # 3. Ouverture du sélecteur de spécialité (Ctrl+P) hors streaming
        if key == '\x10':
            if not is_running:
                self.open_mode_selector('mode')
                if on_render:
                    on_render()
            return None

        # 4. Navigation dans le sélecteur modal
        if self.state == UIState.MODE_SWITCH:
            self.handle_selector_key(key)
            if on_render:
                on_render()
            return None

        # 5. Navigation entre régions et défilement (actifs même en RUNNING et CONFIRMATION)
        if key == '\t':
            self.next_section()
            if on_render:
                on_render()
            return None
        if key == curses.KEY_BTAB:
            self.prev_section()
            if on_render:
                on_render()
            return None
        if key == curses.KEY_PPAGE:
            self.scroll_up(max(1, page_step))
            if on_render:
                on_render()
            return None
        if key == curses.KEY_NPAGE:
            self.scroll_down(max(1, page_step))
            if on_render:
                on_render()
            return None

        # 6. Touche Échap (annule confirmation ou efface bannière d'erreur)
        if key == '\x1b':
            if self.state == UIState.CONFIRMATION:
                self.resolve_confirmation(False)
                if on_render:
                    on_render()
                return None
            if self.state == UIState.ERROR:
                self.clear_error()
                if on_render:
                    on_render()
                return None

        if key == '\x0f' and hasattr(self.extensions.editor, 'copy_selection'):
            copied = self.extensions.editor.copy_selection()
            async def system_copy():
                from focus_clipboard import copy_text
                backend = await asyncio.to_thread(copy_text, copied)
                self.status_notice = ('Sélection copiée : ' + backend) if backend else 'Copie interne disponible (Ctrl+Y) ; presse-papiers système indisponible.'
            if copied:
                self.settings_ui.spawn(system_copy())
            self.status_notice = 'Sélection copiée dans le presse-papiers interne (Ctrl+Y pour coller).'
            return None
        if key == '\x19' and hasattr(self.extensions.editor, 'clipboard'):
            self.extensions.editor.insert_text(self.extensions.editor.clipboard)
            return None
        if key == '\x15':
            editor = self.extensions.editor
            editor.set_text(editor.buffer[editor.cursor:], cursor=0)
            return None

        # 7. Délégation à l'éditeur (active même pendant RUNNING !)
        draft_before = self.extensions.editor.buffer
        cursor_before = self.extensions.editor.cursor
        submitted = self.extensions.editor.handle_key(key)

        if submitted is not None and is_running:
            # Refus non destructif pendant un tour actif : on restaure intégralement le brouillon et le curseur
            if hasattr(self.extensions.editor, 'set_text'):
                try:
                    self.extensions.editor.set_text(draft_before, cursor=cursor_before)
                except TypeError:
                    self.extensions.editor.set_text(draft_before)
            self.status_notice = 'Génération en cours : brouillon conservé (attendez la fin ou Ctrl+C pour interrompre).'
            if on_render:
                on_render()
            return None

        if on_render:
            on_render()
        return submitted

    async def run_conversation_turn(
        self,
        text: str,
        *,
        on_render: Callable[[], None] | None = None,
    ) -> TurnFinished:
        """Exécute un tour conversationnel avec corrélation stricte des événements et protection d'état."""
        if self.settings_ui.values['network'] == 'deny':
            self.status_notice = 'Réseau désactivé, y compris loopback ; aucune requête IA.'
            return TurnFinished('network-disabled', TurnState.FAILED, 'network_disabled')
        if self.settings_ui._consent is None and self.settings_ui.confirm_external_turn(text):
            return TurnFinished('consent-required', TurnState.CANCELLED)
        turn_id = 'turn-' + secrets.token_hex(6)
        user_msg = Message(id='msg-' + secrets.token_hex(6), role=Role.USER, text=text)
        if self.state in (UIState.WELCOME, UIState.ERROR):
            self.state = UIState.CONVERSATION
        self.active_section = 0
        user_entry = TranscriptEntry(
            kind='message',
            message=user_msg,
            complete=False,
            profile_id=self.profile.id,
            scenario_id=self.scenario.id if self.scenario else None,
        )
        self.entries[0].append(user_entry)
        self._trim_entries(0)

        engine = self.current_engine()
        if engine is None:
            user_entry.complete = True
            self.add_notice(0, 'IA non configurée : analyse locale effectuée si applicable. Utilisez --model NOM pour activer un modèle local.')
            self.state = UIState.CONVERSATION
            return TurnFinished(turn_id=turn_id, state=TurnState.COMPLETE)

        if isinstance(engine, DefaultSessionEngine):
            engine.context_supplier = lambda: (self.selected_context if self.context_enabled else None)
            engine.on_injection_alerts = lambda alerts: self.add_notice(
                0,
                'Alerte sécurité : motif d’injection de prompt détecté et isolé (' + ', '.join(alerts) + ').',
                reset_scroll=False,
            )

        assistant_msg_id = 'msg-' + secrets.token_hex(6)
        assistant_entry = TranscriptEntry(
            kind='message',
            message=Message(id=assistant_msg_id, role=Role.ASSISTANT, text=''),
            streaming=True,
            complete=False,
            profile_id=self.profile.id,
            scenario_id=self.scenario.id if self.scenario else None,
        )
        self.entries[0].append(assistant_entry)
        self._trim_entries(0)

        self.active_turn_id = turn_id
        self.active_turn_state = TurnState.RUNNING
        self._active_user_entry = user_entry
        self._active_assistant_entry = assistant_entry
        self.state = UIState.RUNNING
        self.status_notice = f'Opération IA en cours ({self.profile.name}) — saisie active, Ctrl+C pour interrompre…'
        if on_render:
            on_render()

        chunks: list[str] = []
        finished_event: TurnFinished | None = None
        started = False
        last_draw = 0.0
        stream_iter = None

        try:
            session = getattr(engine, 'session', None)
            if (
                session is not None
                and not isinstance(engine, DefaultSessionEngine)
                and self.context_enabled
                and self.selected_context is not None
            ):
                # Pont de compatibilité si un LegacyConversation externe est utilisé avec contexte actif
                started = True
                try:
                    answer = await asyncio.to_thread(session.respond, text, self.selected_context)
                except RuntimeIncomplete as exc:
                    if exc.partial:
                        chunks.append(exc.partial)
                    finished_event = TurnFinished(turn_id, TurnState.FAILED, 'engine_unavailable', safe_display(exc))
                except RuntimeErrorLocal as exc:
                    finished_event = TurnFinished(turn_id, TurnState.FAILED, 'engine_unavailable', safe_display(exc))
                except Exception:
                    finished_event = TurnFinished(turn_id, TurnState.FAILED, 'internal_error', 'Erreur interne du moteur.')
                else:
                    if turn_id in self._cancelled_turn_ids:
                        raise asyncio.CancelledError()
                    if getattr(session, 'last_injection_alerts', None):
                        self.add_notice(
                            0,
                            'Alerte sécurité : motif d’injection de prompt détecté et isolé ('
                            + ', '.join(session.last_injection_alerts) + ').',
                            reset_scroll=False,
                        )
                    chunks.append(answer)
                    finished_event = TurnFinished(turn_id, TurnState.COMPLETE)
            else:
                stream_iter = engine.stream(turn_id, user_msg).__aiter__()
                async for event in stream_iter:
                    if turn_id in self._cancelled_turn_ids or self.active_turn_id != turn_id:
                        raise asyncio.CancelledError()

                    if isinstance(event, TurnStarted):
                        if started:
                            raise StreamProtocolError('duplicate_turn_started', 'Événement TurnStarted dupliqué.')
                        if finished_event is not None:
                            raise StreamProtocolError('event_after_finish', 'Événement TurnStarted reçu après la clôture du tour.')
                        if not isinstance(event.turn_id, str) or event.turn_id != turn_id:
                            raise StreamProtocolError('turn_id_mismatch', 'Identifiant de tour TurnStarted incohérent.')
                        if not isinstance(event.message_id, str) or event.message_id != user_msg.id:
                            raise StreamProtocolError('message_id_mismatch', 'Identifiant de message TurnStarted incohérent.')
                        started = True
                        self.active_turn_state = TurnState.RUNNING

                    elif isinstance(event, TextDelta):
                        if not started:
                            raise StreamProtocolError('delta_before_start', 'Fragment TextDelta reçu avant TurnStarted.')
                        if finished_event is not None:
                            raise StreamProtocolError('event_after_finish', 'Fragment TextDelta reçu après la clôture du tour.')
                        if not isinstance(event.turn_id, str) or event.turn_id != turn_id:
                            raise StreamProtocolError('turn_id_mismatch', 'Fragment TextDelta appartenant à un autre tour.')
                        if not isinstance(event.text, str):
                            raise StreamProtocolError('invalid_delta', 'Fragment TextDelta invalide.')
                        chunks.append(event.text)
                        assistant_entry.message = Message(
                            id=assistant_msg_id,
                            role=Role.ASSISTANT,
                            text=''.join(chunks),
                        )
                        now = time.monotonic()
                        if on_render and (now - last_draw) >= MIN_STREAM_RENDER_INTERVAL:
                            on_render()
                            last_draw = now

                    elif isinstance(event, TurnFinished):
                        if not started:
                            raise StreamProtocolError('finish_before_start', 'Événement TurnFinished reçu avant TurnStarted.')
                        if finished_event is not None:
                            raise StreamProtocolError('duplicate_turn_finished', 'Événement TurnFinished dupliqué après clôture.')
                        if not isinstance(event.turn_id, str) or event.turn_id != turn_id:
                            raise StreamProtocolError('turn_id_mismatch', 'Événement TurnFinished appartenant à un autre tour.')
                        finished_event = event

                    else:
                        raise StreamProtocolError('invalid_event', 'Type d’événement inconnu dans le flux.')

                if turn_id in self._cancelled_turn_ids:
                    raise asyncio.CancelledError()
                if not started or finished_event is None:
                    raise StreamProtocolError('incomplete_stream', 'Flux interrompu sans événement TurnFinished valide.')

        except asyncio.CancelledError:
            already_handled = turn_id in self._cancelled_turn_ids
            self._cancelled_turn_ids.add(turn_id)
            self._closed_turn_ids.add(turn_id)
            assistant_entry.streaming = False
            assistant_entry.complete = False
            user_entry.complete = False
            partial = ''.join(chunks)
            assistant_entry.message = Message(
                id=assistant_msg_id,
                role=Role.ASSISTANT,
                text=partial,
            )
            if not partial and assistant_entry in self.entries[0]:
                self.entries[0].remove(assistant_entry)
            if not already_handled:
                self.add_notice(
                    0,
                    'Interrompu par l’utilisateur : réponse partielle non certifiée et non enregistrée dans la session.',
                    reset_scroll=False,
                )
            if self.active_turn_id == turn_id:
                self.active_turn_id = None
            self._active_user_entry = None
            self._active_assistant_entry = None
            self.active_turn_state = TurnState.CANCELLED
            self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
            self.status_notice = 'Inférence interrompue ; brouillon et session conservés.'
            if on_render:
                on_render()
            return TurnFinished(turn_id=turn_id, state=TurnState.CANCELLED, message='Inférence interrompue.')

        except StreamProtocolError as exc:
            finished_event = TurnFinished(turn_id, TurnState.FAILED, exc.code, exc.user_message)
        except Exception:
            finished_event = TurnFinished(turn_id, TurnState.FAILED, 'invalid_stream', 'Flux interrompu ou incohérent.')
        finally:
            self._closed_turn_ids.add(turn_id)
            if self.active_turn_id == turn_id:
                self.active_turn_id = None
            self._active_user_entry = None
            self._active_assistant_entry = None
            if stream_iter is not None and hasattr(stream_iter, 'aclose'):
                try:
                    await stream_iter.aclose()
                except Exception:
                    pass

        assistant_entry.streaming = False
        assistant_entry.message = Message(
            id=assistant_msg_id,
            role=Role.ASSISTANT,
            text=''.join(chunks),
        )
        if finished_event is None:
            finished_event = TurnFinished(turn_id, TurnState.FAILED, 'incomplete_stream', 'Flux interrompu sans état final.')

        self.active_turn_state = finished_event.state
        if finished_event.state != TurnState.COMPLETE:
            assistant_entry.complete = False
            user_entry.complete = False
            if not chunks and assistant_entry in self.entries[0]:
                self.entries[0].remove(assistant_entry)
            if chunks:
                self.add_notice(
                    0,
                    'Réponse partielle : non certifiée et non enregistrée dans la session.',
                    reset_scroll=False,
                )
            if finished_event.state == TurnState.CANCELLED:
                self.state = UIState.CONVERSATION if self.entries[0] else UIState.WELCOME
                self.status_notice = 'Inférence interrompue ; réponse partielle non enregistrée.'
            else:
                self.set_error(
                    finished_event.error_code or 'engine_error',
                    finished_event.message or 'Moteur IA indisponible ou réponse invalide.',
                    section=0,
                )
        else:
            user_entry.complete = True
            assistant_entry.complete = True
            self.state = UIState.CONVERSATION
            self.status_notice = 'Réponse reçue (non vérifiée — sources et faits à contrôler).'
            self._save_snapshot()
        if on_render:
            on_render()
        return finished_event

    def _save_snapshot(self) -> None:
        msgs: list[Message] = [
            e.message for e in self.entries[0]
            if e.kind == 'message' and e.message is not None and not e.streaming and e.complete
        ]
        snap = SessionSnapshot(
            id=f'{self.profile.id}:{self.scenario.id if self.scenario else "free"}',
            messages=tuple(msgs),
            settings=Settings(
                model=self.active_model,
                profile_id=self.profile.id,
                timeout_seconds=self.timeout,
                context_budget_bytes=self.context_budget,
            ),
            scenario_id=self.scenario.id if self.scenario else None,
        )
        self.extensions.store.save(snap)
        try:
            self.settings_ui.persist(snap)
        except (ValueError, OSError, RuntimeError):
            self.add_notice(0, 'Historique non enregistré : contenu sensible, conflit ou stockage indisponible.')

    # ========================================================================
    # Traitement des commandes et entrées utilisateur
    # ========================================================================

    def _queue_prompts(self, prompts: Sequence[tuple[str, Callable[[str], None]]]) -> None:
        self._prompt_queue.extend(prompts)
        self._advance_prompt_queue()

    def _advance_prompt_queue(self) -> None:
        if self._active_prompt is None and self._prompt_queue:
            label, callback = self._prompt_queue.pop(0)
            self._active_prompt = (label, callback)
            self.status_notice = label

    async def submit_input(self, raw_text: str, *, on_render: Callable[[], None] | None = None) -> None:
        import uchambuzi as app_mod
        import documentation_locale
        import indices_outils
        import commandes
        from parcours import (
            analyse,
            context_for_choice,
            methods_reviews,
            prepare_selected,
            refusal,
            render_analysis,
            render_preparation,
            stage_corpus_file,
        )
        from conversation import audit_file_prompt_injection, RuntimeIncomplete

        text = raw_text.strip()

        # 1. Si une validation (ConfirmationRequest) est en attente
        if self.state == UIState.CONFIRMATION and self.pending_confirmation is not None:
            low = text.lower()
            if low in ('oui', 'o', 'yes', 'y'):
                self.resolve_confirmation(True)
            else:
                self.resolve_confirmation(False)
            if on_render:
                on_render()
            return

        # 2. Si une question multi-étapes (ex: paramètres de /prepare ou /settings) est active
        if self._active_prompt is not None:
            _, callback = self._active_prompt
            self._active_prompt = None
            try:
                callback(text)
            except Exception as exc:
                self.set_error('operation_refused', f'Opération refusée : {safe_display(exc)}')
            self._advance_prompt_queue()
            if on_render:
                on_render()
            return

        # 3. Effacer l'état d'erreur précédent si l'utilisateur appuie sur Entrée ou tape une commande
        if self.state == UIState.ERROR:
            self.clear_error()
            if not text:
                if on_render:
                    on_render()
                return

        if not text:
            return

        normalized = app_mod.normalize_command(text)
        try:
            normalized = self.settings_ui.resolve_command(normalized)
        except (ValueError, OSError):
            self.status_notice = 'Répertoire de travail indisponible ; commande non exécutée.'
            return
        if normalized.split(maxsplit=1)[0] in ('/settings', '/models', '/ai', '/context', '/scenario'):
            try:
                if await self.settings_ui.command(normalized):
                    if on_render:
                        on_render()
                    return
            except (ValueError, OSError, RuntimeError):
                self.status_notice = 'Paramètre refusé ou indisponible ; configuration conservée.'
                return

        try:
            if await self.tool_ui.command(normalized):
                return
        except (ValueError, OSError, PermissionError) as exc:
            self.set_error('tool_error', str(exc))
            return

        # Fermeture
        if normalized in ('/exit', '/quit', 'exit'):
            self.close()
            return

        # Changement de mode / spécialité Focus
        if normalized == '/mode' or normalized.startswith('/mode '):
            arg = normalized[len('/mode'):].strip().lower()
            if not arg:
                self.open_mode_selector('mode')
            elif arg in ('list', 'liste'):
                modes_text = ', '.join(p.name for p in self.catalog.profiles())
                self.add_panel(0, 'Modes Focus disponibles', f'Modes : {modes_text}\nActif : {self.profile.name} ; tapez /mode NOM ou Ctrl+P pour changer.')
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
            else:
                self.switch_profile(arg)
            if on_render:
                on_render()
            return

        # Changement de scénario Focus
        if normalized == '/scenario' or normalized.startswith('/scenario '):
            arg = normalized[len('/scenario'):].strip().lower()
            if not arg:
                self.open_mode_selector('scenario')
            elif arg in ('list', 'liste'):
                avail = ', '.join(s.id for s in self.catalog.scenarios(self.profile.id))
                self.add_panel(0, f'Scénarios ({self.profile.name})', f'Scénarios : {avail}\nUtilisez /scenario NOM ou /scenario off.')
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
            else:
                self.switch_scenario('off' if arg == 'off' else arg)
            if on_render:
                on_render()
            return

        # Aide
        if normalized == '/help':
            self.active_section = 2
            self.scroll_offsets[2] = 0
            if self.state == UIState.WELCOME:
                self.state = UIState.CONVERSATION
            self.status_notice = 'Section Aide affichée (Tab pour revenir à Conversation).'
            if on_render:
                on_render()
            return

        try:
            if normalized.startswith('/audit '):
                target_path = normalized[len('/audit '):].strip()
                report = audit_file_prompt_injection(target_path)
                self.cases.record_security_audit(report)
                body = audit_description(report)
                self.active_section = 1
                self.add_panel(1, 'Audit anti-injection de prompt', body)
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                self.status_notice = 'Audit terminé — consultez la région Enquête.'
                return

            if normalized.startswith('/search '):
                query = normalized[len('/search '):].strip()
                corpus = documentation_locale.Corpus()
                results = corpus.search_ranked(query)
                self.active_section = 1
                if not results:
                    self.add_panel(1, 'Recherche documentaire', f'Aucun outil ou manuel local trouvé pour : {query}')
                else:
                    lines = []
                    for result in results:
                        item = result['item']
                        if result['kind'] == 'tool':
                            lines.append(f"[{result['kind']}] {result['id']} (score {result['score']}) — {item['objective']} [fiche outil]")
                        else:
                            lines.append(
                                f"[{result['kind']}] {result['id']} (score {result['score']}) — {item.get('title', result['id'])}"
                                f" [source : {parcours.readable_code(item['availability'])}, {parcours.readable_code(item['verification'])}, {parcours.readable_code(item['freshness'])}, {parcours.readable_code(item['compatibility'])}]"
                            )
                    self.add_panel(1, 'Recherche documentaire pondérée', '\n'.join(lines))
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                self.status_notice = f'Recherche documentaire pour « {query} » affichée dans Enquête.'
                return

            if normalized == '/methods' or normalized.startswith('/methods '):
                arg = normalized[len('/methods'):].strip()
                reviews = methods_reviews()
                corpus = documentation_locale.Corpus()
                self.active_section = 1
                if not arg or arg in ('list', 'liste'):
                    approved = reviews.approved(corpus, indices_outils.inventory())
                    if not approved:
                        self.add_panel(1, 'Méthodes éprouvées', 'Aucune méthode approuvée enregistrée. Utilisez /methods approve <N> <auteur> | <motif> après /analyze.')
                    else:
                        lines = []
                        for review in approved:
                            event = review['event']
                            proposal = event['proposal']
                            status = (
                                'remplacée' if review['superseded'] else
                                'à réexaminer : ' + ', '.join(review['reasons']) if review['potentially_obsolete'] else 'courante'
                            )
                            lines.append(f"{proposal['tool']} ({proposal['indicator_type']}) — revue par {event['actor']} le {event['timestamp']} [{status}]")
                        lines.append('Approbations documentaires déclaratives ; aucune autorisation d’exécution.')
                        self.add_panel(1, 'Revues documentaires', '\n'.join(lines))
                elif arg.startswith(('approve ', 'approuver ', 'reject ', 'rejeter ')):
                    parts = arg.split(maxsplit=2)
                    verb = parts[0]
                    decision_str = 'approved' if verb in ('approve', 'approuver') else 'rejected'
                    if len(parts) < 3 or '|' not in parts[2]:
                        raise ValueError('Usage : /methods approve <N> <auteur> | <motif> (ou reject).')
                    number = int(parts[1])
                    actor, reason = [p.strip() for p in parts[2].split('|', 1)]
                    choices = self.analysis.get('choices', [])
                    if number < 1 or number > len(choices):
                        raise ValueError('Numéro de recommandation invalide ; exécutez /analyze d’abord.')
                    rec = choices[number - 1]['recommendation']

                    def _on_method_confirm(dec: ConfirmationDecision) -> None:
                        entry = reviews.record(rec, decision_str, actor, reason, human_confirmed=dec.approved)
                        self.add_panel(
                            1,
                            'Validation humaine de méthode',
                            f"Outil : {entry['proposal']['tool']} ({entry['proposal']['indicator_type']})\n"
                            f"Décision documentaire : {entry['decision']} par {entry['actor']}\n"
                            f"Horodatage : {entry['timestamp']}",
                        )

                    self.request_confirmation(
                        f"Revue documentaire ({decision_str}) pour {rec['tool']}",
                        f"Outil : {rec['tool']}\nAuteur : {actor}\nMotif : {reason}",
                        _on_method_confirm,
                    )
                elif arg.startswith(('stage ', 'preparer-corpus ')):
                    candidate_path = arg.split(maxsplit=1)[1].strip()
                    staged = stage_corpus_file(candidate_path)
                    self.add_panel(
                        1,
                        'Mise à jour du corpus en quarantaine',
                        f'Fichier isolé : {staged}\nValidation humaine hors ligne requise avant remplacement du catalogue actif.',
                    )
                else:
                    raise ValueError('Sous-commande /methods inconnue ; utilisez list, approve, reject ou stage.')
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/investigation' or normalized.startswith('/investigation '):
                arg = normalized[len('/investigation'):].strip()
                action_parts = arg.split(maxsplit=1)
                action = action_parts[0].lower() if action_parts else 'status'
                opening_action = action if action in ('create', 'open') else None
                if opening_action:
                    if len(action_parts) != 2:
                        raise ValueError('Usage : /investigation '+action+' <id> [titre]')
                    arg = action_parts[1]
                self.active_section = 1
                if not arg or arg in ('status', 'statut'):
                    if not self.cases.active_case_id:
                        self.add_panel(1, 'Dossier d’enquête', 'Aucun dossier actif. Utilisez /investigation <id> [titre] pour ouvrir un dossier isolé, ou /investigation list.')
                    else:
                        info = self.cases.status()
                        body = (
                            f"Dossier : {info['case_id']}"
                            + (f" — {info['title']}" if info['title'] else '')
                            + f"\nChemin : {info['path']}\nIndices : {info['indicators_count']} ; commandes : {info['prepared_commands_count']} ; contextes : {info['contexts_count']}"
                            + f"\nJournal : {info['journal_entries_count']} événement(s)"
                        )
                        self.add_panel(1, 'Dossier d’enquête', body)
                elif arg in ('list', 'liste'):
                    items = self.cases.list_cases()
                    if not items:
                        self.add_panel(1, 'Dossiers d’enquête', 'Aucun dossier d’enquête enregistré.')
                    else:
                        lines = [
                            f"{it['case_id']} : {it['indicators_count']} indice(s), {it['prepared_commands_count']} commande(s), {it['journal_entries_count']} événement(s)" + ('' if it.get('structure') == 'valid' else ' — dossier inaccessible : contrôle échoué')
                            for it in items
                        ]
                        self.add_panel(1, 'Dossiers d’enquête', '\n'.join(lines))
                elif arg in ('log', 'journal'):
                    if not self.cases.active_case_id:
                        self.add_notice(1, 'Aucun dossier actif ; ouvrez un dossier avec /investigation <id>.')
                    else:
                        entries = self.cases.read_journal()
                        lines = [
                            f"#{e['seq']} [{e['timestamp']}] {journal_description(e)}"
                            for e in entries
                        ]
                        self.add_panel(1, 'Journal d’enquête horodaté', '\n'.join(lines))
                elif action == 'rename':
                    self.cases.rename_case(action_parts[1] if len(action_parts) > 1 else '')
                    self.add_notice(1, 'Dossier renommé : '+self.cases.status()['title'])
                elif action == 'delete':
                    if len(action_parts) > 1:
                        raise ValueError('Cette action concerne le dossier actif ; aucun identifiant attendu.')
                    if not self.cases.active_case_id:
                        self.add_notice(1, 'Aucun dossier actif.')
                        return
                    deleting_id = self.cases.active_case_id
                    deleting_path = self.cases.status()['path']
                    def _delete_confirmed(decision: ConfirmationDecision) -> None:
                        if not decision.approved:
                            self.add_notice(1, 'Suppression annulée.')
                            return
                        # The confirmation applies to this exact active dossier.
                        if self.cases.active_case_id != deleting_id:
                            self.add_notice(1, 'Dossier actif modifié ; suppression annulée.')
                            return
                        try:
                            self.cases.delete_case()
                        except (OSError, ValueError) as exc:
                            self.add_notice(1, 'Suppression impossible : '+safe_display(exc))
                            return
                        self.case_id = None
                        if isinstance(self.extensions.models, DefaultModelProvider):
                            self.extensions.models.reset_sessions()
                        self.analysis = {'choices': []}
                        self.latest_analysis = self.selected_context = None
                        self.context_enabled = False
                        self.add_notice(1, 'Dossier '+deleting_id+' supprimé et contexte réinitialisé.')
                    self.request_confirmation('Supprimer définitivement le dossier '+deleting_id,
                                              deleting_path+' — tous les résultats seront effacés.',
                                              _delete_confirmed)
                    return
                elif action in ('close', 'fermer', 'archive'):
                    if len(action_parts) > 1:
                        raise ValueError('Cette action concerne le dossier actif ; aucun identifiant attendu.')
                    closed = self.cases.archive_case() if action == 'archive' else self.cases.close_case()
                    self.case_id = None
                    if closed is None:
                        self.add_notice(1, 'Aucun dossier actif.')
                    else:
                        if isinstance(self.extensions.models, DefaultModelProvider):
                            self.extensions.models.reset_sessions()
                        self.analysis = {'choices': []}
                        self.latest_analysis = None
                        self.selected_context = None
                        self.context_enabled = False
                        label = 'archivé' if action == 'archive' else 'fermé'
                        self.add_notice(1, f'Dossier {closed} {label} ; contexte et session isolés réinitialisés.')
                else:
                    parts = arg.split(maxsplit=1)
                    cid = parts[0]
                    title = parts[1] if len(parts) > 1 else None
                    state = self.cases.open_case(cid, title=title, create_only=opening_action == 'create',
                                                 existing_only=opening_action == 'open')
                    self.case_id = self.cases.active_case_id
                    if isinstance(self.extensions.models, DefaultModelProvider):
                        self.extensions.models.reset_sessions()
                    self.analysis = state.get('latest_analysis') or {'choices': []}
                    self.latest_analysis = self.analysis if self.analysis.get('choices') and not self.analysis.get('errors') else None
                    self.selected_context = None
                    self.context_enabled = False
                    info = self.cases.status(cid)
                    self.add_panel(
                        1,
                        'Dossier d’enquête actif',
                        f"Dossier : {info['case_id']}" + (f" — {info['title']}" if info['title'] else '')
                        + f"\nChemin : {info['path']}\nIndices : {info['indicators_count']} ; commandes : {info['prepared_commands_count']} ; contextes : {info['contexts_count']}",
                    )
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/reset':
                self.settings_ui.detach_session()
                if isinstance(self.extensions.models, DefaultModelProvider):
                    self.extensions.models.reset_sessions()
                self.entries[0].clear()
                self.analysis = {'choices': []}
                self.latest_analysis = None
                self.selected_context = None
                self.context_enabled = False
                self.state = UIState.WELCOME
                self.status_notice = 'Session et contexte effacés.'
                return

            if normalized == '/context' or (normalized.startswith('/context ') and normalized != '/context off'):
                if self.provider_manager.mode == 'distant':
                    self.add_notice(2, 'Le contexte structuré reste local ; reformulez manuellement les seuls éléments autorisés.')
                elif self.latest_analysis is None:
                    self.add_notice(2, 'Aucune analyse disponible ; utilisez /analyze TEXTE.')
                elif self.current_engine() is None:
                    self.add_notice(2, 'IA non configurée : aucun contexte ne sera transmis.')
                else:
                    self.selected_context = (
                        context_for_choice(self.latest_analysis, int(normalized.split()[1]))
                        if normalized != '/context' else self.latest_analysis
                    )
                    self.context_enabled = True
                    self.cases.record_context(self.selected_context)
                    msg = (
                        'Contexte sélectionné pour les prochains messages IA. Sources et limites incluses ; '
                        'un contexte identique reste dans l’historique sans copie supplémentaire.\n'
                        f'Budget des messages : {self.context_budget} octets, sans suppression silencieuse.'
                    )
                    if normalized != '/context':
                        msg = safe_display(self.selected_context['selection_limits']) + '\n' + msg
                    self.add_panel(0, 'Contexte IA actif', msg)
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/context off':
                self.context_enabled = False
                self.add_notice(0, 'Ajout du contexte désactivé ; les tours précédents restent dans l’historique jusqu’à /reset.')
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/ai':
                state_body = (
                    ('Moteur distant OpenAI : ' + self.provider_manager.remote.model)
                    if self.provider_manager.mode == 'distant'
                    else (
                        f"Moteur Ollama local configuré : {self.active_model.id} ; disponibilité non vérifiée."
                        if self.active_model is not None else 'IA non configurée.'
                    )
                )
                self.add_panel(2, 'État IA', state_body)
                self.active_section = 2
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/models':
                self.active_section = 2
                try:
                    models = self.extensions.models.list_models() if self.extensions.models else ()
                    lines = ['Modèles annoncés par le serveur local (exécution locale non certifiée) :']
                    for m in models:
                        lines.append('  ' + safe_display(m.id))
                    if not models:
                        lines.append('  Aucun modèle annoncé.')
                    self.add_panel(2, 'Modèles locaux', '\n'.join(lines))
                except (RuntimeErrorLocal, AttributeError) as exc:
                    self.add_panel(2, 'Modèles locaux', 'Liste indisponible : ' + safe_display(exc))
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/tools':
                items = indices_outils.inventory()
                self.active_section = 1
                self.add_panel(
                    1,
                    'Outils — présence locale',
                    '\n'.join(f"{item['id']} : {item['executable_path'] or 'absent'}" for item in items),
                )
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized == '/settings':
                self.active_section = 2
                info = (
                    'Mode : ' + self.provider_manager.mode + ' ; fournisseur distant : '
                    + ('OpenAI / ' + self.provider_manager.remote.model if self.provider_manager.remote else 'non configuré')
                    + ' ; clé : jamais affichée. Configuration en mémoire.'
                )
                self.add_panel(2, 'Paramètres fournisseur IA', info)

                def _on_settings_choice(choice_raw: str) -> None:
                    choice = choice_raw.strip().lower()
                    choice = {'configurer': 'configure', 'activer': 'activate', 'retour': 'back'}.get(choice, choice)
                    if choice == 'local':
                        self.provider_manager.select_local()
                        self.add_notice(2, 'Mode local activé.')
                    elif choice == 'configure':
                        holder: dict[str, str] = {}
                        def _ask_provider(prov: str) -> None:
                            holder['provider'] = prov.strip().lower()
                        def _ask_model(mod_name: str) -> None:
                            self.provider_manager.configure_remote(holder['provider'], mod_name.strip(), self.timeout)
                            self.provider_manager.select_local()
                            self.add_notice(2, 'Configuration enregistrée en mémoire ; mode local actif. Clé via OPENAI_API_KEY.')
                        self._queue_prompts([
                            ('Fournisseur (openai) : ', _ask_provider),
                            ('Modèle distant : ', _ask_model),
                        ])
                    elif choice == 'activate':
                        self.provider_manager.select_remote()
                        self.add_notice(2, 'Mode distant activé ; chaque envoi exige une confirmation.')
                    elif choice != 'back':
                        self.add_notice(2, 'Choix inconnu.')

                self._queue_prompts([('Choix : local / configure / activate / back : ', _on_settings_choice)])
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            if normalized.startswith('/prepare '):
                number = int(normalized.split(maxsplit=1)[1])
                self.active_section = 1
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                self._start_prepare_flow(number)
                return

            if normalized.startswith('/target '):
                number = int(normalized.split(maxsplit=1)[1])
                self.active_section = 1
                if self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                self._start_target_flow(number)
                return

            # Mode distant avec confirmation explicite
            if normalized and self.provider_manager.mode == 'distant' and not normalized.startswith(('/analyze ', '/indicator ')):
                if normalized.startswith('/'):
                    self.set_error('unknown_command', 'Commande inconnue ; /help pour les commandes disponibles.')
                    return
                self._start_remote_turn_flow(text)
                return

            # Analyse d'indices et/ou tour conversationnel
            if normalized.startswith('/analyze ') or normalized.startswith('/indicator ') or (
                normalized and (not normalized.startswith('/') or os.path.isfile(normalized))
            ):
                explicit = normalized.startswith(('/analyze ', '/indicator '))
                if explicit:
                    self.latest_analysis = None
                    self.context_enabled = False
                new_analysis = None
                if (
                    explicit
                    or self.current_engine() is None
                    or indices_outils.extract(normalized)
                    or normalized.startswith(('/', './', '../', '~/'))
                ):
                    if normalized.startswith('/indicator '):
                        _, kind, value = normalized.split(maxsplit=2)
                        new_analysis = analyse(value, kind=kind)
                    else:
                        value = normalized[len('/analyze '):] if normalized.startswith('/analyze ') else text
                        new_analysis = analyse(value)
                if new_analysis is not None:
                    self.analysis = new_analysis
                    self.latest_analysis = self.analysis if not self.analysis.get('errors') else None
                    self.context_enabled = False
                    self.cases.record_analysis(self.analysis)
                    rendered = self._capture_renderer(render_analysis, self.analysis)
                    self.add_panel(1, 'Analyse et recommandations', rendered + '\n\nAnalyse non transmise au modèle. /context permet de la sélectionner.')
                    if explicit or self.current_engine() is None:
                        self.active_section = 1
                        self.status_notice = 'Analyse locale disponible dans Enquête.'
                if self.current_engine() is not None and not explicit:
                    await self.run_conversation_turn(text, on_render=on_render)
                elif self.state == UIState.WELCOME:
                    self.state = UIState.CONVERSATION
                return

            self.set_error('unknown_command', 'Commande inconnue ; /help pour les commandes disponibles.')
        except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
            self.analysis = {'choices': []}
            self.latest_analysis = None
            self.context_enabled = False
            self.set_error('operation_refused', 'Opération refusée : ' + safe_display(exc))

    @staticmethod
    def _capture_renderer(renderer: Callable[[dict], None], value: dict) -> str:
        from contextlib import redirect_stdout
        from io import StringIO
        buf = StringIO()
        with redirect_stdout(buf):
            renderer(value)
        return buf.getvalue().rstrip()

    def _finish_preparation(self, result: dict) -> None:
        rendered = self._capture_renderer(render_preparation_readable, result)
        self.add_panel(
            1,
            'Commande préparée et avertissements',
            rendered + '\n\nRésultat non transmis au modèle. /context permet de le sélectionner.',
        )
        self.analysis = dict(self.analysis, last_preparation=result)
        self.latest_analysis = self.analysis
        self.context_enabled = False
        self.cases.record_preparation(result)
        self.status_notice = 'Préparation terminée (aucune exécution automatique).'

    def _start_prepare_flow(self, number: int) -> None:
        import commandes
        from parcours import prepare_selected, refusal
        choices = self.analysis.get('choices', [])
        if number < 1 or number > len(choices):
            self._finish_preparation(refusal('invalid_selection', 'Faire /analyze puis choisir un numéro affiché.'))
            return
        tool_name = choices[number - 1]['recommendation']['tool']
        if tool_name not in commandes.EXACT_VERSIONS:
            self._finish_preparation(refusal('unsupported_tool', 'Aucune règle de préparation pour cet outil; recommandation informative seulement.'))
            return
        indicator = choices[number - 1]['indicator']
        kind, target = indicator['type'], indicator['normalized']
        if kind == 'file':
            holder: dict[str, object] = {}
            def _on_root(root_val: str) -> None:
                root = root_val.strip()
                if not root:
                    self._finish_preparation(refusal('cancelled', 'Préparation annulée.'))
                    return
                holder['root'] = root
                if tool_name == 'strings':
                    def _on_min_len(min_val: str) -> None:
                        import re
                        val = min_val.strip()
                        if not re.fullmatch(r'[0-9]{1,2}', val):
                            self._finish_preparation(refusal('unsafe_option', 'Longueur minimale invalide.'))
                            return
                        res = prepare_selected(
                            self.analysis,
                            number,
                            parameters={'min_length': int(val)},
                            constraints={'file_roots': [str(holder['root'])]},
                        )
                        self._finish_preparation(res)
                    self._queue_prompts([('Longueur minimale des chaînes (entier 4 à 64) : ', _on_min_len)])
                else:
                    res = prepare_selected(
                        self.analysis,
                        number,
                        parameters={},
                        constraints={'file_roots': [root]},
                    )
                    self._finish_preparation(res)
            self._queue_prompts([('Racine de travail autorisée (chemin absolu, vide = annuler) : ', _on_root)])
        elif kind in ('domain', 'ip'):
            holder_net: dict[str, str] = {}
            def _on_resolver(res_val: str) -> None:
                holder_net['resolver'] = res_val.strip()
                if kind == 'domain':
                    def _on_rtype(rt_val: str) -> None:
                        holder_net['record_type'] = rt_val.strip().upper()
                        _confirm_scope()
                    self._queue_prompts([('Type DNS (A, AAAA, MX, TXT) : ', _on_rtype)])
                else:
                    _confirm_scope()

            def _confirm_scope() -> None:
                resolver = holder_net['resolver']
                details = f'Cible : {target} ; résolveur : {resolver}. Requête active si exécutée manuellement.\nConfirmer ce périmètre pour la préparation seulement ?'
                def _on_decision(dec: ConfirmationDecision) -> None:
                    if not dec.approved:
                        self._finish_preparation(refusal('network_forbidden', 'Périmètre réseau non confirmé.'))
                        return
                    params = {'resolver': resolver}
                    if 'record_type' in holder_net:
                        params['record_type'] = holder_net['record_type']
                    constraints = {
                        'allow_network': True,
                        'authorized_targets': [target],
                        'authorized_resolvers': [resolver],
                    }
                    res = prepare_selected(self.analysis, number, parameters=params, constraints=constraints)
                    self._finish_preparation(res)
                self.request_confirmation('Périmètre réseau DNS', details, _on_decision)

            self._queue_prompts([('Résolveur autorisé (IP explicite) : ', _on_resolver)])
        else:
            self._finish_preparation(
                refusal('unsupported_indicator', 'Pour URL/e-mail, examiner la cible dérivée avec /target N puis choisir explicitement ce nouvel indice.')
            )

    def _start_target_flow(self, number: int) -> None:
        from urllib.parse import urlsplit
        import indices_outils
        from parcours import analyse, render_analysis
        self.context_enabled = False
        self.latest_analysis = None
        choices = self.analysis.get('choices', [])
        if number < 1 or number > len(choices):
            raise ValueError('Numéro de proposition invalide.')
        indicator = choices[number - 1]['indicator']
        if indicator['validation'] != 'valid' or indicator['type'] not in ('email', 'url'):
            raise ValueError('Choisir une proposition pour URL ou e-mail valide.')
        value = indicator['normalized']
        host = value.rsplit('@', 1)[1] if indicator['type'] == 'email' else urlsplit(value).hostname
        details = (
            f"Indice original : {indicator['original']}\nDomaine/hôte extrait proposé : {host}\n"
            'Ce choix ne constitue aucune autorisation réseau ni préparation de commande.'
        )
        def _on_decision(dec: ConfirmationDecision) -> None:
            if not dec.approved:
                self.add_notice(1, 'Transformation annulée.')
            else:
                kind = 'ip' if indices_outils.classify(host, 'ip')['validation'] == 'valid' else 'domain'
                self.analysis = analyse(host, kind=kind)
            self.latest_analysis = self.analysis if not self.analysis.get('errors') else None
            self.cases.record_analysis(self.analysis)
            rendered = self._capture_renderer(render_analysis, self.analysis)
            self.add_panel(1, 'Analyse et recommandations', rendered + '\n\nAnalyse non transmise au modèle. /context permet de la sélectionner.')

        self.request_confirmation('Sélectionner cet indice dérivé', details, _on_decision)

    def _start_remote_turn_flow(self, text: str) -> None:
        import json
        from conversation import RuntimeIncomplete
        self.active_section = 0
        if self.state == UIState.WELCOME:
            self.state = UIState.CONVERSATION
        info = (
            f'Moteur : OpenAI / {self.provider_manager.remote.model}. Aucun historique ni fichier joint automatiquement.\n'
            'Vérifiez les secrets et les données d’enquête ; une demande confirmée peut être facturée.'
        )
        self.add_panel(0, 'Préparation d’envoi distant', info)

        def _after_text_choice(final_text: str) -> None:
            if not final_text:
                self.add_notice(0, 'Transmission annulée : texte vide.')
                return
            try:
                payload = self.provider_manager.remote.payload(final_text)
            except RuntimeErrorLocal as exc:
                self.set_error('remote_error', 'Erreur IA : ' + safe_display(exc), section=0)
                return
            preview = 'Corps JSON destiné à api.openai.com :\n' + safe_display(json.dumps(payload, ensure_ascii=True, indent=2))

            def _on_confirm(dec: ConfirmationDecision) -> None:
                if not dec.approved:
                    self.add_notice(0, 'Transmission annulée.')
                    return
                try:
                    answer = self.provider_manager.remote.chat(payload['messages'], consent=True)
                    self.add_panel(0, 'Réponse distante (non vérifiée)', answer + '\n\nSources et faits à contrôler.')
                except RuntimeIncomplete as exc:
                    self.add_panel(0, 'Texte partiel distant (non vérifié)', safe_display(exc) + '\n' + safe_display(exc.partial))
                except RuntimeErrorLocal as exc:
                    self.set_error('remote_error', 'Erreur IA : ' + safe_display(exc), section=0)

            self.request_confirmation('Confirmer cet envoi distant potentiellement payant', preview, _on_confirm)

        def _on_action(act_raw: str) -> None:
            action = act_raw.strip().lower()
            if action not in ('', 'r'):
                self.add_notice(0, 'Transmission annulée.')
                return
            if action == 'r':
                self._queue_prompts([('Texte expurgé : ', lambda rep: _after_text_choice(rep.strip()))])
            else:
                _after_text_choice(text)

        self._queue_prompts([('Conserver (entrée), remplacer (r), annuler (a) : ', _on_action)])

    # ========================================================================
    # Rendu complet de l'écran selon la taille du terminal
    # ========================================================================

    def render_viewport(self, width: int, height: int) -> list[str]:
        """Construit les lignes de l'écran pour un terminal de dimensions (width, height)."""
        width = max(1, width)
        height = max(1, height)

        # L'éditeur reste actif pendant UIState.RUNNING afin de permettre la saisie en cours de génération
        input_active = self.state != UIState.CLOSING and self.settings_ui.panel is None

        # Cas d'un terminal très étroit ou très bas : mode dégradé lisible sans perte de saisie
        if width < MIN_TERMINAL_WIDTH or height < MIN_TERMINAL_HEIGHT:
            tiny_lines: list[str] = [
                clip_to_width(f'UCHAMBUZI Focus [{self.profile.name}]', width),
                clip_to_width(f'État: {self.state.value} | {self.SECTIONS[self.active_section]}', width),
                clip_to_width('Écran étroit : agrandir svp', width),
            ]
            editor_all = list(self.extensions.editor.render_lines(width, active=input_active)) or ['uchambuzi> ']
            max_tiny_ed = max(1, min(len(editor_all), max(1, height // 3)))
            cursor_row = next((i for i, line in enumerate(editor_all) if '█' in line), len(editor_all) - 1)
            start = max(0, min(cursor_row, len(editor_all) - max_tiny_ed))
            vis_ed = editor_all[start:start + max_tiny_ed]
            body = self._render_active_region_lines(width, height=max(1, height-4))
            avail = max(1, height - len(tiny_lines) - len(vis_ed) - 1)
            tiny_lines.extend(body[:avail] if self.settings_ui.panel else body[-avail:])
            while len(tiny_lines) < max(0, height - len(vis_ed) - 1):
                tiny_lines.append('')
            for ed_line in vis_ed:
                if len(tiny_lines) < max(0, height - 1):
                    tiny_lines.append(clip_to_width(ed_line, width))
            if height >= 1:
                tiny_lines.append(clip_to_width(self.status_notice, width))
            return [clip_to_width(self.settings_ui.style.text(line), width) for line in tiny_lines[:height]]

        lines: list[str] = []

        # 1. Barre d'en-tête : Identité, Mode/Scénario, Modèle, Dossier, État
        scenario_part = f'/{self.scenario.id}' if self.scenario else ''
        model_label = self.active_model.id if self.active_model else 'sans-IA'
        if self.settings_ui.use_ai and self.active_model and not self.settings_ui.ai.model_id:
            model_label += ' (non vérifié)'
        if self.provider_manager.mode == 'distant' and self.provider_manager.remote:
            model_label = f'distant:{self.provider_manager.remote.model}'
        case_part = f' | Dossier: {self.case_id}' if self.case_id else ''
        header_top = f' UCHAMBUZI Focus — Mode: {self.profile.name}{scenario_part} | IA: {model_label}{case_part} | État: {self.state.value.upper()}'
        lines.append(clip_to_width(header_top, width - 1).ljust(width - 1))

        # 2. Barre d'onglets / régions défilantes
        tabs = []
        for idx, name in enumerate(self.SECTIONS):
            count = len(self.entries[idx])
            badge = f' ({count})' if count and idx != 2 else ''
            if idx == self.active_section:
                tabs.append(f'[{idx + 1}:{name}{badge} *]')
            else:
                tabs.append(f' {idx + 1}:{name}{badge} ')
        tab_bar = ' '.join(tabs) + '  │ Tab: région │ PgUp/PgDn: défiler │ Ctrl+P: mode │ Ctrl+D: quitter'
        lines.append(clip_to_width(tab_bar, width - 1).ljust(width - 1))
        lines.append('─' * (width - 1))

        # 3. Calcul préalable des lignes de la zone de saisie (multiligne + défilement interne)
        if self._active_prompt is not None:
            prompt_label, _ = self._active_prompt
            buf_text = terminal_display(self.extensions.editor.buffer)
            raw_editor_lines = [f'? {prompt_label}{buf_text}█']
        elif self.state == UIState.CONFIRMATION:
            buf_text = terminal_display(self.extensions.editor.buffer)
            raw_editor_lines = [f'[Validation oui/non]> {buf_text}█']
        else:
            raw_editor_lines = list(self.extensions.editor.render_lines(width - 1, active=input_active))
            if not raw_editor_lines:
                raw_editor_lines = ['uchambuzi> ']

        # Hauteur dynamique allouée à l'éditeur en préservant une zone minimale de conversation
        min_body_rows = min(5, max(2, height // 6))
        max_editor_rows = max(1, height - len(lines) - min_body_rows - 2)
        total_editor_lines = len(raw_editor_lines)
        visible_editor_rows = min(total_editor_lines, max_editor_rows)

        # Détermination de la ligne visuelle portant le curseur pour le défilement interne de l'éditeur
        cursor_vis_row = None
        for idx_line, ed_line in enumerate(raw_editor_lines):
            if '█' in ed_line:
                cursor_vis_row = idx_line
                break
        if cursor_vis_row is None:
            logical_row = getattr(self.extensions.editor, 'cursor_row', 0)
            cursor_vis_row = min(max(0, int(logical_row)), max(0, total_editor_lines - 1))

        if total_editor_lines <= visible_editor_rows:
            self.editor_scroll_offset = 0
        else:
            if cursor_vis_row < self.editor_scroll_offset:
                self.editor_scroll_offset = cursor_vis_row
            elif cursor_vis_row >= self.editor_scroll_offset + visible_editor_rows:
                self.editor_scroll_offset = cursor_vis_row - visible_editor_rows + 1
            max_ed_offset = max(0, total_editor_lines - visible_editor_rows)
            self.editor_scroll_offset = max(0, min(self.editor_scroll_offset, max_ed_offset))

        ed_start = self.editor_scroll_offset
        ed_end = ed_start + visible_editor_rows
        visible_editor_lines = raw_editor_lines[ed_start:ed_end]

        # 4. Zone centrale défilante (accueil, conversation, enquête, aide ou sélecteur)
        footer_rows = 1 + len(visible_editor_lines) + 1  # séparateur + lignes éditeur + barre d'état
        body_height = max(1, height - len(lines) - footer_rows)
        sec = self.active_section
        previous_positions = self._region_positions.get(sec, [])
        anchor = None
        if 0 < self.scroll_offsets[sec] <= len(previous_positions)-self._region_heights.get(sec,body_height) and previous_positions and self.settings_ui.panel is None:
            old_start = max(0, len(previous_positions) - self._region_heights.get(sec, body_height) - self.scroll_offsets[sec])
            anchor = previous_positions[min(old_start, len(previous_positions)-1)]
        self._requested_source_anchor = anchor
        region_lines = self._render_active_region_lines(width - 1, height=body_height)

        total_lines = len(region_lines)
        sec = self.active_section
        positions = self._region_positions.get(sec, [])
        if anchor is not None and positions:
            same_line = [i for i, value in enumerate(positions) if value[:2] == anchor[:2]]
            if same_line:
                before = [i for i in same_line if positions[i][2] <= anchor[2]]
                anchor_start = before[-1] if before else same_line[0]
                self.scroll_offsets[sec] = max(1, total_lines - body_height - anchor_start)
        self._last_region_line_counts[sec] = total_lines
        self._region_heights[sec] = body_height

        max_offset = max(0, total_lines - body_height)
        offset = min(self.scroll_offsets[sec], max_offset)
        self.scroll_offsets[sec] = offset

        end = max(0, total_lines - offset)
        start = max(0, end - body_height)
        visible = region_lines[start:end]
        for row in visible:
            lines.append(clip_to_width(row, width - 1))
        while len(lines) < height - footer_rows:
            lines.append('')

        # 5. Séparateur bas + indicateurs de défilement (conversation et éditeur)
        info_parts: list[str] = []
        if offset > 0:
            info_parts.append(f'↕ défilement +{offset}')
        if total_editor_lines > visible_editor_rows:
            info_parts.append(f'↕ éditeur L{ed_start + 1}-{ed_end}/{total_editor_lines}')
        scroll_info = (' ' + ' | '.join(info_parts) + ' ') if info_parts else ''
        sep_len = max(0, (width - 1) - display_width(scroll_info))
        lines.append(('─' * sep_len) + scroll_info)

        # 6. Zone de saisie multiligne
        for ed_line in visible_editor_lines:
            lines.append(clip_to_width(ed_line, width - 1))

        # 7. Barre d'état
        lines.append(clip_to_width(' ' + self.status_notice, width - 1))
        frame = self.settings_ui.animations.frame(unicode=self.settings_ui.style.unicode)
        if frame and lines:
            lines[-1] = clip_to_width(' ' + self.status_notice + ' | ' + frame, width-1)
        return [clip_to_width(self.settings_ui.style.text(line), width-1) for line in lines[:height]]

    def _render_active_region_lines(self, width: int, height: int = 20) -> list[str]:
        if self.settings_ui.panel is not None:
            if not isinstance(self.extensions.selector, DefaultSelector):
                title = 'Spécialité Focus (/mode)' if self.selector_kind == 'mode' else self.settings_ui.panel.title
                return list(self.extensions.selector.render_selector(title, self.selector_items, self.selector_index, width))[:height]
            return self.settings_ui.render_panel(width, height)
        if self.state == UIState.MODE_SWITCH:
            title = 'Spécialité Focus (/mode)' if self.selector_kind == 'mode' else f'Scénario pour {self.profile.name} (/scenario)'
            return list(self.extensions.selector.render_selector(title, self.selector_items, self.selector_index, width))

        # État d'accueil lorsque la conversation est vide sur l'onglet Conversation
        if self.active_section == 0 and not self.entries[0]:
            out: list[str] = []
            for logo_line in self.extensions.logo.render_logo(width, height):
                out.append(clip_to_width(logo_line, width))
            out.append('')
            ai_desc = (
                f'locale — {self.active_model.id}' + (' (disponibilité non vérifiée)' if self.settings_ui.use_ai and not self.settings_ui.ai.model_id else '')
                if self.active_model is not None
                else 'non configurée (fonctions locales actives ; --model NOM pour l’IA)'
            )
            welcome_body = (
                f'Spécialité active : {self.profile.name} — {self.profile.instructions}\n'
                f'IA : {ai_desc}\n'
                'Mode : préparation bornée, aucune exécution automatique de commandes.\n'
                'Saisissez une question, un indice (ex. /analyze example.org) ou /mode pour changer de spécialité.'
            )
            out.extend(self.extensions.markdown.render_panel('Session UCHAMBUZI Focus', welcome_body, width))
            return out

        section_entries = self.entries[self.active_section]
        if not section_entries:
            return ['  (Aucun élément dans cette région pour le moment. Tapez /analyze example.org ou /help.)']

        # Ne mettre en page que la queue necessaire au viewport et au defilement.
        # Les entrees originales restent intactes pour l'historique et les sessions.
        blocks = []
        row_count = 0
        wanted = max(1,height) + self.scroll_offsets[self.active_section] + 32
        requested = getattr(self, '_requested_source_anchor', None)
        anchor_seen = requested is None
        for entry in reversed(section_entries):
            rendered, mapped = [], []
            if entry.kind == 'message' and entry.message is not None:
                cache_key = (entry.message, width, id(self.extensions.markdown), entry.complete)
                cached = self._render_cache.get(cache_key) if not entry.streaming else None
                if cached is None:
                    msg_lines = tuple(self.extensions.markdown.render_message(entry.message, width, streaming=entry.streaming))
                    msg_positions = []
                    if hasattr(self.extensions.markdown, 'layout_message'):
                        layout = self.extensions.markdown.layout_message(entry.message, max(1,width-2), streaming=entry.streaming)
                        msg_positions = [(entry.message.id, -1, 0)] + [(entry.message.id, line.source_line, line.source_column) for line in layout]
                    cached = msg_lines, tuple(msg_positions)
                    if not entry.streaming and len(entry.message.text) <= 65536:
                        if len(self._render_cache) >= 2048:
                            self._render_cache.pop(next(iter(self._render_cache)))
                        self._render_cache[cache_key] = cached
                rendered.extend(cached[0])
                mapped.extend(cached[1])
                anchor_seen = anchor_seen or (requested is not None and requested[0] == entry.message.id)
            elif entry.kind in ('panel', 'error'):
                rendered.extend(self.extensions.markdown.render_panel(entry.title or 'Erreur', entry.body, width))
            else:
                rendered.extend('  '+line for line in wrap_line('• '+entry.body, max(1,width-2)))
            while len(mapped) < len(rendered):
                mapped.append((str(id(entry)),len(mapped),0))
            anchor_seen = anchor_seen or (requested is not None and requested[0] == str(id(entry)))
            rendered.append('')
            mapped.append((str(id(entry)),-2,0))
            blocks.append((rendered,mapped))
            row_count += len(rendered)
            if row_count >= wanted and anchor_seen:
                break
        rendered_lines, positions = [], []
        for rendered, mapped in reversed(blocks):
            rendered_lines.extend(rendered)
            positions.extend(mapped)
        self._region_positions[self.active_section] = positions
        return rendered_lines


# ============================================================================
# Boucle événementielle curses plein écran et restauration stricte du terminal
# ============================================================================

def run_focus_tui(
    *,
    model: str | None = None,
    port: int = 11434,
    timeout: float = DEFAULT_TIMEOUT,
    runtime=None,
    context_budget: int = DEFAULT_CONTEXT_BUDGET,
    case_id: str | None = None,
    extensions: FocusExtensions | None = None,
    engine: ConversationEngine | None = None,
) -> int | None:
    """Lance la TUI conversationnelle UCHAMBUZI Focus avec garantie de restauration du terminal."""
    if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get('TERM') in ('', 'dumb'):
        print('TUI indisponible sur ce terminal ; retour au terminal classique.', file=sys.stderr)
        return None

    try:
        import curses
        import select
        import termios
    except ImportError:
        print('TUI indisponible ; retour au terminal classique.', file=sys.stderr)
        return None

    # Validation préalable des paramètres avant d'entrer en mode curses
    try:
        controller = FocusTUIController(
            model=model,
            port=port,
            timeout=timeout,
            runtime=runtime,
            context_budget=context_budget,
            case_id=case_id,
            extensions=extensions,
            engine=engine,
        )
    except ValueError as exc:
        print('Configuration invalide : ' + safe_display(exc), file=sys.stderr)
        return 2

    saved_termios = None
    try:
        saved_termios = termios.tcgetattr(sys.stdin.fileno())
    except (termios.error, OSError, ValueError):
        saved_termios = None

    def _restore_terminal() -> None:
        try:
            if not curses.isendwin():
                curses.nocbreak()
                curses.echo()
                curses.endwin()
        except Exception:
            pass
        if saved_termios is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved_termios)
            except Exception:
                pass

    def _curses_main(screen) -> int:
        curses.raw()
        curses.noecho()
        curses.nonl()
        terminal_keys = TerminalKeys()
        bracketed_enabled = False
        try:
            os.write(sys.stdout.fileno(), b'\x1b[?2004h')
            bracketed_enabled = True
        except OSError:
            pass
        if not bracketed_enabled:
            try:
                os.write(sys.stdout.fileno(), b'\x1b[?2004h')
                bracketed_enabled = True
            except OSError:
                pass
        try:
            curses.set_escdelay(25)
        except (AttributeError, curses.error):
            pass
        screen.keypad(True)
        screen.timeout(15)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        try:
            # curses.wrapper starts colors even when NO_COLOR is requested.
            # Pair zero must retain the terminal defaults for monochrome output.
            curses.use_default_colors()
        except curses.error:
            pass
        from focus_theme import TerminalStyle
        color_config = None
        color_ready = False
        last_animation_active = False

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        previous_viewport: list[str] = []
        last_size: tuple[int, int] = (0, 0)

        def draw() -> None:
            nonlocal previous_viewport, last_size, color_config, color_ready, last_animation_active
            try:
                height, width = screen.getmaxyx()
                style = TerminalStyle.detect(controller.settings_ui.values, colors=getattr(curses, 'COLORS', 0))
                # COLORS becomes meaningful only after start_color.
                if curses.has_colors() and not getattr(curses, 'COLORS', 0):
                    try:
                        curses.start_color()
                    except curses.error:
                        pass
                    style = TerminalStyle.detect(controller.settings_ui.values, colors=getattr(curses, 'COLORS', 0))
                if style != color_config:
                    color_config = style
                    effective_style, color_ready = style.configure_curses(curses)
                    controller.settings_ui.style = effective_style
                    try:
                        screen.bkgd(' ', curses.color_pair(2) if color_ready else 0)
                    except curses.error:
                        color_ready = False
                    previous_viewport = []
                viewport = controller.render_viewport(width, height)
                last_animation_active = controller.settings_ui.animations.active
                size_changed = (height, width) != last_size or len(viewport) != len(previous_viewport)
                if size_changed:
                    screen.erase()
                    last_size = (height, width)
                for row_idx, line in enumerate(viewport):
                    if row_idx >= height:
                        break
                    if not size_changed and row_idx < len(previous_viewport) and previous_viewport[row_idx] == line:
                        continue
                    attr = 0
                    if color_ready:
                        if row_idx == 0:
                            attr = curses.color_pair(1) | curses.A_BOLD
                        elif line.startswith(('▸ ', '> ')):
                            attr = curses.color_pair(1) | curses.A_REVERSE
                        elif line.startswith(('┌ Error', '┌ Erreur')):
                            attr = curses.color_pair(3) | curses.A_BOLD
                    try:
                        screen.move(row_idx, 0)
                        screen.clrtoeol()
                        screen.addstr(row_idx, 0, terminal_display(line), attr)
                    except curses.error:
                        pass
                previous_viewport = list(viewport)
                screen.refresh()
            except curses.error:
                pass

        try:
            draw()

            def _peek_next_wch():
                screen.nodelay(True)
                try:
                    return screen.get_wch()
                except curses.error:
                    return None
                finally:
                    screen.timeout(15)

            paste_keypad = False

            def _dispatch_key(key: int | str, *, page_step: int = 18):
                nonlocal paste_keypad
                submitted = controller.handle_key(key, page_step=page_step)
                if paste_keypad != controller._bracketed_paste:
                    paste_keypad = controller._bracketed_paste
                    # Preserve literal escape sequences inside bracketed paste.
                    screen.keypad(not paste_keypad)
                return submitted

            def _normalize_raw_keys(raw_key: int | str) -> list[int | str]:
                result = []
                for key in terminal_keys.feed(raw_key):
                    # Keep the existing unbracketed multiline paste convention.
                    if (
                        key in ('\n', '\r')
                        and not controller._bracketed_paste
                        and controller.state not in (UIState.CONFIRMATION, UIState.MODE_SWITCH)
                        and controller._active_prompt is None
                        and controller.extensions.editor.buffer
                        and not controller.extensions.editor.buffer.startswith('/')
                    ):
                        next_key = _peek_next_wch()
                        if next_key is not None:
                            try:
                                curses.unget_wch(next_key)
                            except (curses.error, AttributeError, ValueError):
                                pass
                            key = '\x1b\n'
                    result.append(key)
                return result

            while controller.state != UIState.CLOSING:
                active_task = controller._running_task
                if active_task is not None and active_task.done():
                    try:
                        active_task.result()
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        controller.set_error('internal_error', safe_display(exc))
                    if controller._running_task is active_task:
                        controller._running_task = None
                    draw()

                try:
                    key = screen.get_wch()
                except curses.error:
                    expired = terminal_keys.flush()
                    for expired_key in expired:
                        _dispatch_key(expired_key)
                    had_tasks = bool(controller.settings_ui.tasks)
                    if controller.settings_ui.tasks or (controller._running_task is not None and not controller._running_task.done()):
                        loop.run_until_complete(asyncio.sleep(0.01))
                    if expired or had_tasks or controller.settings_ui.animations.active or last_animation_active:
                        draw()
                    continue

                if key == curses.KEY_RESIZE:
                    try:
                        curses.update_lines_cols()
                    except AttributeError:
                        pass
                    last_size = (0, 0)
                    draw()
                    continue

                height, _ = screen.getmaxyx()
                submitted = None
                for normalized_key in _normalize_raw_keys(key):
                    value = _dispatch_key(normalized_key, page_step=max(1, height - 6))
                    if value is not None:
                        submitted = value

                # Regroupement des frappes/collages immédiatement disponibles dans le tampon curses avant redessin
                burst_count = 0
                while (
                    submitted is None
                    and controller.state != UIState.CLOSING
                    and burst_count < 64
                ):
                    next_raw = _peek_next_wch()
                    if next_raw is None:
                        break
                    if next_raw == curses.KEY_RESIZE:
                        try:
                            curses.update_lines_cols()
                        except AttributeError:
                            pass
                        last_size = (0, 0)
                        break
                    height, _ = screen.getmaxyx()
                    for next_norm in _normalize_raw_keys(next_raw):
                        value = _dispatch_key(next_norm, page_step=max(1, height - 6))
                        if value is not None:
                            submitted = value
                    burst_count += 1

                if submitted is not None:
                    controller._running_task = loop.create_task(controller.submit_input(submitted, on_render=draw))
                    loop.run_until_complete(asyncio.sleep(0.005))
                elif controller._running_task is not None or controller.settings_ui.tasks:
                    loop.run_until_complete(asyncio.sleep(0.005))
                draw()

            return 0
        finally:
            if bracketed_enabled:
                try:
                    os.write(sys.stdout.fileno(), b'\x1b[?2004l')
                except OSError:
                    pass
            if controller._running_task is not None and not controller._running_task.done():
                controller._running_task.cancel()
                try:
                    loop.run_until_complete(controller._running_task)
                except (asyncio.CancelledError, Exception):
                    pass
            for task in tuple(controller.settings_ui.tasks):
                task.cancel()
            if controller.settings_ui.tasks:
                loop.run_until_complete(asyncio.gather(*controller.settings_ui.tasks, return_exceptions=True))
            loop.close()

    try:
        return curses.wrapper(_curses_main)
    except (curses.error, OSError) as exc:
        _restore_terminal()
        print('TUI interrompue : ' + safe_display(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        _restore_terminal()
        print('TUI interrompue.', file=sys.stderr)
        return 130
    finally:
        _restore_terminal()
