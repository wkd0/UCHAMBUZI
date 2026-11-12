# Contrat de finalisation et intégration Focus 11

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Contrat historique d'intégration de mission. Il décrit les branches et interfaces de cette étape, non le routage ou l'acceptation de l'interface Textual actuelle.

La branche `work/mission11-settings` conserve `8bee6d5` et ses dépendances 06/08/09.
Elle qualifie le socle `404cc500f43093b5c98c81ecadce8be4ebdf3aa6` et le catalogue 07
`6400487`. Le worktree du coordinateur n'est pas utilisé en écriture.

## Interfaces à raccorder

`InteractiveCatalog(source=None)` expose `profiles()`, `get_profile(id)`,
`scenarios(mode=None)` et `get_scenario(mode, id)`. Par défaut la source est
`FocusScenariosCatalog` de mission 07. Une source injectée reste utilisée ; la
recherche parcourt ses seuls éléments compatibles. Les 24 scénarios du registre
sont les seules offres natives ; `off` est le retour à la conversation libre.
L'ancien ID `timeline` est un alias de `timeline_analysis`, pas une entrée ajoutée.
La propriété `manager` expose le `ScenarioManager` de la source quand il existe.

`SettingsUI` réutilise ce manager et son `ModeEngine`. `select_mode(id)` et
`select_scenario(Scenario | None)` sont appelés **avant** de mettre à jour l'état
visible du contrôleur. Les changements utilisent les transitions du manager 07.
Un changement de mode désélectionne le scénario, notamment s'il devient
incompatible. Les scénarios ne sont pas copiés dans une configuration parallèle.
Les paramètres de scénario natifs par défaut sont ceux validés par le registre 07.

`ScenarioInstructions(manager)` est injecté à la place du point de composition
`FocusAI.mode_engine`. Il expose `compose_active_instructions(active_scenario=...)`
et délègue les autres attributs au moteur 06 réel. La composition utilise le
scénario, sa méthodologie, ses paramètres et ses critères d'achèvement réels du
manager 07. Le texte descriptif du panneau ne sert pas de spécialisation de secours.
Les modules sources des missions 06, 07 et 08 ne sont pas modifiés pour ce pont.

Lors d'une confirmation externe, `freeze()` fige les instructions complètes. Le
transport utilise exactement ces instructions ; une variation de PATH entre
prévisualisation et envoi ne change donc pas les données approuvées. Le consentement
inclut aussi destination, modèle, historique, contexte utilisateur et génération.
Il est consommé une seule fois. Refus, erreur et fin du flux libèrent cet instantané.
Aucune valeur de clé ne figure dans ce contenu ou dans les préférences.

## Contrôleur et éditeur 03

Le patch du contrôleur est livré séparément, calculé contre `404cc500`.
Les points à conserver lors d'une réconciliation ultérieure sont :

1. Factory `FocusExtensions.catalog = InteractiveCatalog` et adaptation des sources
   injectées ; factory `FocusEditor` du socle 03 conservée.
2. Initialisation `SettingsUI` en fin de constructeur ; délégation des commandes
   après `normalize_command`. Les racines slash acceptent tout séparateur blanc.
   `/parametres`, `/modeles`, `/ia`, `/specialite`, `/activite` et `/contexte` sont
   normalisés par l'interface existante.
3. Traitement du collage encadré **avant** Ctrl+S et les autres raccourcis. La cible
   est le champ de valeur actif, sinon l'éditeur conversationnel existant. Les
   séquences de touches définies par le socle et son mode de collage sont conservées.
4. Ctrl+S ouvre les paramètres hors confirmation, fermeture ou question active.
   Les panneaux ont un cycle indépendant du tour IA ; leur ouverture ne remplace
   pas RUNNING. `SettingsUI.key()` traite navigation/annulation et les champs.
5. Les valeurs numériques utilisent une autre instance du même `FocusEditor` de
   mission 03. Le brouillon, son historique et son curseur ne sont pas réutilisés
   comme champ de configuration. `render_panel(width, height)` rend ce champ ou
   le sélecteur. L'éditeur conversationnel visible reste sans curseur actif tant
   que le panneau détient le focus.
6. `select_mode`/`select_scenario` synchronisent le manager réel et l'UI. Pendant
   un tour, les mutations du contexte sont refusées ; consultation et annulation
   restent possibles. Fermer un panneau restaure région et défilement, sans écrire
   dans le brouillon.
7. `interrupt_running_turn()` appelle `SettingsUI.cancel_turn(turn_id)` avant de
   fermer le tour. Les générations externes approuvées sont reliées à
   `_running_task`, pour conserver le chemin d'interruption du contrôleur.
8. La boucle fait avancer les tâches de panneau et les transitions sans attente
   bloquante. Les caractères saisis ne transitent pas dans l'animation. Le dessin
   conserve le cache de lignes ; aucune remise à blanc complète pendant le test
   de streaming et de panneau sans redimensionnement/changement de thème.
9. Le rendu étroit combine le suivi du curseur de mission 03 avec une hauteur
   bornée du panneau. Le décodage portable `TerminalKeys` complète les noms de touches étendues
   de ncurses et les séquences reçues brutes. L’activation/restauration du mode
   de collage ne dépend pas de `curses.define_key`, absent de Python standard.
10. Les paires curses passent par `TerminalStyle.configure_curses`, qui rend le
    style réellement initialisé ou un repli monochrome. L'UI garde ce résultat
    effectif. Le manifeste d'installation est livré dans un patch distinct.

Les conflits rencontrés en reprenant le socle étaient limités au routage du
collage/panneau, au suivi du curseur sur petit écran et à l'union du manifeste.
Aucune méthode de `FocusEditor` ni boucle de corrélation des fragments n'a été
remplacée. La reprise locale du socle est le merge `1ec4673` ; la reprise du
catalogue 07 est `ebbe598`. Le responsable de l'intégration peut appliquer les
patches calculés contre son socle sans reprendre ce merge de qualification.

## Fournisseurs, modèles et sessions

La sélection d'un fournisseur ouvre son catalogue réel ; le choix est engagé
avec un modèle revérifié. Une annulation ou un échec conserve l'ancien choix.
Une annulation pendant la revérification ne doit pas appliquer tardivement son
résultat ni fermer un nouveau panneau. Les erreurs n'affichent ni clé ni réponse
brute du serveur. La liste des fournisseurs est une liste de configurations,
jamais une preuve de connexion permanente.

Les tests transport utilisent un endpoint HTTPS de syntaxe valide, dont la
connexion est remplacée explicitement par HTTP loopback dans le test. Ils couvrent
le secret d'environnement fictif, les paramètres compatibles, les refus, les
réponses 401/429/503, la déconnexion SSE et l'annulation effective. Ils ne démontrent
pas une connexion HTTPS ou une identité de fournisseur externe réelle.

Les confirmations de découverte et de revérification affichent également l'URL
du fournisseur. Leur accord est lié à cette destination et à l'instance du
fournisseur ; ces éléments et la préférence réseau sont revérifiés au démarrage
de l'opération asynchrone. Changer la destination invalide l'accord avant toute
requête de catalogue, comme pour la génération.

Les sessions restent celles de mission 09. Une liste réelle de 65 sessions est
parcourue et une sélection est reprise. Les modèles enregistrés ne sont pas
présentés comme disponibles sans vérification. Aucune nouvelle base de sessions.

## Capacités du terminal

La détection prend en compte TTY, encodage, TERM, NO_COLOR, COLORTERM et les couleurs
annoncées par ncurses. Un terminfo direct à 16777216 couleurs est reconnu même sans
COLORTERM. L'initialisation descend vers 256, puis les couleurs de base, puis le
monochrome si un appel échoue. Les contrôles d'entrée ne deviennent jamais du style.

Les accents RGB de référence présentent un contraste d'au moins 4,5:1 contre le
fond noir ou blanc choisi. Les accents des palettes 256 de référence sont contrôlés
également. Une palette 16 personnalisée par l'émulateur, le rendu des glyphes et
les besoins d'un lecteur d'écran exigent une qualification propre au terminal ;
aucune conformité générale d'accessibilité n'est déclarée.

Le mode monochrome conserve les couleurs par défaut du terminal : ncurses ne
force pas un texte blanc sur fond noir lorsque `NO_COLOR` ou `colors=mono` est
actif. Les couleurs d'erreur des palettes RGB et 256 sont distinctes selon le
fond et sont incluses dans les contrôles de contraste. Les champs de paramètres
défilent vers leur curseur lors d'une saisie longue ou d'un redimensionnement ;
ce défilement concerne uniquement l'éditeur du champ et préserve le brouillon
conversationnel.

## Validation et comparaison UX

Les tests automatiques se lancent avec Python standard :

```sh
python3 -m unittest discover -s tests -p 'test_focus_*.py'
python3 -m unittest discover -s tests
```

Le test TrueColor direct est sauté si `infocmp xterm-direct` est absent ; les autres
capacités restent exercées. La qualification sur Kali utilise une copie temporaire
isolée, sans modification de l'installation de production et sans téléchargement.
Le rapport de livraison donne les nombres exacts, les références Git et les traces
PTY/IA pour la version finalisée.

| Exigence observable des panneaux | Contrôle Focus |
| --- | --- |
| Accès depuis la conversation | Slash anglais et alias français, Ctrl+S pendant le flux. |
| Sélection réelle | Les 24 scénarios passent du sélecteur au manager puis aux instructions du transport. |
| Brouillon et curseur conservés | Éditeur 03 réel, navigation, valeur numérique invalide/valide, collage et annulation. |
| Pas d'offre disponible inventée | Catalogues vides, provider désactivé, erreur de catalogue, modèle absent, session corrompue. |
| Défilement et terminal étroit | 500 éléments unitaires, 65 sessions réelles, dimensions répétées et PTY. |
| Pas de clignotement induit par le panneau | Dessin différentiel et comptage des effacements complets dans le PTY sans resize. |
| Actions réseau compréhensibles | Consentements distincts, destination visible, contenu figé et annulation réelle. |

Les [commandes OpenAI](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
et le [mode interactif Claude Code](https://code.claude.com/docs/en/interactive-mode)
servent de références pour l'accès clavier et la préservation de l'édition.
Ces exigences sont vérifiées sur Focus. Les deux produits n'ont pas fait l'objet
ici du même benchmark PTY, de latence ni d'accessibilité : aucune parité globale
n'est revendiquée. Focus garde les mutations du moteur différées jusqu'à la fin
d'un tour, même si son panneau peut rester ouvert pendant ce tour.


## Correctif de décodage trouvé en recette réelle

Les essais PTY avec Ollama ont révélé que `curses.define_key` du socle 404 n’existe
pas dans les Python Ubuntu et Kali testés. Son bloc de registration empêchait
aussi l’activation du mode de collage ; le test antérieur qui retrouvait le mot
« seconde » ne prouvait pas la reconnaissance des délimiteurs du collage.

`focus_terminal_keys.TerminalKeys` est un décodeur sans attente bloquante. Il
reconnaît les noms ncurses `kHOM5`, `kEND5`, `kLFT3`, `kRIT3` et les séquences
brutes Ctrl+Début/Fin, Alt+Gauche/Droite et de collage. Les fragments sont conservés
pendant une fenêtre de 25 ms ; Échap isolé est libéré par la boucle de scrutation,
et les préfixes inconnus ne perdent pas leurs caractères. En collage, seule sa
fermeture est interprétée ; le décodage keypad de ncurses est suspendu jusqu’à
cette fermeture pour préserver aussi les séquences d’échappement littérales.

Le patch du contrôleur remplace uniquement son ancien normalisateur de touches et
son appel inexistant à define_key. Il conserve le traitement des touches de
l’éditeur, le regroupement de frappes et la boucle conversationnelle. Un nouveau
test PTY lit le brouillon et le curseur après fermeture du panneau, prouve les
positions 0/6/10 pour Ctrl+Début, Alt+Gauche/Droite et Ctrl+Fin, puis vérifie un
collage multiligne contenant Ctrl+S sans ouvrir de panneau ni insérer les délimiteurs.
