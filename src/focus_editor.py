# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_editor.py
# Role          : Edition conversationnelle pour la TUI Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Editeur autonome injectable dans FocusExtensions, sans stockage implicite."""
import curses
import unicodedata
from focus_view import graphemes, cluster_width
from collections.abc import Callable, Sequence

COMMANDS = ('/help', '/analyze', '/indicator', '/target', '/prepare', '/tools',
            '/context', '/models', '/settings', '/ai', '/mode', '/exit',
            '/aide', '/analyse', '/indice', '/cible', '/preparer', '/outils',
            '/contexte', '/modeles', '/parametres', '/ia', '/dossier', '/methodes',
            '/auditer', '/chercher', '/quitter', '/specialite', '/activite',
            '/investigation', '/methods', '/audit', '/search', '/reset', '/quit', '/scenario')


def _extend(ch: str) -> bool:
    return (unicodedata.combining(ch) != 0 or unicodedata.category(ch) in ('Mn', 'Mc', 'Me')
            or '\ufe00' <= ch <= '\ufe0f' or '\U0001f3fb' <= ch <= '\U0001f3ff')


def _boundaries(text: str) -> list[int]:
    positions, offset = [0], 0
    for cluster in graphemes(text):
        offset += len(cluster)
        positions.append(offset)
    return positions


def _width(cluster: str) -> int:
    return cluster_width(cluster)


def _visible(cluster: str) -> str:
    return ''.join('▉' if c == '█' else '�' if unicodedata.category(c) in ('Cc', 'Cs') or
                   (unicodedata.category(c) == 'Cf' and c not in ('\u200c', '\u200d')) else c for c in cluster)


class FocusEditor:
    """Tampon Unicode ; historique en mémoire, fournisseurs de suggestions facultatifs."""
    def __init__(self, history: Sequence[str] = (), *,
                 suggesters: Sequence[Callable[[str], Sequence[str]]] = ()) -> None:
        self._buffer = ''
        self._cursor = 0
        self._history = list(history)
        self._index = None
        self._draft = ('', 0)
        self._edits: dict[int, tuple[str, int]] = {}
        self._suggesters = tuple(suggesters)
        self._cursor_row = 0
        self._last_submission = None
        self._paste = False
        self._paste_cr = False
        self._anchor = None
        self.clipboard = ''
        self._saved_selection = None

    @classmethod
    def from_session(cls, session, **kwargs):
        """Charge les messages utilisateur selon le reglage de la session 09."""
        data = session.data
        history = [m['text'] for m in data['messages'] if m.get('role') == 'user' and m.get('state', 'complete') == 'complete'] if data.get('history_enabled', False) else []
        return cls(history=history, **kwargs)

    @property
    def selection(self):
        if self._anchor is None or self._anchor == self._cursor: return None
        return tuple(sorted((self._anchor, self._cursor)))

    def copy_selection(self):
        bounds = self.selection
        self.clipboard = self._buffer[slice(*bounds)] if bounds else ''
        return self.clipboard

    def _delete_selection(self):
        bounds = self.selection
        if bounds:
            start, end = bounds
            self._buffer = self._buffer[:start] + self._buffer[end:]
            self._cursor = start
        self._anchor = None
        return bool(bounds)

    @property
    def buffer(self) -> str: return self._buffer
    @property
    def cursor(self) -> int: return self._cursor
    @property
    def cursor_row(self) -> int: return self._cursor_row
    @property
    def history(self) -> Sequence[str]: return tuple(self._history)

    def set_text(self, value: str, *, cursor: int | None = None) -> None:
        self._buffer = str(value).replace('\r\n', '\n').replace('\r', '\n')
        self._cursor = len(self._buffer) if cursor is None else max(0, min(len(self._buffer), cursor))
        if cursor is not None:
            self._cursor = max(p for p in _boundaries(self._buffer) if p <= self._cursor)
        # Le controleur restaure un envoi refuse immediatement apres handle_key.
        if cursor is not None and self._last_submission == value:
            if self._history and self._history[-1] == value:
                self._history.pop()
        if cursor is not None and self._saved_selection is not None and self._saved_selection[0] == value:
            self._anchor = self._saved_selection[1]
        else:
            self._anchor = None
        self._saved_selection = None
        self._last_submission = None

    def clear(self) -> None:
        self._buffer = ''
        self._cursor = 0
        self._index = None
        self._edits.clear()
        self._paste = False
        self._paste_cr = False
        self._anchor = None

    def insert_text(self, value: str) -> None:
        value = value.replace('\r\n', '\n').replace('\r', '\n')
        self._delete_selection()
        self._buffer = self._buffer[:self._cursor] + value + self._buffer[self._cursor:]
        self._cursor += len(value)
        # Une insertion au milieu peut relier le texte a la consonne suivante.
        if self._cursor < len(self._buffer):
            self._cursor = min(p for p in _boundaries(self._buffer) if p >= self._cursor)

    def _move_history(self, direction: int) -> None:
        if not self._history: return
        if self._index is None:
            if direction > 0: return
            self._draft = (self._buffer, self._cursor)
            self._index = len(self._history) - 1
        else:
            self._edits[self._index] = (self._buffer, self._cursor)
            self._index = max(0, min(len(self._history), self._index + direction))
            if self._index == len(self._history):
                self._index = None
                self._buffer, self._cursor = self._draft
                return
        self._buffer, self._cursor = self._edits.get(self._index, (self._history[self._index], len(self._history[self._index])))

    def suggestions(self) -> tuple[str, ...]:
        prefix = self._buffer[:self._cursor]
        values = [c for c in COMMANDS if c.startswith(prefix)] if prefix.startswith('/') and ' ' not in prefix else []
        for provider in self._suggesters:
            values.extend(provider(prefix))
        return tuple(dict.fromkeys(values))

    def handle_key(self, key: int | str) -> str | None:
        if key == '\x1b[200~': self._paste = True; self._paste_cr = False; return None
        if key == '\x1b[201~': self._paste = False; self._paste_cr = False; return None
        if self._paste:
            if isinstance(key, str):
                if self._paste_cr and key.startswith('\n'): key = key[1:]
                self._paste_cr = key.endswith('\r') if key else False
                if key: self.insert_text(key)
            return None
        if key in ('SHIFT_ENTER', '\x1b\n', '\x1b\r', '\x0e'):
            self.insert_text('\n'); return None
        if key in ('\n', '\r', curses.KEY_ENTER):
            text = self._buffer
            self._saved_selection = (text, self._anchor)
            self._last_submission = text if text.strip() and (not self._history or self._history[-1] != text) else None
            if self._last_submission is not None: self._history.append(text)
            self.clear()
            return text
        shift_map = {'SHIFT_LEFT': curses.KEY_LEFT, 'SHIFT_RIGHT': curses.KEY_RIGHT,
                     'SHIFT_UP': curses.KEY_UP, 'SHIFT_DOWN': curses.KEY_DOWN,
                     'SHIFT_HOME': curses.KEY_HOME, 'SHIFT_END': curses.KEY_END,
                     'SHIFT_CTRL_HOME': 'CTRL_HOME', 'SHIFT_CTRL_END': 'CTRL_END',
                     'SHIFT_ALT_LEFT': 'ALT_LEFT', 'SHIFT_ALT_RIGHT': 'ALT_RIGHT'}
        if key == 'COPY_SELECTION': self.copy_selection(); return None
        selecting = isinstance(key, str) and key in shift_map
        if selecting:
            if self._anchor is None: self._anchor = self._cursor
            key = shift_map[key]
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN,
                     curses.KEY_HOME, curses.KEY_END, '\x01', '\x05', 'CTRL_HOME', 'CTRL_END', 'ALT_LEFT', 'ALT_RIGHT'):
            if self.selection and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                self._cursor = self.selection[0 if key == curses.KEY_LEFT else 1]
                self._anchor = None
                return None
            self._anchor = None
        if key in ('\b', '\x7f', curses.KEY_BACKSPACE, curses.KEY_DC) and self._delete_selection(): return None
        bounds = _boundaries(self._buffer)
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT, '\b', '\x7f', curses.KEY_BACKSPACE, curses.KEY_DC):
            left = max((p for p in bounds if p < self._cursor), default=0)
            right = min((p for p in bounds if p > self._cursor), default=len(self._buffer))
            if key == curses.KEY_LEFT: self._cursor = left
            elif key == curses.KEY_RIGHT: self._cursor = right
            elif key in ('\b', '\x7f', curses.KEY_BACKSPACE):
                self._buffer = self._buffer[:left] + self._buffer[self._cursor:]; self._cursor = left
            else: self._buffer = self._buffer[:self._cursor] + self._buffer[right:]
            return None
        start = self._buffer.rfind('\n', 0, self._cursor) + 1
        end = self._buffer.find('\n', self._cursor)
        if end < 0: end = len(self._buffer)
        if key in (curses.KEY_HOME, '\x01'): self._cursor = start; return None
        if key in (curses.KEY_END, '\x05'): self._cursor = end; return None
        if key in ('CTRL_HOME',): self._cursor = 0; return None
        if key in ('CTRL_END',): self._cursor = len(self._buffer); return None
        if key in ('ALT_LEFT', 'ALT_RIGHT'):
            if key == 'ALT_LEFT':
                while self._cursor and self._buffer[self._cursor - 1].isspace(): self._cursor -= 1
                while self._cursor and not self._buffer[self._cursor - 1].isspace(): self._cursor -= 1
            else:
                while self._cursor < len(self._buffer) and not self._buffer[self._cursor].isspace(): self._cursor += 1
                while self._cursor < len(self._buffer) and self._buffer[self._cursor].isspace(): self._cursor += 1
            return None
        if key in (curses.KEY_UP, curses.KEY_DOWN):
            col = self._cursor - start
            if key == curses.KEY_UP and start:
                prev = self._buffer.rfind('\n', 0, start - 1) + 1
                self._cursor = min(prev + col, start - 1)
            elif key == curses.KEY_DOWN and end < len(self._buffer):
                nxt = self._buffer.find('\n', end + 1)
                self._cursor = min(end + 1 + col, len(self._buffer) if nxt < 0 else nxt)
            elif not selecting: self._move_history(-1 if key == curses.KEY_UP else 1)
            self._cursor = max(p for p in _boundaries(self._buffer) if p <= self._cursor)
            return None
        if key == '\x00':
            options = self.suggestions()
            if options:
                import os
                common = os.path.commonprefix(options)
                if len(common) > self._cursor: self.set_text(common + self._buffer[self._cursor:], cursor=len(common))
            return None
        if isinstance(key, str):
            if len(key) == 1 and (key.isprintable() or key == '\u200d' or _extend(key)): self.insert_text(key)
            elif len(key) > 1 and not key.startswith('\x1b') and not (key.isascii() and key.isupper() and '_' in key):
                if all(c.isprintable() or c in '\n\r\t\u200d' or _extend(c) for c in key): self.insert_text(key)
        return None

    def render_lines(self, width: int, *, active: bool = True) -> Sequence[str]:
        width = max(1, width)
        prefix = '> ' if width < 18 else 'uchambuzi> '
        continuation = '  ' if width < 18 else '           '
        if width <= len(prefix): prefix = continuation = ''
        rows = []
        line = prefix
        cols = len(prefix)
        bounds = _boundaries(self._buffer)
        positions = list(zip(bounds, bounds[1:]))
        positions.append((len(self._buffer), len(self._buffer)))
        for a, b in positions:
            cluster = self._buffer[a:b]
            selected = self.selection
            if selected and a in selected:
                marker = '⟦' if a == selected[0] else '⟧'
                if cols + 1 > width and cols > len(continuation): rows.append(line); line = continuation; cols = len(line)
                line += marker; cols += 1
            if a == self._cursor:
                if cols + 1 > width and cols > len(continuation): rows.append(line); line = continuation; cols = len(line)
                self._cursor_row = len(rows)
                if active: line += '█'; cols += 1
            if not cluster: continue
            if cluster == '\n': rows.append(line); line = continuation; cols = len(line); continue
            display = _visible(cluster)
            w = _width(display)
            if cols + w > width and cols > len(continuation): rows.append(line); line = continuation; cols = len(line)
            line += display; cols += w
        rows.append(line)
        return tuple(rows)
