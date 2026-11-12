# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_activity.py
# Role          : Ligne d'activite dynamique et telemetrie IA pour le REPL
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Formatage en temps réel de l'activité, spinners animés et télémétrie des jetons."""

import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Glyphes du spinner braille (10 étapes)
BRAILLE_SPINNER = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
SPINNER_FRAMES = tuple(BRAILLE_SPINNER)
DEFAULT_SPINNER_SPEED = 8.0  # 8 images / seconde
DEFAULT_HINT = 'Échap pour interrompre'
HINT_MIN_WIDTH = 65

# Verbes contextuels selon le type d'opération
OPERATION_VERBS = {
    # Génération IA
    'ai': 'Rédaction…',
    'ia': 'Rédaction…',
    'chat': 'Rédaction…',
    'generation': 'Rédaction…',
    'prompt': 'Rédaction…',
    'redaction': 'Rédaction…',
    'rédaction': 'Rédaction…',
    'model': 'Rédaction…',
    # Analyse forensique
    '/analyze': 'Analyse forensique…',
    'analyze': 'Analyse forensique…',
    '/analyse': 'Analyse forensique…',
    'analyse': 'Analyse forensique…',
    '/indicator': 'Analyse forensique…',
    'indicator': 'Analyse forensique…',
    '/indice': 'Analyse forensique…',
    'indice': 'Analyse forensique…',
    # Recherche documentaire
    '/search': 'Recherche documentaire…',
    'search': 'Recherche documentaire…',
    '/recherche': 'Recherche documentaire…',
    'recherche': 'Recherche documentaire…',
    'doc': 'Recherche documentaire…',
    '/doc': 'Recherche documentaire…',
    'documentaire': 'Recherche documentaire…',
    # Audit anti-injection
    '/audit': 'Audit anti-injection…',
    'audit': 'Audit anti-injection…',
    'anti-injection': 'Audit anti-injection…',
    'injection': 'Audit anti-injection…',
    # Vérification des outils Kali
    '/tools': 'Vérification des outils…',
    'tools': 'Vérification des outils…',
    '/outils': 'Vérification des outils…',
    'outils': 'Vérification des outils…',
    # Exécution approuvée
    'command': 'Exécution approuvée…',
    'commande': 'Exécution approuvée…',
    'exec': 'Exécution approuvée…',
    'execution': 'Exécution approuvée…',
    'exécution': 'Exécution approuvée…',
    'run': 'Exécution approuvée…',
    # Interruption
    'interrupt': 'Interruption en cours…',
    'interruption': 'Interruption en cours…',
    'cancel': 'Interruption en cours…',
    'echap': 'Interruption en cours…',
    'échap': 'Interruption en cours…',
    'ctrl+c': 'Interruption en cours…',
}


def get_operation_verb(operation: Optional[str]) -> str:
    """Retourne le verbe contextuel associé à une opération ou une commande."""
    if not operation:
        return 'Rédaction…'
    key = str(operation).strip().lower()
    if key in OPERATION_VERBS:
        return OPERATION_VERBS[key]
    if not key.startswith('/') and ('/' + key) in OPERATION_VERBS:
        return OPERATION_VERBS['/' + key]
    if str(operation).strip() in OPERATION_VERBS.values():
        return str(operation).strip()
    return str(operation).strip()


def get_spinner_frame(time_or_step: Union[int, float, None] = None, speed: float = DEFAULT_SPINNER_SPEED) -> str:
    """Retourne la glyphe du spinner braille selon le temps (secondes) ou l'étape (entier)."""
    if time_or_step is None:
        time_or_step = time.monotonic()
    if isinstance(time_or_step, int):
        idx = time_or_step % len(SPINNER_FRAMES)
    else:
        idx = int(float(time_or_step) * speed) % len(SPINNER_FRAMES)
    return SPINNER_FRAMES[idx]


def normalize_status(status: Union[str, bool]) -> str:
    """Normalise un statut d'opération en chaîne standard ('Terminé', 'Interrompu', 'Échec')."""
    if status is True:
        return 'Terminé'
    if status is False:
        return 'Échec'
    s = str(status).strip()
    s_lower = s.lower()
    if s_lower in ('termine', 'terminé', 'done', 'success', 'ok'):
        return 'Terminé'
    if s_lower in ('interrompu', 'interrupted', 'cancel', 'cancelled', 'echap', 'échap', 'ctrl+c'):
        return 'Interrompu'
    if s_lower in ('echec', 'échec', 'fail', 'failed', 'error', 'erreur'):
        return 'Échec'
    return s


def format_tokens(tokens: int) -> str:
    """Formate une quantité de jetons générés ou traités (ex: '↑ 312 jetons')."""
    label = 'jeton' if tokens == 1 else 'jetons'
    return f"↑ {tokens} {label}"


def format_context_usage(used_tokens: int, max_tokens: int) -> str:
    """Formate le pourcentage d'utilisation du budget de contexte (ex: 'ctx 82%')."""
    if not isinstance(used_tokens, (int, float)) or not isinstance(max_tokens, (int, float)):
        raise TypeError("used_tokens et max_tokens doivent être des nombres.")
    if max_tokens <= 0:
        return "ctx 0%"
    pct = round((used_tokens / max_tokens) * 100)
    pct = max(0, min(100, pct))
    return f"ctx {pct}%"


def format_activity_line(
    operation: str = 'ai',
    elapsed: float = 0.0,
    tokens: Optional[int] = None,
    width: Optional[int] = 80,
    *,
    spinner: Optional[str] = None,
    spinner_time: Optional[float] = None,
    can_interrupt: bool = True,
    hint: str = DEFAULT_HINT,
) -> str:
    """Formate la ligne d'activité active avec spinner, verbe, temps, jetons et astuce.

    Exemples:
      '⠋ Rédaction… (4 s · Échap pour interrompre)'
      '⠋ Rédaction… (4 s · ↑ 312 jetons · Échap pour interrompre)'
      '⠋ Rédaction… (4 s · ↑ 312 jetons)'  [si width < 65]
    """
    if spinner is None:
        spinner = get_spinner_frame(spinner_time)
    verb = get_operation_verb(operation)

    # Eléments entre parenthèses
    details: List[str] = [f"{int(round(elapsed))} s"]

    if tokens is not None and tokens > 0:
        details.append(format_tokens(tokens))

    # Tronquer l'astuce responsive si largeur < 65 colonnes ou interruption désactivée
    if can_interrupt and hint and (width is None or width >= HINT_MIN_WIDTH):
        details.append(hint)

    inside = " · ".join(details)
    line = f"{spinner} {verb} ({inside})"

    # Protection contre le débordement strict si largeur définie
    if width is not None and len(line) > width:
        if width > 3:
            return line[:width - 1] + '…'
        return line[:width]

    return line


def format_completion(
    status: Union[str, bool] = 'Terminé',
    elapsed: float = 0.0,
    tokens: Optional[int] = None,
    *,
    width: Optional[int] = None,
) -> str:
    """Format de fin d'opération / fin de tour (ex: '⎿ Terminé · 4.2 s').

    Variantes :
      '⎿ Terminé · 4.2 s'
      '⎿ Interrompu · 1.5 s'
      '⎿ Échec · 0.8 s'
      '⎿ Terminé · 4.2 s · ↑ 312 jetons'  [si tokens fournis]
    """
    stat_str = normalize_status(status)
    res = f"⎿ {stat_str} · {elapsed:.1f} s"
    if tokens is not None and tokens > 0:
        res += f" · {format_tokens(tokens)}"
    if width is not None and len(res) > width:
        if width > 3:
            return res[:width - 1] + '…'
        return res[:width]
    return res


class ActivityTracker:
    """Gestionnaire d'état de l'activité en temps réel et télémétrie des jetons."""

    def __init__(
        self,
        operation: str = 'ai',
        *,
        tokens: Optional[int] = None,
        can_interrupt: bool = True,
        hint: str = DEFAULT_HINT,
        speed: float = DEFAULT_SPINNER_SPEED,
        start_time: Optional[float] = None,
    ):
        self.operation = operation
        self.verb = get_operation_verb(operation)
        self.tokens = tokens
        self.can_interrupt = can_interrupt
        self.hint = hint
        self.speed = speed
        self.start_time = start_time if start_time is not None else time.monotonic()
        self.end_time: Optional[float] = None
        self.is_active = True
        self.status: Optional[str] = None
        self.stats: Dict[str, Any] = {}

    @property
    def elapsed(self) -> float:
        """Retourne le temps écoulé en secondes."""
        if self.end_time is not None:
            return max(0.0, self.end_time - self.start_time)
        return max(0.0, time.monotonic() - self.start_time)

    def set_operation(self, operation: str) -> None:
        """Met à jour l'opération et son verbe contextuel."""
        self.operation = operation
        self.verb = get_operation_verb(operation)

    def update_tokens(self, tokens: int) -> None:
        """Définit le nombre absolu de jetons."""
        self.tokens = tokens

    def add_tokens(self, count: int) -> None:
        """Ajoute des jetons au compteur existant."""
        self.tokens = (self.tokens or 0) + count

    def update_stats(self, stats: Dict[str, Any]) -> None:
        """Intègre les statistiques retournées par le moteur local (Ollama)."""
        if isinstance(stats, dict):
            self.stats.update(stats)
            if 'eval_count' in stats and stats['eval_count'] is not None:
                self.tokens = stats['eval_count']

    def render(self, width: int = 80, timestamp: Optional[float] = None) -> str:
        """Génère la ligne d'activité courante."""
        t = timestamp if timestamp is not None else time.monotonic()
        elapsed = self.elapsed if self.end_time is not None else max(0.0, t - self.start_time)
        spinner = get_spinner_frame(t, speed=self.speed)
        return format_activity_line(
            self.verb,
            elapsed=elapsed,
            tokens=self.tokens,
            width=width,
            spinner=spinner,
            can_interrupt=self.can_interrupt,
            hint=self.hint,
        )

    def render_pt(self, width: int = 80, timestamp: Optional[float] = None) -> List[Tuple[str, str]]:
        """Génère les fragments colorés pour Prompt_Toolkit."""
        t = timestamp if timestamp is not None else time.monotonic()
        elapsed = self.elapsed if self.end_time is not None else max(0.0, t - self.start_time)
        spinner = get_spinner_frame(t, speed=self.speed)
        verb = self.verb
        details = [f"{int(round(elapsed))} s"]
        if self.tokens is not None and self.tokens > 0:
            details.append(format_tokens(self.tokens))
        if self.can_interrupt and self.hint and (width is None or width >= HINT_MIN_WIDTH):
            details.append(self.hint)
        inside = " · ".join(details)
        return [
            ('fg:#38BDF8', f"{spinner} "),
            ('bold fg:#E2E8F0', f"{verb} "),
            ('fg:#94A3B8', f"({inside})\n"),
        ]

    def finish(self, status: Union[str, bool] = 'Terminé', tokens: Optional[int] = None) -> str:
        """Termine l'activité et retourne la ligne de fin."""
        self.is_active = False
        if self.end_time is None:
            self.end_time = time.monotonic()
        self.status = normalize_status(status)
        tok = tokens if tokens is not None else self.tokens
        return format_completion(self.status, self.elapsed, tokens=tok)

    def interrupt(self) -> str:
        """Marque l'activité comme interrompue."""
        return self.finish('Interrompu')

    def fail(self) -> str:
        """Marque l'activité comme échouée."""
        return self.finish('Échec')

    def __enter__(self) -> 'ActivityTracker':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            if issubclass(exc_type, KeyboardInterrupt):
                self.interrupt()
            else:
                self.fail()
        elif self.is_active:
            self.finish('Terminé')
        return False
