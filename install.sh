#!/usr/bin/env bash
# ============================================================================
# UCHAMBUZI - Assistant local pour l'investigation numerique
# ============================================================================
# Fichier       : install.sh
# Role          : Installation utilisateur sans dependance additionnelle
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Erreur : python3 (>= 3.10) est requis pour installer UCHAMBUZI." >&2
    exit 1
fi
exec python3 "$ROOT/src/uchambuzi.py" --source "$ROOT" "$@"
