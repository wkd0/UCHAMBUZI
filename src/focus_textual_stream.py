# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_textual_stream.py
# Role          : Markdown progressif et suivi du dialogue Textual
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Rendu du flux sans cadre et défilement interrompu par la lecture manuelle."""
from __future__ import annotations

import re

from rich.markdown import Markdown
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual import events
from textual.containers import VerticalScroll
from textual.widgets import Static
from textual.strip import Strip
from textual.visual import RichVisual


def streaming_markdown(text: str, *, streaming: bool = True) -> str:
    """Ferme les fences dans la copie de rendu, jamais dans la réponse conservée.

    Le curseur appartient au dernier bloc (y compris un bloc de code ouvert).
    Une fence déjà fermée exige une nouvelle ligne pour rester du Markdown valide.
    """
    fence: str | None = None
    last_was_closing = False
    for line in text.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        last_was_closing = False
        if match is None:
            continue
        marker, suffix = match.groups()
        if fence is None:
            if marker[0] == "`" and "`" in suffix:
                continue
            fence = marker
        elif marker[0] == fence[0] and len(marker) >= len(fence) and not suffix.strip():
            fence = None
            last_was_closing = True

    rendered = text
    if streaming:
        # An opening fence with no code yet needs a line break before the cursor.
        last_line = text.split("\n")[-1]
        opening_only = fence is not None and re.match(
            r"^ {0,3}" + re.escape(fence) + r"[^\n]*$", last_line
        )
        rendered += "\n▌" if opening_only else ("\n\n▌" if last_was_closing else "▌")
    if fence is not None:
        rendered += "\n" + fence + "\n"
    return rendered


class TranscriptScroll(VerticalScroll):
    """Suit les réponses jusqu'à ce que l'enquêteur remonte pour relire."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.follow_output = True
        self._follow_pending = False
        self._following = False

    def follow_end(self) -> None:
        """Suit après layout, sans déduire le suivi d'une ancienne hauteur."""
        if self.follow_output and not self._follow_pending:
            self._follow_pending = True
            self.call_after_refresh(self._follow_after_refresh)

    def _follow_after_refresh(self) -> None:
        self._follow_pending = False
        if self.follow_output and self.is_mounted:
            self._following = True
            try:
                # Pas de deuxième callback différé qui pourrait ignorer une molette.
                super().scroll_end(animate=False, immediate=True)
            finally:
                self._following = False

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        if not self._following:
            # Le layout peut borner l'ancienne position au nouveau maximum
            # lorsque le terminal s'élargit : cela reste un suivi du bas.
            if new_value < old_value and new_value < self.max_scroll_y:
                self.follow_output = False

    def scroll_to(self, x: float | None = None, y: float | None = None, **kwargs) -> None:
        """Reprend au bas demandé, jamais au bas imposé par un nouveau layout.

        Molette, PageDown et glissement de scrollbar utilisent cette entrée.
        Les bornages réactifs de Textual lors d'un resize ne passent pas ici.
        """
        if y is not None:
            if y < self.scroll_y:
                self.follow_output = False
            elif y >= self.max_scroll_y:
                self.follow_output = True
        super().scroll_to(x, y, **kwargs)

    def scroll_history(self, direction: int) -> None:
        """Route la molette depuis n'importe quelle zone de l'écran principal."""
        if direction < 0:
            self.follow_output = False
            self.scroll_relative(y=-3, animate=False, immediate=True)
        else:
            self.scroll_relative(y=3, animate=False, immediate=True)
            if self.is_vertical_scroll_end:
                self.follow_output = True
                self.follow_end()

    def _on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.scroll_history(-1)
        event.stop()
        event.prevent_default()

    def _on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.scroll_history(1)
        event.stop()
        event.prevent_default()

    def on_resize(self, event: events.Resize) -> None:
        self.follow_end()


class SelectableRichVisual(RichVisual):
    """Keep Rich layout while supplying Textual's selection coordinates."""

    def render_strips(self, width, height, style, options):
        strips = super().render_strips(width, height, style, options)
        self._widget._selection_lines = [strip.text for strip in strips]
        rendered = []
        for y, strip in enumerate(strips):
            span = options.selection.get_span(y) if options.selection is not None else None
            # Le style transparent par défaut de Textual peut produire la même
            # couleur pour le texte et le fond des rendus Rich sélectionnés.
            selected_style = RichStyle(color="#FFFFFF", bgcolor="#24547B")
            segments = []
            x = 0
            for segment in strip:
                if segment.control:
                    segments.append(segment)
                    continue
                text = segment.text
                end = x + len(text)
                bounds = {x, end}
                if span is not None:
                    start, stop = span
                    stop = end if stop == -1 else stop
                    bounds.update(point for point in (start, stop) if x < point < end)
                points = sorted(bounds)
                for left, right in zip(points, points[1:]):
                    rich_style = segment.style or RichStyle.null()
                    if span is not None and left >= span[0] and (span[1] == -1 or left < span[1]):
                        rich_style += selected_style
                    rich_style += RichStyle(meta={'offset': (left, y)})
                    segments.append(Segment(text[left - x:right - x], rich_style))
                x = end
            rendered.append(Strip(segments, strip.cell_length))
        return rendered


class SelectableStatic(Static):
    """Expose Rich Markdown, panels and tables to native mouse selection."""

    def render(self):
        visual = super().render()
        if isinstance(visual, RichVisual):
            if getattr(self, '_selection_visual_source', None) is not visual:
                self._selection_visual_source = visual
                self._selection_visual = SelectableRichVisual(self, self.content)
            return self._selection_visual
        return visual

    def get_selection(self, selection):
        if isinstance(self.visual, RichVisual):
            text = "\n".join(getattr(self, '_selection_lines', ()))
            return selection.extract(text), "\n"
        return super().get_selection(selection)


class StreamingAnswer(SelectableStatic):
    """Regroupe les fragments, rend du Markdown brut et suit la dernière ligne."""

    def __init__(self) -> None:
        super().__init__()
        self.text = ""
        self._dirty = False
        self._streaming = True
        self._timer = None
        self.display = False

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.04, self.flush)

    def append_text(self, text: str) -> None:
        self.text += text
        self._dirty = True

    def flush(self) -> None:
        if not self._dirty:
            return
        self.display = bool(self.text)
        self.update(Markdown(streaming_markdown(self.text, streaming=self._streaming)))
        self._dirty = False
        for ancestor in self.ancestors:
            if isinstance(ancestor, TranscriptScroll):
                ancestor.follow_end()
                break

    def finish(self) -> None:
        """Supprime le curseur sur succès, interruption ou erreur."""
        self._streaming = False
        self._dirty = True
        self.flush()
        if self._timer is not None:
            self._timer.stop()

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()
