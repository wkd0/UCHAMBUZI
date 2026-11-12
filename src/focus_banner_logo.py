# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_banner_logo.py
# Role          : Rendu du symbole SVG officiel en demi-blocs Unicode
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Logo terminal dérivé du SVG officiel, sans dépendance graphique à l'exécution.

Masque rasterisé depuis assets/branding/logo/uchambuzi-lockup-horizontal.svg.
Deux pixels verticaux par cellule ; transparence conservée sur le fond terminal.
Le bleu nuit du SVG devient ardoise pour rester lisible sur fond sombre.
"""
from rich.text import Text

PIXEL_ROWS = (
    '          oo',
    '         oooo',
    '       eeeeeeee',
    '    eeeeeeeeeeeee',
    '   eeeeee e eeeeeee',
    '  oeeeee  e   eeeeeo',
    ' eooeee  eeee eeeeoee',
    ' eooeee  eeee eeeeooe',
    '  oeeeee  e   eeeeeo',
    '   eeeeeeeeeeeeeeee',
    '     eeeeeeeeeeee',
    '       eeeeeeee',
)

def banner_logo(primary: str, outline: str) -> Text:
    """Compose le symbole avec des demi-blocs Unicode TrueColor."""
    colors = {'o': primary, 'e': outline}
    result = Text(no_wrap=True)
    for y in range(0, len(PIXEL_ROWS), 2):
        top = PIXEL_ROWS[y].ljust(22)
        bottom = PIXEL_ROWS[y + 1].ljust(22)
        for upper, lower in zip(top, bottom):
            if upper == lower == ' ':
                result.append(' ')
            elif upper == ' ':
                result.append('▄', style=colors[lower])
            elif lower == ' ':
                result.append('▀', style=colors[upper])
            elif upper == lower:
                result.append('█', style=colors[upper])
            else:
                result.append('▀', style=f'{colors[upper]} on {colors[lower]}')
        if y + 2 < len(PIXEL_ROWS):
            result.append('\n')
    return result
