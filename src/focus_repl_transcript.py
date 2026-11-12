# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_repl_transcript.py
# Role          : Shim de compatibilite reexportant le module repl_render
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Shim de compatibilité : réexporte l'ensemble de repl_render."""
from repl_render import (
    MARKDOWN_THEME,
    TranscriptHeading,
    TranscriptCodeBlock,
    TranscriptMarkdown,
    markdown,
    MarkdownStream,
    preview_ansi,
    OutputRecord,
    Transcript,
    ReflowConsole,
)

__all__ = [
    'MARKDOWN_THEME',
    'TranscriptHeading',
    'TranscriptCodeBlock',
    'TranscriptMarkdown',
    'markdown',
    'MarkdownStream',
    'preview_ansi',
    'OutputRecord',
    'Transcript',
    'ReflowConsole',
]
