# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_terminal_keys.py
# Role          : Decodage portable non bloquant des touches terminal et du collage
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Complète ncurses sans dépendre de define_key, absent de Python standard."""
import curses
import time

SEQUENCES = {
    **{'\x1b' + prefix + final: key
       for prefix in ('[', 'O')
       for final, key in (('A', curses.KEY_UP), ('B', curses.KEY_DOWN),
                          ('C', curses.KEY_RIGHT), ('D', curses.KEY_LEFT),
                          ('H', curses.KEY_HOME), ('F', curses.KEY_END))},
    '\x1b[1~': curses.KEY_HOME, '\x1b[4~': curses.KEY_END,
    '\x1b[7~': curses.KEY_HOME, '\x1b[8~': curses.KEY_END,
    '\x1b[3~': curses.KEY_DC, '\x1b[5~': curses.KEY_PPAGE, '\x1b[6~': curses.KEY_NPAGE,
    '\x1b[200~': '\x1b[200~', '\x1b[201~': '\x1b[201~',
    '\x1b[1;3D': 'ALT_LEFT', '\x1b[1;3C': 'ALT_RIGHT',
    '\x1b[1;5H': 'CTRL_HOME', '\x1b[1;5F': 'CTRL_END',
    '\x1b[1;2D':'SHIFT_LEFT', '\x1b[1;2C':'SHIFT_RIGHT',
    '\x1b[1;2A':'SHIFT_UP', '\x1b[1;2B':'SHIFT_DOWN',
    '\x1b[1;2H':'SHIFT_HOME', '\x1b[1;2F':'SHIFT_END',
    '\x1b[1;6H':'SHIFT_CTRL_HOME', '\x1b[1;6F':'SHIFT_CTRL_END',
    '\x1b[1;4D':'SHIFT_ALT_LEFT', '\x1b[1;4C':'SHIFT_ALT_RIGHT',
    '\x1b[1;5D':'ALT_LEFT', '\x1b[1;5C':'ALT_RIGHT',
    '\x1bb':'ALT_LEFT', '\x1bf':'ALT_RIGHT',
    '\x1b\n': '\x1b\n', '\x1b\r': '\x1b\n',
}
KEY_NAMES = {b'kHOM5':'CTRL_HOME', b'kEND5':'CTRL_END',
             b'kLFT3':'ALT_LEFT', b'kRIT3':'ALT_RIGHT', b'KEY_SLEFT':'SHIFT_LEFT', b'KEY_SRIGHT':'SHIFT_RIGHT', b'KEY_SR':'SHIFT_UP', b'KEY_SF':'SHIFT_DOWN', b'KEY_SHOME':'SHIFT_HOME', b'KEY_SEND':'SHIFT_END'}

KEY_NAMES.update({b'kHOM6':'SHIFT_CTRL_HOME', b'kEND6':'SHIFT_CTRL_END',
                  b'kLFT2':'SHIFT_LEFT', b'kRIT2':'SHIFT_RIGHT',
                  b'kUP2':'SHIFT_UP', b'kDN2':'SHIFT_DOWN',
                  b'kLFT4':'SHIFT_ALT_LEFT', b'kRIT4':'SHIFT_ALT_RIGHT',
                  b'kLFT5':'ALT_LEFT', b'kRIT5':'ALT_RIGHT'})


class TerminalKeys:
    def __init__(self, *, clock=time.monotonic, keyname=curses.keyname, delay=.25):
        self.clock, self.keyname, self.delay = clock, keyname, delay
        self.pending = ''
        self.deadline = 0
        self.paste = False

    def flush(self, *, force=False):
        if not self.pending or not (force or self.clock() >= self.deadline):
            return []
        # Une sequence CSI reconnue mais partielle reste bornee et en attente.
        # Seul Escape isole expire ; un intervalle reseau ne doit pas exposer [200~.
        if self.pending.startswith(('\x1b[', '\x1bO')) and any(seq.startswith(self.pending) for seq in SEQUENCES) and not force:
            return []
        pending, self.pending = self.pending, ''
        return list(pending)

    def feed(self, key):
        if isinstance(key, int):
            try:
                mapped = KEY_NAMES.get(self.keyname(key), key)
            except curses.error:
                mapped = key
            if self.paste and mapped in SEQUENCES.values():
                mapped = next((s for s,v in SEQUENCES.items() if v == mapped), key)
            return self.flush(force=True) + [mapped]
        if not isinstance(key, str):
            return []
        if len(key) > 1:
            return [event for char in key for event in self.feed(char)]
        if not self.pending and key != '\x1b':
            return [key]
        if not self.pending:
            self.deadline = self.clock() + self.delay
        self.pending += key
        if self.pending.startswith("\x1b["):
            self.deadline = self.clock() + 2.0
        sequences = {'\x1b[201~':'\x1b[201~'} if self.paste else SEQUENCES
        if self.pending in sequences:
            result, self.pending = sequences[self.pending], ''
            if result == '\x1b[200~': self.paste = True
            if result == '\x1b[201~': self.paste = False
            return [result]
        if any(s.startswith(self.pending) for s in sequences):
            return []
        return self.flush(force=True)
