# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_menu.py
# Role          : Rendu du menu de commandes slash sous la saisie et aide interactive
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Composant de rendu pour le menu d'autocomplétion des commandes slash et l'aide aux raccourcis.

Affiche les suggestions directement SOUS la boîte de saisie (sans fenêtre flottante
opaque masquant le texte) et au-dessus de la barre d'état inférieure.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence
from prompt_toolkit.formatted_text import FormattedText, to_plain_text
from prompt_toolkit.completion import Completion
from prompt_toolkit.utils import get_cwidth


# ============================================================================
# Palette Visuelle UCHAMBUZI (Haute Lisibilité TrueColor)
# ============================================================================
COLOR_ORANGE = '#E85D26'   # Orange officiel UCHAMBUZI / WKD
COLOR_CYAN = '#38BDF8'     # Cyan vif pour sélection et contrastes
COLOR_GRAY = '#94A3B8'     # Gris ardoise clair pour métadonnées et descriptions
COLOR_WHITE = '#FFFFFF'    # Blanc éclatant
COLOR_BORDER = '#334155'   # Délimitation discrète


# Documentation standard des commandes UCHAMBUZI
DEFAULT_COMMAND_DOCS: dict[str, str] = {
    '/help': 'Affiche ce guide des commandes et les raccourcis disponibles',
    '/usage': 'Affiche l\'utilisation des ressources, du contexte et des jetons',
    '/clear': 'Efface l\'écran du terminal et réaffiche la bannière de session',
    '/status': 'Affiche l\'état complet du moteur IA, des outils et du dossier',
    '/team': 'Bascule entre les 4 pôles cyber (OSINT, Red Team, Blue Team, Purple Team)',
    '/mode': 'Bascule entre les 8 profils spécialisés (Assist, Trace, Intel, Defend...)',
    '/theme': 'Choisit ou affiche la palette de couleurs (Focus, Matrix, Dracula, Nord...)',
    '/scenario': 'Active une activité ou un scénario guidé pour le profil courant',
    '/analyze': 'Analyse un indice (IP, domaine, hash, URL, fichier) et ses outils',
    '/indicator': 'Déclare un indicateur technique explicite avec son type',
    '/target': 'Sélectionne un hôte ou un indice dérivé pour analyse',
    '/prepare': 'Prépare une commande d\'investigation sans exécution automatique',
    '/investigation': 'Gère le dossier d\'enquête actif et consulte le journal horodaté UTC',
    '/tools': 'Vérifie l\'inventaire et la présence des 7 outils Kali (dig, exiftool...)',
    '/audit': 'Inspecte un fichier suspect contre les injections de prompt',
    '/methods': 'Bibliothèque de méthodes d\'investigation validées et éprouvées',
    '/search': 'Recherche documentaire déterministe et pondérée dans le corpus',
    '/models': 'Affiche les modèles IA locaux installés dans Ollama',
    '/ai': 'Affiche l\'état du moteur IA ou bascule d\'état/modèle',
    '/settings': 'Affiche ou configure les paramètres de session',
    '/context': 'Gère la taille du contexte et le budget mémoire de la session',
    '/details': 'Développe la dernière sortie d\'outil ou /details NUMERO (Ctrl+T)',
    '/history': 'Affiche l\'historique des commandes saisies dans cette session',
    '/reset': 'Efface l\'historique de la conversation courante',
    '/exit': 'Quitte proprement l\'application UCHAMBUZI',
}


def _extract_completion_info(item: Any) -> tuple[str, str]:
    """Extrait le texte de commande et la description d'un élément de complétion."""
    if isinstance(item, Completion):
        display_text = item.display_text if hasattr(item, 'display_text') else str(item.display)
        meta = item.display_meta_text if hasattr(item, 'display_meta_text') else str(item.display_meta or '')
        if not meta:
            meta = DEFAULT_COMMAND_DOCS.get(display_text, '')
        return display_text, meta
    if isinstance(item, tuple) and len(item) >= 2:
        return str(item[0]), str(item[1])
    text = str(item)
    return text, DEFAULT_COMMAND_DOCS.get(text, '')


def format_completion_menu(
    completions: Sequence[Any],
    selected_index: int | None = None,
    width: int = 80,
    max_items: int = 8,
) -> FormattedText:
    """Génère la liste de complétion des commandes slash sous la boîte de saisie.

    Spécifications :
    - 8 lignes maximum
    - Défilement fluide centré sur le curseur si plus de 8 suggestions
    - Commande en orange éclatant (#E85D26) ou sélectionnée (#38BDF8)
    - Description alignée en gris clair (#94A3B8)
    - AUCUN fond opaque qui cache le texte
    """
    if not completions:
        return FormattedText([])

    total = len(completions)
    max_items = max(1, min(max_items, 8))

    # Calcul de la fenêtre glissante pour limiter strictement à max_items (8 lignes)
    if total <= max_items:
        start_idx = 0
        end_idx = total
    else:
        if selected_index is None or selected_index < 0:
            start_idx = 0
        else:
            # Centrer la sélection dans la fenêtre de défilement
            half = max_items // 2
            if selected_index < half:
                start_idx = 0
            elif selected_index >= total - half:
                start_idx = total - max_items
            else:
                start_idx = selected_index - half
        end_idx = min(total, start_idx + max_items)

    visible_items = completions[start_idx:end_idx]

    # Extraction des libellés et alignement de la colonne commande
    parsed: list[tuple[int, str, str]] = []
    max_cmd_len = 0
    for offset, item in enumerate(visible_items):
        abs_index = start_idx + offset
        cmd_text, meta_text = _extract_completion_info(item)
        max_cmd_len = max(max_cmd_len, get_cwidth(cmd_text))
        parsed.append((abs_index, cmd_text, meta_text))

    # Largeur de la colonne commande (bornée pour préserver l'espace description)
    col_width = max(12, min(max_cmd_len + 2, 28))

    fragments: list[tuple[str, str]] = []

    for abs_index, cmd_text, meta_text in parsed:
        is_selected = (selected_index is not None and abs_index == selected_index)

        # Indicateur de curseur
        if is_selected:
            fragments.append((f'bold fg:{COLOR_CYAN}', ' › '))
            # Commande sélectionnée : cyan éclatant, aucun fond opaque
            cmd_display = cmd_text.ljust(col_width)
            fragments.append((f'bold fg:{COLOR_CYAN}', cmd_display))
        else:
            fragments.append(('', '   '))
            # Commande standard : orange éclatant UCHAMBUZI (#E85D26)
            cmd_display = cmd_text.ljust(col_width)
            fragments.append((f'bold fg:{COLOR_ORANGE}', cmd_display))

        # Description alignée en gris clair (#94A3B8)
        # Bornage en largeur pour éviter les retours à la ligne intempestifs
        prefix_len = 3 + col_width + 1
        available_desc_width = max(10, width - prefix_len - 2)
        if get_cwidth(meta_text) > available_desc_width:
            # Tronquer proprement avec ellipse
            truncated = ''
            for ch in meta_text:
                if get_cwidth(truncated + ch) > available_desc_width - 1:
                    break
                truncated += ch
            meta_display = truncated + '…'
        else:
            meta_display = meta_text

        # Indicateur de défilement discret si pertinent sur la dernière/première ligne
        scroll_hint = ''
        if total > max_items:
            if abs_index == start_idx and start_idx > 0:
                scroll_hint = f'  (↑ {start_idx} de plus)'
            elif abs_index == end_idx - 1 and end_idx < total:
                remaining = total - end_idx
                scroll_hint = f'  (↓ {remaining} de plus)'

        if scroll_hint and get_cwidth(meta_display + scroll_hint) <= available_desc_width:
            meta_display += scroll_hint

        fragments.append((f'fg:{COLOR_GRAY}', f" {meta_display}\n"))

    return FormattedText(fragments)


def render_shortcuts_help(width: int = 80) -> FormattedText:
    """Génère le panneau d'aide des raccourcis clavier quand l'utilisateur tape '?'."""
    shortcuts: list[tuple[str, str]] = [
        ('Entrée', 'Valider la commande ou soumettre la question à l\'IA'),
        ('Alt+Entrée / Ctrl+N', 'Saut de ligne (saisie multiligne libre)'),
        ('Tab / Maj+Tab', 'Naviguer dans les suggestions de commandes'),
        ('Shift+Tab', 'Rotation rapide du pôle (OSINT → Red → Blue → Purple → Assist)'),
        ('Échap', 'Fermer l\'autocomplétion ou interrompre la réponse IA'),
        ('Échap Échap', 'Recharger le dernier message saisi pour édition rapide'),
        ('Ctrl+O / Ctrl+T', 'Développer la dernière sortie d\'outil (/details)'),
        ('Ctrl+C', 'Vider la saisie (double appui rapide < 2s pour quitter)'),
        ('/', 'Ouvrir le menu interactif des commandes slash'),
        ('?', 'Afficher cette aide des raccourcis clavier'),
    ]

    fragments: list[tuple[str, str]] = [
        (f'bold fg:{COLOR_CYAN}', ' ◈ Raccourcis clavier interactifs UCHAMBUZI :\n'),
    ]

    max_key_len = max(get_cwidth(k) for k, _ in shortcuts) + 2
    for key, desc in shortcuts:
        fragments.append(('', '   '))
        fragments.append((f'bold fg:{COLOR_ORANGE}', key.ljust(max_key_len)))
        available = max(10, width - max_key_len - 6)
        if get_cwidth(desc) > available:
            desc = desc[:available - 1] + '…'
        fragments.append((f'fg:{COLOR_GRAY}', f' {desc}\n'))

    return FormattedText(fragments)


def render_menu_from_buffer(buffer: Any, width: int = 80, max_items: int = 8) -> FormattedText:
    """Inspecte l'état du buffer prompt_toolkit et rend le menu approprié.

    - Si la complétion est active : menu des suggestions
    - Si l'invite est '?' : aide des raccourcis clavier
    - Sinon : FormattedText vide
    """
    if buffer is None:
        return FormattedText([])

    complete_state = getattr(buffer, 'complete_state', None)
    if complete_state and getattr(complete_state, 'completions', None):
        return format_completion_menu(
            completions=complete_state.completions,
            selected_index=getattr(complete_state, 'complete_index', None),
            width=width,
            max_items=max_items,
        )

    text = getattr(buffer, 'text', '')
    if text.strip() == '?':
        return render_shortcuts_help(width=width)

    return FormattedText([])
