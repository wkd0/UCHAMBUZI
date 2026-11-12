# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_render.py
# Role          : Rendu conversationnel, streaming Markdown, transcript et console reflow
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Présentation uniquement : aucune exécution et aucune pensée simulée."""
from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import io
import re

from rich.console import Console
from rich.markdown import Markdown, Heading, CodeBlock
from rich.syntax import Syntax
from rich.rule import Rule
from rich.padding import Padding
from rich.text import Text
from rich.theme import Theme

from conversation import safe_display


MARKDOWN_THEME = Theme({
    'markdown.h1': 'bold #38BDF8',
    'markdown.h2': 'bold #38BDF8',
    'markdown.h3': 'bold #38BDF8',
    'markdown.code': '#E85D26',
    'markdown.link': 'underline #38BDF8',
    'markdown.link_url': '#94A3B8',
    'markdown.item.bullet': '#38BDF8',
    'markdown.block_quote': 'italic #94A3B8',
})


class TranscriptHeading(Heading):
    def __rich_console__(self, console, options):
        self.text.justify = 'left'
        yield self.text


class TranscriptCodeBlock(CodeBlock):
    def __rich_console__(self, console, options):
        yield Syntax(str(self.text).strip('\n'), self.lexer_name, theme=self.theme,
                     word_wrap=True, padding=0, background_color='default')


class TranscriptMarkdown(Markdown):
    elements = {**Markdown.elements, 'heading_open': TranscriptHeading,
                'fence': TranscriptCodeBlock, 'code_block': TranscriptCodeBlock}


def markdown(text):
    return Padding(TranscriptMarkdown(safe_display(text), code_theme='monokai', justify='left'), (0, 2))


class MarkdownStream:
    """Valide des blocs complets sans couper les blocs de code clôturés."""
    def __init__(self):
        self.pending = ''

    def feed(self, chunk):
        self.pending += chunk
        blocks = []
        fence = None
        offset = 0
        boundary = 0
        for line in self.pending.splitlines(keepends=True):
            match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
            if match:
                marker = match.group(1)
                if fence is None:
                    fence = marker
                elif marker[0] == fence[0] and len(marker) >= len(fence) and not match.group(2).strip():
                    fence = None
            offset += len(line)
            if not line.strip() and fence is None and line.endswith('\n'):
                block = self.pending[boundary:offset].strip('\n')
                if block:
                    blocks.append(block)
                boundary = offset
        self.pending = self.pending[boundary:]
        return blocks

    def finish(self):
        pending, self.pending = self.pending, ''
        return pending


def preview_ansi(text, width, height):
    """Aperçu borné au-dessus de l'éditeur ; la réponse complète reste dans le flux."""
    if not text:
        return ''
    if len(text) > 12000:
        text = '… aperçu de la fin du bloc\n' + text[-12000:]
    output = io.StringIO()
    console = Console(file=output, force_terminal=True, color_system='truecolor',
                      width=max(8, width), theme=MARKDOWN_THEME)
    console.print(markdown(text))
    lines = output.getvalue().splitlines()
    limit = max(1, min(8, height // 3))
    if len(lines) > limit:
        lines = ['\x1b[2m  … suite de la réponse en cours\x1b[0m'] + lines[-limit:]
    return '\n'.join(lines) + '\n'


@dataclass(frozen=True)
class OutputRecord:
    title: str
    output: str
    success: bool


class Transcript:
    def __init__(self, console):
        self.console = console
        self.records = []

    def operation(self, title, output, *, success=True):
        record = OutputRecord(safe_display(title), safe_display(output), success)
        self.records.append(record)
        identifier = len(self.records)
        self.console.print(Text(f'• [{identifier}] {record.title}', style='#94D3A2' if success else '#F87171'))
        lines = record.output.splitlines() or ['(aucune sortie)']
        clipped = False
        for index, line in enumerate(lines[:3]):
            preview = Text(line.expandtabs(4), style='#94A3B8')
            width = max(1, self.console.width - 4)
            if preview.cell_len > width:
                preview.truncate(width, overflow='ellipsis')
                clipped = True
            self.console.print(Text('  └ ' if index == 0 else '    ', style='#94A3B8') + preview)
        remaining = len(lines) - 3
        if remaining > 0 or clipped:
            prefix = f'+ {remaining} lignes · ' if remaining > 0 else 'Ligne abrégée · '
            self.console.print(Text(f'    {prefix}/details {identifier} pour développer', style='dim #94A3B8'))
        return identifier

    def details(self, identifier=None):
        if not self.records:
            self.console.print(Text('Aucune sortie à développer.', style='dim'))
            return
        if isinstance(identifier, str) and identifier.strip().lower().startswith('search '):
            query = identifier.strip()[7:].strip()
            if not query:
                self.console.print(Text('Usage : /details search <texte>', style='#FBBF24'))
                return
            count = 0
            for number, item in enumerate(self.records, 1):
                for line_number, line in enumerate(item.output.splitlines(), 1):
                    if query.casefold() in line.casefold():
                        self.console.print(Text(f'[{number}:{line_number}] {line}'))
                        count += 1
                        if count >= 50:
                            self.console.print(Text('Recherche limitée à 50 lignes.', style='dim'))
                            return
            if not count:
                self.console.print(Text('Aucun résultat correspondant.', style='dim'))
            return
        try:
            number = int(identifier) if identifier else len(self.records)
            if number < 1 or number > len(self.records):
                raise ValueError()
        except (ValueError, TypeError):
            self.console.print(Text(f'Choisir /details 1 à {len(self.records)}.', style='#FBBF24'))
            return
        record = self.records[number - 1]
        self.console.print(Text(f'• Détails {number} · {record.title}', style='bold #38BDF8'))
        self.console.print(Padding(Text(record.output or '(aucune sortie)'), (0, 2)))


class ReflowConsole(Console):
    """Conserve les objets de rendu, pas des lignes figées à l'ancienne largeur.

    Le réaffichage ne touche qu'à l'écran visible, une fois rempli par notre flux.
    Le scrollback du terminal et les sorties brutes restent conservés.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._render_history = deque(maxlen=300)
        self._owns_screen = False

    def print(self, *objects, **kwargs):
        self._render_history.append((objects, dict(kwargs)))
        return super().print(*objects, **kwargs)

    def remember_input(self, text):
        self._render_history.append(((Rule(style='#94A3B8'),), {}))
        self._render_history.append(((Text('› ' + safe_display(text), style='bold #38BDF8'),), {}))

    def history_at_width(self, width):
        output = io.StringIO()
        renderer = Console(file=output, width=max(8, width), theme=MARKDOWN_THEME,
                           force_terminal=self.is_terminal, color_system=self.color_system,
                           no_color=self.no_color)
        for objects, kwargs in self._render_history:
            renderer.print(*objects, **kwargs)
        return output.getvalue().splitlines()

    def redraw(self, width, height, reserved, previous_width, previous_height):
        if not self._owns_screen:
            self._owns_screen = len(self.history_at_width(previous_width)) >= previous_height
        if not self._owns_screen:
            return False
        lines = self.history_at_width(width)
        available = max(0, height - reserved)
        visible = lines[-available:] if available else []
        # CSI 2J efface l'écran visible ; CSI 3J (scrollback) est volontairement absent.
        self.file.write('\x1b[H\x1b[2J')
        if visible:
            self.file.write('\n'.join(visible) + '\n')
        self.file.flush()
        return True
