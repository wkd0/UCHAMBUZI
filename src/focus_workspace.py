# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_workspace.py
# Role          : Validation des repertoires et ressources du contexte
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Chemins explicites : aucune lecture de contenu ni execution."""
import os
from pathlib import Path


def directory(path):
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    if not os.access(p, os.R_OK | os.X_OK) or not (p.stat().st_mode & 0o444) or not (p.stat().st_mode & 0o111):
        raise PermissionError(str(p))
    return p


def resource(root, path):
    root = directory(root)
    p = Path(path).expanduser()
    p = (p if p.is_absolute() else root / p).resolve(strict=True)
    if not p.is_relative_to(root):
        raise ValueError('Ressource hors du repertoire autorise')
    if not p.is_file():
        raise ValueError('La ressource doit etre un fichier')
    if not os.access(p, os.R_OK) or not (p.stat().st_mode & 0o444):
        raise PermissionError(str(p))
    return p
