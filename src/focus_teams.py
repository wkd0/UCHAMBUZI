# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_teams.py
# Role          : Registre unique des Teams et de leur disponibilite
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Registre public des quatre Teams."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Team:
    id: str
    slug: str
    number: int
    name: str
    icon: str
    color: str
    tools_hint: str
    available: bool
    mode_id: str

    @property
    def description(self) -> str:
        return {
            "assist": "Assistant d'investigation générale et dialogue IA",
            "osint": "Renseignement d'origine sources ouvertes",
            "red": "Audit offensif et cartographie",
            "blue": "Détection, trafic et défense",
            "purple": "Exercices et émulation d'adversaires",
        }.get(self.id, "")

    @property
    def status(self) -> str:
        return "Actif" if self.available else "En développement"

    @property
    def development_notice(self) -> str:
        milestone = "Jalon 5 · " if self.id == "red" else ""
        return (
            f"Le pôle {self.name} est en cours de développement. "
            f"{milestone}Outils prévus : {self.tools_hint}.\n\n"
            "Pour vos investigations courantes, tapez /team osint."
        )

ASSIST_COLOR = "#E2E8F0"
ASSIST_LABEL = "Assist"
ASSIST_TEAM = Team("assist", "assist", 0, "Assist", "", "#E2E8F0", "assistance générale · dialogue IA", True, "assist")

TEAMS: tuple[Team, ...] = (
    Team("osint", "osint", 1, "OSINT Team", "", "#38BDF8", "whois · dig · exiftool", True, "intel"),
    Team("red", "red", 2, "Red Team", "", "#EF4444", "nmap · nuclei · nikto · testssl", False, "assess"),
    Team("blue", "blue", 3, "Blue Team", "", "#3B82F6", "tshark · zeek · suricata", False, "defend"),
    Team("purple", "purple", 4, "Purple Team", "", "#C084FC", "MITRE ATT&CK · Atomic Red · Sigma", False, "validate"),
)

def get_team(key) -> Team | None:
    """Résout identifiant, slug ou numéro public."""
    value = str(key).strip().lower()
    if value in ("0", "assist", "assistant"):
        return ASSIST_TEAM
    return next((t for t in TEAMS if value in (t.id, t.slug, str(t.number))), None)

def active_teams() -> tuple[Team, ...]:
    return tuple(t for t in TEAMS if t.available)
