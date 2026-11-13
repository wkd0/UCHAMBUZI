# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : repl_commands.py
# Role          : Registre centralisé des commandes slash, alias et aide REPL
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Définition et registre unique des commandes d'investigation UCHAMBUZI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Command:
    """Définition d'une commande slash avec ses alias et métadonnées."""
    name: str
    aliases: tuple[str, ...] = ()
    summary: str = ""
    usage: str = ""
    group: str = "general"
    background_title: str | None = None
    help_aliases: str | None = None
    help_description: str | None = None

    def __post_init__(self) -> None:
        if not self.usage:
            object.__setattr__(self, 'usage', self.name)
        if self.help_aliases is None:
            aliases_display = ', '.join(self.aliases) if self.aliases else '—'
            object.__setattr__(self, 'help_aliases', aliases_display)
        if self.help_description is None:
            object.__setattr__(self, 'help_description', self.summary)


class CommandRegistry:
    """Registre centralisé garantissant l'unicité et la cohérence des commandes."""

    def __init__(self, commands: Sequence[Command] = ()) -> None:
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}
        for cmd in commands:
            self.register(cmd)

    def register(self, command: Command) -> None:
        name = command.name.lower()
        if name in self._commands:
            raise ValueError(f"Commande déjà enregistrée : {name}")
        self._commands[name] = command
        for alias in command.aliases:
            alias_lower = alias.lower()
            if alias_lower in self._aliases:
                raise ValueError(f"Alias déjà enregistré : {alias_lower}")
            self._aliases[alias_lower] = name

    def get(self, name_or_alias: str) -> Command | None:
        target = self.resolve(name_or_alias)
        return self._commands.get(target.lower())

    def resolve(self, name_or_alias: str) -> str:
        key = name_or_alias.strip().lower()
        return self._aliases.get(key, key)

    def all_commands(self) -> list[Command]:
        return list(self._commands.values())

    def get_documentation_dict(self) -> dict[str, str]:
        return {cmd.name: cmd.summary for cmd in self._commands.values()}

    def get_aliases_map(self) -> dict[str, str]:
        return dict(self._aliases)

    def get_all_slash_commands(self) -> list[str]:
        return sorted(set(list(self._commands.keys()) + list(self._aliases.keys())))

    def get_help_rows(self) -> list[tuple[str, str, str]]:
        return [(cmd.usage, cmd.help_aliases or '—', cmd.help_description or cmd.summary)
                for cmd in self._commands.values()]

    def resolve_command_prefix(self, cmd_text: str) -> tuple[str | None, list[str]]:
        """Résout un préfixe de commande slash parmi les commandes et alias enregistrés.

        Règles :
        - Si vide : (None, [])
        - Si match exact (nom ou alias) : (cmd_exact, [cmd_exact])
        - Si match préfixe unique : (cmd_trouvée, [cmd_trouvée])
        - Si matches multiples vers la même commande canonique : (cmd_trouvée, [cmd_trouvée])
        - Si matches multiples ambigus : (None, [liste_des_matches])
        - Si aucun match : (None, [])
        """
        raw = cmd_text.strip()
        if not raw:
            return (None, [])

        token = raw.split()[0].lower()
        lookup = token if token.startswith('/') else f"/{token}"
        all_cmds = self.get_all_slash_commands()

        # 1. Match exact (priorité absolue)
        if lookup in all_cmds:
            return (lookup, [lookup])

        # 2. Recherche par préfixe
        matches = [c for c in all_cmds if c.startswith(lookup)]
        if not matches:
            return (None, [])

        if len(matches) == 1:
            return (matches[0], [matches[0]])

        # 3. Matches multiples : convergence vers la même commande canonique
        canonical_targets = {self.resolve(c) for c in matches}
        if len(canonical_targets) == 1:
            canonical = next(iter(canonical_targets))
            cmd_found = canonical if canonical in matches else min(matches, key=len)
            return (cmd_found, [cmd_found])

        # 4. Matches multiples ambigus
        return (None, sorted(matches))


OSINT_COMMANDS = frozenset({
    '/tools', '/analyze', '/indicator', '/target', '/prepare', '/audit',
    '/pseudo', '/domaine', '/email', '/archive', '/photo', '/scenario',
    '/methods', '/report', '/investigation', '/terminal',
})


# Définition des commandes UCHAMBUZI (source unique de vérité en anglais)
BUILTIN_COMMANDS: tuple[Command, ...] = (
    Command(name='/tips', summary='Choisir si les conseils sont affichés', usage='/tips', group='general'),
    Command(
        name='/help',
        aliases=(),
        summary="Affiche ce guide des commandes et les raccourcis disponibles",
        usage="/help",
        group="general",
        help_description="Affiche ce guide complet des commandes",
    ),
    Command(
        name='/usage',
        aliases=('/tokens',),
        summary="Affiche l'utilisation des ressources, du contexte et des jetons",
        usage="/usage",
        group="general",
        help_aliases="/tokens",
        help_description="Métriques d'utilisation du contexte et des jetons",
    ),
    Command(
        name='/clear',
        aliases=('/cls',),
        summary="Efface l'écran du terminal et réaffiche la bannière de session",
        usage="/clear",
        group="general",
        help_aliases="/cls",
        help_description="Efface le terminal et réaffiche la bannière",
    ),
    Command(
        name='/status',
        aliases=(),
        summary="Affiche l'état complet du moteur IA, des outils et du dossier",
        usage="/status",
        group="general",
        help_description="État complet du système, moteur IA et dossier",
    ),
    Command(
        name='/team',
        aliases=('/mode',),
        summary="Bascule entre les modes et pôles cyber (Assist, OSINT, Red, Blue, Purple)",
        usage="/team [nom]",
        group="posture",
        help_aliases="/mode",
        help_description="Bascule entre les modes et pôles cyber (Assist, OSINT, Red, Blue, Purple)",
    ),
    Command(
        name='/theme',
        aliases=(),
        summary="Choisit ou affiche la palette de couleurs (Focus, Matrix, Dracula, Nord...)",
        usage="/theme [nom]",
        group="ui",
        help_description="Change la palette (Focus, Matrix, Dracula...)",
    ),
    Command(
        name='/scenario',
        aliases=(),
        summary="Active une activité ou un scénario guidé pour le profil courant",
        usage="/scenario [nom]",
        group="posture",
        help_description="Active une activité guidée spécifique au profil",
    ),
    Command(name='/pseudo', summary='Recherche des profils associés à un pseudonyme', usage='/pseudo <pseudo>', group='investigation'),
    Command(name='/domaine', summary='Reconnaissance passive d’un domaine', usage='/domaine <domaine>', group='investigation'),
    Command(name='/email', summary='Recherche de comptes associés à une adresse', usage='/email <adresse>', group='investigation'),
    Command(name='/archive', summary='Recherche d’URL archivées', usage='/archive <url>', group='investigation'),
    Command(name='/photo', summary='Analyse des métadonnées d’une image', usage='/photo <chemin>', group='investigation'),
    Command(
        name='/analyze',
        aliases=(),
        summary="Analyse un indice (IP, domaine, hash, URL, fichier) et ses outils",
        usage="/analyze <cible>",
        group="investigation",
        background_title="Analyse des indices",
        help_description="Analyse un indice (IP, domaine, hash, fichier)",
    ),
    Command(
        name='/indicator',
        aliases=(),
        summary="Déclare un indicateur technique explicite avec son type",
        usage="/indicator <type> <val>",
        group="investigation",
        background_title="Déclaration et analyse d’indice",
        help_description="Déclare un indicateur technique explicite avec son type",
    ),
    Command(
        name='/target',
        aliases=(),
        summary="Sélectionne un hôte ou un indice dérivé pour analyse",
        usage="/target <n°>",
        group="investigation",
        help_description="Sélectionne un hôte ou un indice dérivé pour analyse",
    ),
    Command(
        name='/prepare',
        aliases=(),
        summary="Prépare une commande d'investigation sans exécution automatique",
        usage="/prepare <n°>",
        group="investigation",
        background_title="Exécution approuvée",
        help_description="Prépare une commande recommandée sous contrôle",
    ),
    Command(
        name='/tools',
        aliases=(),
        summary="Choisit un outil par objectif, explique son rôle et prépare son utilisation",
        usage="/tools [specialite|nom|run <outil> <indice>|setup|install <nom>|verify <nom>]",
        group="investigation",
        background_title="Vérification des outils locaux",
        help_description="Catalogue OSINT, filtre par spécialité ou détail par nom",
    ),
    Command(
        name='/investigation',
        aliases=('/case', '/cases'),
        summary="Gère le dossier d'enquête actif et consulte le journal horodaté UTC",
        usage="/investigation [create <id> [titre]|open <id>|rename <titre>|close|archive|delete|log]",
        group="forensic",
        help_description="Gestion des dossiers d'enquête et journal en clair UTC",
    ),
    Command(name='/copy', summary='Copie la sélection, la réponse ou /copy commande', group='session'),
    Command(name='/terminal', summary='Ouvre un shell Bash libre dans le dossier actif ; exit pour revenir', group='investigation'),
    Command(
        name='/report',
        aliases=(),
        summary="Exporte le dossier vérifié en Markdown local",
        usage="/report",
        group="forensic",
        help_description="Rapport OSINT : cadre, indices, constats et journal en clair UTC",
    ),
    Command(
        name='/audit',
        aliases=(),
        summary="Inspecte un fichier suspect contre les injections de prompt",
        usage="/audit <fichier>",
        group="security",
        background_title="Audit du fichier",
        help_description="Audit de sécurité anti-injection de prompt",
    ),
    Command(
        name='/search',
        aliases=(),
        summary="Recherche documentaire déterministe et pondérée dans le corpus",
        usage="/search <mots>",
        group="investigation",
        background_title="Recherche documentaire locale",
        help_description="Recherche déterministe dans le corpus officiel",
    ),
    Command(
        name='/methods',
        aliases=(),
        summary="Bibliothèque de méthodes d'investigation validées et éprouvées",
        usage="/methods",
        group="investigation",
        help_description="Consulte les méthodes d'investigation validées",
    ),
    Command(
        name='/models',
        aliases=(),
        summary="Affiche les modèles IA locaux installés dans Ollama",
        usage="/models",
        group="ai",
        background_title="Modèles locaux Ollama",
        help_description="Affiche les modèles IA locaux installés dans Ollama",
    ),
    Command(
        name='/ai',
        aliases=(),
        summary="Ouvre le sélecteur du moteur IA, des modèles et de la connexion",
        usage="/ai",
        group="ai",
        help_description="Sélecteur IA : modèle, activation et connexion Ollama",
    ),
    Command(
        name='/settings',
        aliases=(),
        summary="Affiche ou configure les paramètres de session",
        usage="/settings [ai <ollama|openai>|model <nom>|port <port>]",
        group="session",
        help_description="Affiche ou configure les paramètres de session",
    ),
    Command(
        name='/context',
        aliases=(),
        summary="Gère la taille du contexte et le budget mémoire de la session",
        usage="/context [n°|off]",
        group="ai",
        help_description="Gère le contexte technique associé aux messages IA",
    ),
    Command(
        name='/history',
        aliases=(),
        summary="Affiche l'historique des commandes saisies dans cette session",
        usage="/history",
        group="session",
        help_description="Historique des commandes saisies dans cette session",
    ),
    Command(
        name='/reset',
        aliases=(),
        summary="Efface l'historique de la conversation courante",
        usage="/reset",
        group="session",
        help_aliases="—",
        help_description="Réinitialise le contexte de la conversation active",
    ),
    Command(
        name='/exit',
        aliases=('/quit',),
        summary="Quitte proprement l'application UCHAMBUZI",
        usage="/exit",
        group="session",
        help_aliases="/quit",
        help_description="Ferme proprement la session UCHAMBUZI",
    ),
    Command(
        name='/details',
        aliases=(),
        summary="Développe une sortie ou recherche avec /details search <texte>",
        usage="/details [n°|search texte]",
        group="session",
        help_aliases="Ctrl+T",
        help_description="Développe une sortie locale sans la réexécuter",
    ),
)

COMMAND_REGISTRY = CommandRegistry(BUILTIN_COMMANDS)
REGISTRY = COMMAND_REGISTRY

# Exports de rétrocompatibilité stricte avec focus_repl.py
COMMAND_DOCUMENTATION: dict[str, str] = COMMAND_REGISTRY.get_documentation_dict()
ALIASES_MAP: dict[str, str] = COMMAND_REGISTRY.get_aliases_map()
ALL_SLASH_COMMANDS: list[str] = COMMAND_REGISTRY.get_all_slash_commands()


def resolve_command_prefix(
    cmd_text: str,
    registry: CommandRegistry | None = None,
) -> tuple[str | None, list[str]]:
    """Résout un préfixe de commande slash selon le registre des commandes UCHAMBUZI.

    Paramètres :
        cmd_text : Préfixe ou commande complète saisie (ex: '/ex', '/prep', '/exit').
        registry : Registre de commandes optionnel (par défaut COMMAND_REGISTRY).

    Retourne :
        (cmd_exact, [cmd_exact]) si match exact
        (cmd_trouvée, [cmd_trouvée]) si match préfixe unique ou convergent
        (None, [liste_des_matches]) si correspondances multiples et ambiguës
        (None, []) si aucune correspondance
    """
    reg = registry or COMMAND_REGISTRY
    return reg.resolve_command_prefix(cmd_text)



def handle_tools(console, argument="", *, confirm=None):
    """Routeur commun : catalogue A2 et opérations vérifiées A3."""
    from tools_catalog import handle_tools as render, load_catalog
    from tools_installer import ToolsInstaller
    from repl_approval import ask_approval
    import subprocess
    parts = argument.strip().split(maxsplit=1)
    if not parts or parts[0] not in ('install', 'update', 'remove', 'verify', 'import', 'setup'):
        return render(console, argument)
    try:
        manager = getattr(console, '_uchambuzi_case_manager', None)
        installer = ToolsInstaller(load_catalog(), case_manager=manager,
            confirm=confirm or (lambda question: ask_approval(question)),
            output=lambda message: console.print(message, markup=False, highlight=False))
        result = installer.handle(argument.strip())
        console.print('Opération réussie.' if result else 'Opération refusée, annulée ou vérification en échec.', markup=False)
        return result
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        console.print('Opération outils impossible : '+str(exc), markup=False, highlight=False)
        return False
