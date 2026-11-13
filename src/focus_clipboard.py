# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_clipboard.py
# Role          : Repli graphique pour une demande explicite de copie
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
import os
import shutil
import subprocess


def copy_text(text):
    """Copie explicite exacte, sans shell ni lecture du presse-papiers.

    La sélection native/PRIMARY et Ctrl+Maj+C/V appartiennent au terminal.
    Ce repli sert uniquement les actions de copie de l'application ; sans
    cible graphique ou tmux, l'appelant conserve son repli interne/OSC 52.
    """
    commands = []
    if os.environ.get('WAYLAND_DISPLAY'):
        commands.append(('wl-copy', ['--type', 'text/plain;charset=utf-8']))
    if os.environ.get('DISPLAY'):
        commands.extend([('xclip', ['-selection', 'clipboard']), ('xsel', ['--clipboard', '--input'])])
    if os.environ.get('TMUX'):
        commands.append(('tmux', ['load-buffer', '-']))
    for name, args in commands:
        program = shutil.which(name)
        if program:
            try:
                result = subprocess.run([program, *args], input=text.encode('utf-8'),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                if result.returncode == 0:
                    return name
            except (OSError, subprocess.TimeoutExpired):
                pass
    return None
