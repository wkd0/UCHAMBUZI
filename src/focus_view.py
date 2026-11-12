# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_view.py
# Role          : Rendu Markdown et projection terminale de la conversation
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Projection terminale sans mutation du texte source, compatible Focus 02.

Les lignes structurées exposent le numéro de ligne source et les styles pour un
contrôleur capable d'utiliser des attributs curses et un ancrage stable.
"""
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata
from focus_contracts import Role


def terminal_text(text):
    """Les contrôles dangereux ne parviennent jamais au terminal."""
    # Retirer les séquences OSC et CSI avec leur contenu avant de filtrer les
    # caractères isolés ; le texte original du message reste inchangé.
    text = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\|$)', '', text)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    return ''.join('�' if (unicodedata.category(c) in ('Cc', 'Cs') and c not in '\n\t')
                   or c in '\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'
                   else c for c in text)


def width_of(char):
    if unicodedata.combining(char) or unicodedata.category(char) in ('Mn', 'Mc', 'Me', 'Cf') or '\U0001f3fb' <= char <= '\U0001f3ff':
        return 0
    return 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1


# Proprietes Indic_Conjunct_Break Unicode 17.0.0 pour UAX #29, regle GB9c.
# Source : https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt
# Donnees derivees (c) 2025 Unicode, Inc. ; notice de licence conservee ci-dessous.
# UNICODE LICENSE V3
#
# COPYRIGHT AND PERMISSION NOTICE
#
# Copyright © 1991-2026 Unicode, Inc.
#
# NOTICE TO USER: Carefully read the following legal agreement. BY
# DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR
# SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE
# TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT
# DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of data files and any associated documentation (the "Data Files") or
# software and any associated documentation (the "Software") to deal in the
# Data Files or Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, and/or sell
# copies of the Data Files or Software, and to permit persons to whom the
# Data Files or Software are furnished to do so, provided that either (a)
# this copyright and permission notice appear with all copies of the Data
# Files or Software, or (b) this copyright and permission notice appear in
# associated Documentation.
#
# THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF
# THIRD PARTY RIGHTS.
#
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE
# BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES,
# OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
# ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA
# FILES OR SOFTWARE.
#
# Except as contained in this notice, the name of a copyright holder shall
# not be used in advertising or otherwise to promote the sale, use or other
# dealings in these Data Files or Software without prior written
# authorization of the copyright holder.

def _property_ranges(encoded):
    result = []
    for value in encoded.split():
        pair = value.split('..')
        result.append((int(pair[0], 16), int(pair[-1], 16)))
    return tuple(result)


_INDIC_RANGES = {
    'Linker': _property_ranges(
        '094D 09CD 0ACD 0B4D 0C4D 0D4D 1039 17D2 1A60 1B44 1BAB A9C0 AAF6 10A3F 11133 113D0 1193E '
        '11A47 11A99 11F42 '
    ),
    'Consonant': _property_ranges(
        '0915..0939 0958..095F 0978..097F 0995..09A8 09AA..09B0 09B2 09B6..09B9 09DC..09DD 09DF '
        '09F0..09F1 0A95..0AA8 0AAA..0AB0 0AB2..0AB3 0AB5..0AB9 0AF9 0B15..0B28 0B2A..0B30 '
        '0B32..0B33 0B35..0B39 0B5C..0B5D 0B5F 0B71 0C15..0C28 0C2A..0C39 0C58..0C5A 0D15..0D3A '
        '1000..102A 103F 1050..1055 105A..105D 1061 1065..1066 106E..1070 1075..1081 108E '
        '1780..17B3 1A20..1A54 1B0B..1B0C 1B13..1B33 1B45..1B4C 1B83..1BA0 1BAE..1BAF 1BBB..1BBD '
        'A989..A98B A98F..A9B2 A9E0..A9E4 A9E7..A9EF A9FA..A9FE AA60..AA6F AA71..AA73 AA7A '
        'AA7E..AA7F AAE0..AAEA ABC0..ABDA 10A00 10A10..10A13 10A15..10A17 10A19..10A35 11103..11126 '
        '11144 11147 11380..11389 1138B 1138E 11390..113B5 11900..11906 11909 1190C..11913 '
        '11915..11916 11918..1192F 11A00 11A0B..11A32 11A50 11A5C..11A83 11F04..11F10 11F12..11F33 '
    ),
    'Extend': _property_ranges(
        '0300..036F 0483..0487 0488..0489 0591..05BD 05BF 05C1..05C2 05C4..05C5 05C7 0610..061A '
        '064B..065F 0670 06D6..06DC 06DF..06E4 06E7..06E8 06EA..06ED 0711 0730..074A 07A6..07B0 '
        '07EB..07F3 07FD 0816..0819 081B..0823 0825..0827 0829..082D 0859..085B 0897..089F '
        '08CA..08E1 08E3..0902 093A 093C 0941..0948 0951..0957 0962..0963 0981 09BC 09BE 09C1..09C4 '
        '09D7 09E2..09E3 09FE 0A01..0A02 0A3C 0A41..0A42 0A47..0A48 0A4B..0A4D 0A51 0A70..0A71 0A75 '
        '0A81..0A82 0ABC 0AC1..0AC5 0AC7..0AC8 0AE2..0AE3 0AFA..0AFF 0B01 0B3C 0B3E 0B3F 0B41..0B44 '
        '0B55..0B56 0B57 0B62..0B63 0B82 0BBE 0BC0 0BCD 0BD7 0C00 0C04 0C3C 0C3E..0C40 0C46..0C48 '
        '0C4A..0C4C 0C55..0C56 0C62..0C63 0C81 0CBC 0CBF 0CC0 0CC2 0CC6 0CC7..0CC8 0CCA..0CCB '
        '0CCC..0CCD 0CD5..0CD6 0CE2..0CE3 0D00..0D01 0D3B..0D3C 0D3E 0D41..0D44 0D57 0D62..0D63 '
        '0D81 0DCA 0DCF 0DD2..0DD4 0DD6 0DDF 0E31 0E34..0E3A 0E47..0E4E 0EB1 0EB4..0EBC 0EC8..0ECE '
        '0F18..0F19 0F35 0F37 0F39 0F71..0F7E 0F80..0F84 0F86..0F87 0F8D..0F97 0F99..0FBC 0FC6 '
        '102D..1030 1032..1037 103A 103D..103E 1058..1059 105E..1060 1071..1074 1082 1085..1086 '
        '108D 109D 135D..135F 1712..1714 1715 1732..1733 1734 1752..1753 1772..1773 17B4..17B5 '
        '17B7..17BD 17C6 17C9..17D1 17D3 17DD 180B..180D 180F 1885..1886 18A9 1920..1922 1927..1928 '
        '1932 1939..193B 1A17..1A18 1A1B 1A56 1A58..1A5E 1A62 1A65..1A6C 1A73..1A7C 1A7F 1AB0..1ABD '
        '1ABE 1ABF..1ADD 1AE0..1AEB 1B00..1B03 1B34 1B35 1B36..1B3A 1B3B 1B3C 1B3D 1B42 1B43 '
        '1B6B..1B73 1B80..1B81 1BA2..1BA5 1BA8..1BA9 1BAA 1BAC..1BAD 1BE6 1BE8..1BE9 1BED '
        '1BEF..1BF1 1BF2..1BF3 1C2C..1C33 1C36..1C37 1CD0..1CD2 1CD4..1CE0 1CE2..1CE8 1CED 1CF4 '
        '1CF8..1CF9 1DC0..1DFF 200D 20D0..20DC 20DD..20E0 20E1 20E2..20E4 20E5..20F0 2CEF..2CF1 '
        '2D7F 2DE0..2DFF 302A..302D 302E..302F 3099..309A A66F A670..A672 A674..A67D A69E..A69F '
        'A6F0..A6F1 A802 A806 A80B A825..A826 A82C A8C4..A8C5 A8E0..A8F1 A8FF A926..A92D A947..A951 '
        'A953 A980..A982 A9B3 A9B6..A9B9 A9BC..A9BD A9E5 AA29..AA2E AA31..AA32 AA35..AA36 AA43 AA4C '
        'AA7C AAB0 AAB2..AAB4 AAB7..AAB8 AABE..AABF AAC1 AAEC..AAED ABE5 ABE8 ABED FB1E FE00..FE0F '
        'FE20..FE2F FF9E..FF9F 101FD 102E0 10376..1037A 10A01..10A03 10A05..10A06 10A0C..10A0F '
        '10A38..10A3A 10AE5..10AE6 10D24..10D27 10D69..10D6D 10EAB..10EAC 10EFA..10EFF 10F46..10F50 '
        '10F82..10F85 11001 11038..11046 11070 11073..11074 1107F..11081 110B3..110B6 110B9..110BA '
        '110C2 11100..11102 11127..1112B 1112D..11132 11134 11173 11180..11181 111B6..111BE 111C0 '
        '111C9..111CC 111CF 1122F..11231 11234 11235 11236..11237 1123E 11241 112DF 112E3..112EA '
        '11300..11301 1133B..1133C 1133E 11340 1134D 11357 11366..1136C 11370..11374 113B8 '
        '113BB..113C0 113C2 113C5 113C7..113C9 113CE 113CF 113D2 113E1..113E2 11438..1143F '
        '11442..11444 11446 1145E 114B0 114B3..114B8 114BA 114BD 114BF..114C0 114C2..114C3 115AF '
        '115B2..115B5 115BC..115BD 115BF..115C0 115DC..115DD 11633..1163A 1163D 1163F..11640 116AB '
        '116AD 116B0..116B5 116B6 116B7 1171D 1171F 11722..11725 11727..1172B 1182F..11837 '
        '11839..1183A 11930 1193B..1193C 1193D 11943 119D4..119D7 119DA..119DB 119E0 11A01..11A0A '
        '11A33..11A38 11A3B..11A3E 11A51..11A56 11A59..11A5B 11A8A..11A96 11A98 11B60 11B62..11B64 '
        '11B66 11C30..11C36 11C38..11C3D 11C3F 11C92..11CA7 11CAA..11CB0 11CB2..11CB3 11CB5..11CB6 '
        '11D31..11D36 11D3A 11D3C..11D3D 11D3F..11D45 11D47 11D90..11D91 11D95 11D97 11EF3..11EF4 '
        '11F00..11F01 11F36..11F3A 11F40 11F41 11F5A 13440 13447..13455 1611E..16129 1612D..1612F '
        '16AF0..16AF4 16B30..16B36 16F4F 16F8F..16F92 16FE4 16FF0..16FF1 1BC9D..1BC9E 1CF00..1CF2D '
        '1CF30..1CF46 1D165..1D166 1D167..1D169 1D16D..1D172 1D17B..1D182 1D185..1D18B 1D1AA..1D1AD '
        '1D242..1D244 1DA00..1DA36 1DA3B..1DA6C 1DA75 1DA84 1DA9B..1DA9F 1DAA1..1DAAF 1E000..1E006 '
        '1E008..1E018 1E01B..1E021 1E023..1E024 1E026..1E02A 1E08F 1E130..1E136 1E2AE 1E2EC..1E2EF '
        '1E4EC..1E4EF 1E5EE..1E5EF 1E6E3 1E6E6 1E6EE..1E6EF 1E6F5 1E8D0..1E8D6 1E944..1E94A '
        '1F3FB..1F3FF E0020..E007F E0100..E01EF '
    ),
}
_INDIC_STARTS = {name: tuple(a for a, _ in ranges) for name, ranges in _INDIC_RANGES.items()}


@lru_cache(maxsize=4096)
def _indic_property(ch):
    code = ord(ch)
    if code < 0x300:
        return ''
    for name, ranges in _INDIC_RANGES.items():
        pos = bisect_right(_INDIC_STARTS[name], code) - 1
        if pos >= 0 and code <= ranges[pos][1]:
            return name
    return ''


def graphemes(text):
    """Graphemes partages par l'editeur/rendu, dont les conjonctions GB9c.

    Les proprietes indiciennes sont explicites, independantes de la version
    unicodedata du Python hote. Ceci ne pretend pas implementer tout UAX #29.
    """
    cluster = ''
    regional = 0
    # 0 : hors conjonction ; 1 : consonne ; 2 : consonne puis au moins un linker.
    indic = 0
    for ch in text:
        prop = _indic_property(ch)
        is_regional = '\U0001f1e6' <= ch <= '\U0001f1ff'
        extend = bool(cluster) and (width_of(ch) == 0 or prop in ('Linker', 'Extend')
                                    or cluster.endswith('\u200d')
                                    or (is_regional and regional == 1)
                                    or (prop == 'Consonant' and indic == 2))
        if not extend and cluster:
            yield cluster
            cluster = ''
            regional = 0
            indic = 0
        cluster += ch
        regional = regional + 1 if is_regional else 0
        if prop == 'Consonant':
            indic = 1
        elif prop == 'Linker' and indic:
            indic = 2
        elif prop != 'Extend':
            indic = 0
    if cluster:
        yield cluster


def cluster_width(cluster):
    widths = [width_of(c) for c in cluster]
    if '\u200d' in cluster or '\ufe0f' in cluster or any('\U0001f1e6' <= c <= '\U0001f1ff' for c in cluster):
        return max(2, max(widths, default=0))
    return sum(widths)


def display_width(text):
    return sum(cluster_width(g) for g in graphemes(text))


def wrap_exact(line, width):
    """Coupe aux grappes sans supprimer d'espaces ; taquets de tabulation à 4."""
    width = max(1, width)
    result, part, col = [], '', 0
    for cluster in graphemes(line):
        if cluster == '\t':
            for _ in range(4 - col % 4):
                if col >= width:
                    result.append(part)
                    part, col = '', 0
                part += ' '
                col += 1
            continue
        size = cluster_width(cluster)
        if col and col + size > width:
            result.append(part)
            part, col = '', 0
        part += cluster
        col += size
    result.append(part)
    return result


@dataclass(frozen=True)
class Span:
    text: str
    style: str = 'text'


@dataclass(frozen=True)
class RenderedLine:
    source_line: int
    text: str
    style: str = 'text'
    source_column: int = 0


# Seuls des délimiteurs complets sont interprétés ; un fragment incomplet reste visible.
_INLINE = re.compile(r'(!?\[([^\]\n]+)\]\(([^\s)]+)\)|\*\*([^*\n]+)\*\*|__([^_\n]+)__|(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!\w)_([^_\n]+)_(?!\w)|`([^`\n]+)`)')


def inline_spans(text):
    result = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            result.append(Span(text[pos:m.start()]))
        if m.group(2) is not None:
            result.append(Span(m.group(2) + ' (' + m.group(3) + ')', 'link'))
        elif m.group(4) is not None or m.group(5) is not None:
            result.append(Span(m.group(4) or m.group(5), 'bold'))
        elif m.group(6) is not None or m.group(7) is not None:
            result.append(Span(m.group(6) or m.group(7), 'italic'))
        else:
            result.append(Span(m.group(8), 'code'))
        pos = m.end()
    result.append(Span(text[pos:]))
    return tuple(result)


def inline_text(text):
    # Les guillemets marquent les emphases dans le repli sans attributs curses.
    marks = {'bold': ('«', '»'), 'italic': ('‹', '›'), 'code': ('`', '`')}
    return ''.join(marks.get(s.style, ('', ''))[0] + s.text + marks.get(s.style, ('', ''))[1]
                   for s in inline_spans(text))


def _table_cells(line):
    text = line.strip().strip('|')
    cells, part, escaped, code = [], [], False, False
    for char in text:
        if escaped:
            part.append(char)
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == '`':
            code = not code
            part.append(char)
        elif char == '|' and not code:
            cells.append(''.join(part).strip())
            part = []
        else:
            part.append(char)
    if escaped:
        part.append('\\')
    cells.append(''.join(part).strip())
    return cells


def _table_separator(line):
    cells = _table_cells(line)
    return bool(cells) and all(re.fullmatch(r':?-{3,}:?', c) for c in cells)


@lru_cache(maxsize=64)
def _render(text, width, streaming):
    source = terminal_text(text).split('\n')
    result = []
    code = False
    fence_char, fence_len = '', 0
    i = 0
    def emit(index, value, style='text', prefix=''):
        parts = wrap_exact(value, max(1, width - display_width(prefix)))
        # Associer la projection aux colonnes de la ligne source, sans modifier
        # le texte original. Les decorations sans equivalent pointent la position precedente.
        mapping, cursor = [], 0
        for char in value:
            found = source[index].find(char, cursor)
            if found >= 0:
                cursor = found + 1
            mapping.append(max(0, cursor - 1))
        column = 0
        for part in parts:
            original_column = mapping[min(column, len(mapping)-1)] if mapping else 0
            result.append(RenderedLine(index, prefix + part, style, original_column))
            column += len(part)
    while i < len(source):
        line = source[i]
        fence = re.match(r'^ {0,3}(`{3,}|~{3,})([^`]*)$', line)
        if fence and (not code or (fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_len and not fence.group(2).strip())):
            if code:
                emit(i, '└─ fin du code', 'code_border')
                code = False
            else:
                code = True
                fence_char, fence_len = fence.group(1)[0], len(fence.group(1))
                emit(i, '┌─ code' + (' : ' + fence.group(2).strip() if fence.group(2).strip() else ''), 'code_border')
            i += 1
            continue
        if code:
            emit(i, line, 'code', '│ ')
            i += 1
            continue
        if i + 1 < len(source) and '|' in line and _table_separator(source[i + 1]):
            rows = [_table_cells(line)]
            j = i + 2
            while j < len(source) and '|' in source[j] and source[j].strip():
                rows.append(_table_cells(source[j])); j += 1
            count = max(map(len, rows))
            sizes = [max(display_width(inline_text(row[k])) if k < len(row) else 0 for row in rows) for k in range(count)]
            for n, row in enumerate(rows):
                cells = [inline_text(row[k]) if k < len(row) else '' for k in range(count)]
                value = ' │ '.join(c + ' ' * (sizes[k] - display_width(c)) for k, c in enumerate(cells))
                emit(i if n == 0 else i + n + 1, value, 'table', '│ ')
                if n == 0:
                    emit(i + 1, '─┼─'.join('─' * size for size in sizes), 'table', '├─')
            i = j
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$', line)
        quote = re.match(r'^(\s*)>\s?(.*)$', line)
        item = re.match(r'^(\s*)([-+*]|\d+[.)])\s+(.*)$', line)
        if heading:
            emit(i, inline_text(heading.group(2)), 'heading', '▌ ')
        elif quote:
            emit(i, inline_text(quote.group(2)), 'quote', quote.group(1) + '│ ')
        elif item:
            marker = '•' if item.group(2) in '-+*' else item.group(2)
            emit(i, inline_text(item.group(3)), 'list', item.group(1) + marker + ' ')
        else:
            emit(i, inline_text(line))
        i += 1
    return tuple(result)


class ConversationRenderer:
    """Renderer Focus ; `layout_message` fournit les points d'ancrage source."""
    def layout_message(self, message, width, *, streaming=False):
        # Éviter de retenir de très longues réponses dans le cache borné en nombre.
        render = _render if len(message.text) <= 65536 else _render.__wrapped__
        return render(message.text, max(1, width), streaming)

    @staticmethod
    def source_text(message):
        """Texte exact à copier explicitement, jamais la projection terminale."""
        return message.text

    @staticmethod
    def anchored_view(layout, height, anchor=None):
        """Renvoie une fenêtre et son ancre (ligne source, occurrence sur cette ligne).

        L'appelant mémorise l'ancre lors d'un défilement manuel et la restitue
        après réception ou resize ; None suit la fin de la réponse.
        """
        height = max(0, height)
        if not layout or not height:
            return (), None
        if anchor is None:
            start = max(0, len(layout) - height)
        else:
            source, occurrence = anchor
            matches = [i for i, line in enumerate(layout) if line.source_line == source]
            if matches:
                start = matches[min(max(0, occurrence), len(matches) - 1)]
            else:
                start = next((i for i, line in enumerate(layout) if line.source_line > source), len(layout) - 1)
            start = min(start, max(0, len(layout) - 1))
        first = layout[start]
        occurrence = sum(1 for line in layout[:start] if line.source_line == first.source_line)
        return layout[start:start + height], (first.source_line, occurrence)

    def render_message(self, message, width, *, streaming=False):
        label = '› Enquêteur' if message.role == Role.USER else '◆ UCHAMBUZI'
        if streaming:
            label += ' ▍'
        return (label,) + tuple('  ' + line.text for line in self.layout_message(message, max(1, width - 2), streaming=streaming))

    def render_panel(self, title, content, width):
        lines = ['[' + terminal_text(title).replace('\n', ' ') + ']']
        for line in terminal_text(content).split('\n'):
            lines.extend(wrap_exact(line, width))
        return tuple(lines)
