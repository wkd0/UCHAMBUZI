# Focus : paramètres, sélecteurs et transitions

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note pour 0.3.0-beta.2 : ce document décrit des composants ou recettes historiques.
> Le REPL courant présente quatre Teams ; seule OSINT est active.
> Les anciens profils restent internes et ne sont plus proposés par `/mode`.
> Voir [les commandes actuelles](commandes.md) et [les fonctionnalités](fonctionnalites.md).


La mission 11 ajoute des paramètres effectifs à la TUI Focus. Les modifications
agissent sur le moteur IA, les modes, les scénarios, le stockage de sessions ou
le rendu du terminal. Aucun paquet pip n'est nécessaire.

## Utilisation

Lancer `uchambuzi` dans un terminal compatible. Les commandes anglaises restent
la référence ; `normalize_command` conserve notamment `/parametres`, `/modeles`,
`/ia` et `/contexte`.

| Commande | Effet |
| --- | --- |
| `/settings` ou `Ctrl+S` | Ouvrir les paramètres ; Ctrl+S fonctionne aussi pendant un flux IA. |
| `/settings show` | Lire les valeurs et leur portée. |
| `/settings set NOM VALEUR` | Valider puis appliquer une valeur. Chaînes avec espaces possibles. |
| `/team` | Présenter les quatre Teams, OSINT seule active. |
| `/scenario`, `/scenario timeline`, `/scenario off` | Choisir un scénario du catalogue du mode, ou la conversation libre. |
| `/models [FOURNISSEUR]` | Lire le catalogue réel puis choisir un modèle. Aucun téléchargement. |
| `/ai` | Choisir un fournisseur configuré ; sa présence ne prouve pas sa connexion. |
| `/ai configure ID URL_HTTPS VARIABLE_ENV` | Ajouter en mémoire un fournisseur compatible Chat Completions. |
| `/context` | Lire le contexte actif et les préférences de confidentialité. |
| `/context sessions` | Choisir une session existante ; une session corrompue est indisponible. |
| `/context directory` | Choisir le répertoire courant du contexte, son parent ou un sous-répertoire. Rouvrir permet de continuer la navigation. |
| `/context N`, `/context off` | Conserver le parcours de sélection du contexte technique du contrôleur. |

Dans un sélecteur : flèches ou `j`/`k`, Début/Fin, Page précédente/suivante,
Entrée et Échap. `q` annule également. L'élément actif est marqué et son
explication apparaît sous la liste. Les listes vides n'offrent aucune sélection.
Les listes longues montrent une fenêtre qui suit le curseur après redimensionnement.
Échap restitue la région, le défilement et le brouillon ; le curseur de saisie
reste géré par l'éditeur existant. Ctrl+C conserve l'interruption du tour IA,
y compris quand un panneau est ouvert.

Exemples :

```text
/settings set theme light
/settings set colors mono
/settings set unicode off
/settings set reduced_motion true
/settings set history true
/settings set workspace /chemin/de/travail
/models
/settings set temperature 0.3
/settings set max_tokens 512
```

Les paramètres de génération exigent un fournisseur sélectionné et les capacités
correspondantes. Un identifiant de modèle est revérifié à la sélection. Un modèle
passé par `--model` est déclaré « non vérifié » jusqu'à sa première vérification.
Une reprise de session impose une nouvelle sélection de modèle. La présence dans
un catalogue ne garantit ni le chargement futur ni l'acceptation de toutes les
valeurs par un modèle particulier.

## Définitions et persistance

| Paramètres | Portée | Défaut / validation |
| --- | --- | --- |
| `theme` | Utilisateur | `dark` ; choix explicite `dark` ou `light`. |
| `colors` | Utilisateur | `auto` ; plafond `truecolor`, `256`, `16`, ou `mono`. |
| `unicode` | Utilisateur | `auto` ; `on` ne force pas un encodage incompatible, `off` impose ASCII. |
| `animations`, `reduced_motion` | Utilisateur | `true`, `false` ; booléens stricts. |
| `history` | Utilisateur | `false` ; aucune nouvelle conversation sur disque par défaut. |
| `network` | Utilisateur | `local` ; `deny` bloque aussi loopback, `external_confirm` permet les demandes de consentement. |
| `confirmations` | Utilisateur | `always`, seul choix autorisé. |
| `permissions` | Session | `prepare_only`, seul choix autorisé. Aucun droit d'exécution ajouté. |
| `mode`, `scenario` | Session | `assist`, `null` ; validation par le catalogue actif. `off` désactive le scénario. |
| `provider`, `model` | Session | `null` ; catalogue et fournisseur vérifiés. `null` désactive la sélection. |
| `temperature` | Session | `null` ; nombre fini entre 0 et 2 si le fournisseur le permet. |
| `max_tokens`, `context_size` | Session | `null` ; entiers positifs bornés par la mission 08 et ses capacités. |
| `timeout` | Session | Délai du contrôleur, 300 s par défaut ; nombre fini strictement positif, au plus 600 s. |
| `workspace` | Session | `null` ; répertoire existant, lisible et traversable. |

Les booléens acceptent `true`/`false` ou `on`/`off`. Les options inconnues, les
valeurs invalides, les permissions plus larges et les capacités non prises en
charge sont refusées. Le fichier existant est conservé lors d'un rejet.

Les seules préférences utilisateur sont écrites dans
`config/focus-preferences.json` sous la racine résolue par
`focus_storage.default_data_dir`, avec remplacement atomique, fsync et fichier
privé 0600. Un fichier malformé est conservé ; les valeurs transitoires par défaut
restent accessibles, mais l'écriture est désactivée pour cette instance.

L'historique utilise exclusivement `SessionManager` / `Session` de la mission 09,
son verrouillage et ses révisions. L'activation est explicite. Les tours réussis,
le mode, le scénario, le répertoire et les paramètres de génération sont conservés.
Changer de mode ou de scénario sépare les sessions persistées. Revenir au contexte
précédent conserve le fil en mémoire du contrôleur ; les sessions disque peuvent
être reprises par `/context sessions`. Les messages partiels ne rejoignent pas
l'historique transmis au modèle. Désactiver l'historique d'une session active
utilise `Session.set_history(False)`, qui retire ses messages du fichier.

Le répertoire ne déclenche ni lecture automatique ni changement global de
répertoire du processus. Il sert à résoudre les chemins relatifs explicites de
`/audit` et `/indicator file`, et est transmis comme contexte passif à l'IA.
Le répertoire d'une session reprise est revérifié. Le contexte technique choisi
avec `/context N` est enveloppé dans le rôle utilisateur, jamais dans les
instructions système. Le budget du contrôleur est contrôlé avant génération ;
un dépassement ne provoque aucun envoi ni suppression automatique d'historique.

## Confidentialité et fournisseurs

Ollama est configuré sur `127.0.0.1` et le port fourni au contrôleur. Il n'est ni
lancé ni installé automatiquement. Les réponses vides, erreurs et catalogues
absents restent visibles comme tels. La sélection vérifiée est distincte d'un
statut de connexion permanente, qui n'est pas affiché.

Pour un fournisseur externe, configurer son URL HTTPS et le **nom** de sa variable
d'environnement. Aucune valeur de clé ne doit être saisie dans une commande.
Les URLs contenant des identifiants sont refusées. Les secrets restent lus par
`HTTPProvider` au moment des requêtes. La définition du fournisseur reste en
mémoire ; aucune clé ni endpoint n'est ajouté aux préférences utilisateur.

L'accès externe exige `network=external_confirm`, un consentement de découverte,
un consentement de revérification à la sélection, puis une confirmation distincte
pour chaque génération. La prévisualisation inclut fournisseur, modèle, paramètres,
instructions de mode, scénario, historique et message effectivement transmis.
Le consentement est lié à ce contenu et consommé une seule fois. Le paramètre
réseau ne constitue pas un pare-feu système.

Les refus de stockage de contenu sensible de la mission 09 sont respectés et
signalés sans recopier le secret dans le statut d'erreur. Ils sont heuristiques ;
ce mécanisme ne certifie pas l'absence de tout secret possible dans un texte libre.

## Terminal et animations

Le composant `BrandLogo` de mission 05 reste utilisé. Le logo reste lisible en
monochrome. Les paires curses colorent réellement l'en-tête, les éléments de
navigation et les erreurs ; le fond clair/sombre est un choix explicite.
Aucune détection du fond par une requête OSC n'est utilisée.

`TerminalStyle` limite le rendu aux capacités du flux, de TERM/COLORTERM et de
ncurses. TrueColor exige aussi des couleurs directes dans terminfo/ncurses ;
COLORTERM seul ne suffit pas. Un terminal xterm-256color reçoit la palette 256,
un terminal à huit couleurs utilise les paires de base du mode « 16 », et
`NO_COLOR`, un flux non TTY ou un terminal minimal reçoit le monochrome.
`TerminalStyle.ansi` produit également des séquences contrôlées 24 bits, 256 ou
16 pour les appelants ANSI ; les données reçues ne sont jamais interprétées
comme du style. CSI, OSC, contrôles et bidirectionnels passent par la neutralisation
existante ; le repli ASCII s'applique à tout l'écran sans modifier le texte stocké.

`Animations` écoute les vrais `ModeTransitionEvent` et utilise leur mode cible, leurs glyphes et les durées de `animation_hints`. La transition de
mode garde le glyphe du mode choisi ; scénario et panneau disposent de transitions
courtes distinctes. La durée est plafonnée à 180 ms, 120 ms par défaut. Aucun
sommeil ni thread ne lit le clavier. Désactivation et mouvement réduit rendent
immédiatement l'état final. Une animation n'indique jamais une connexion ou une
progression IA. Sur écran très étroit, son texte peut être tronqué ; l'état final
reste consultable. Les changements de mode/modèle/scénario sont refusés pendant
un tour actif ; la lecture et la navigation du panneau restent possibles.

## Intégration et validation

Socle : `3d05957ec43b0d716cd1d77f340bd729b374bf60`.
Contributions reprises dans cette branche :

- modes `d941077` → `7e62b63` ;
- IA `3c9b0713810cddc40fe63784fd0849664e6939e4` → `6e48229` ;
- sessions `43bccf134a7f86a430449dfd5fdf865fd8f4af58` → `6396b55` ;
- branding `4f2facf66b913f6a188a798b75cb81ed2618244d`, déjà fourni par le socle.

Le contrôleur conserve l'éditeur, ses protocoles, la corrélation des événements et
les points d'injection. `SettingsUI` raccorde les modules autonomes. Le catalogue
réel de mission 07 (`6400487`) fournit les 24 scénarios. `InteractiveCatalog`
adapte sa recherche à la signature du contrôleur ; un catalogue injecté vide
ne produit aucun scénario ajouté, hormis le retour explicite en conversation libre.
Les instructions complètes proviennent de `ScenarioManager`, via un adaptateur
injecté dans le moteur 08. Le socle éditeur 03 (`404cc500`) est qualifié conjointement.
Les moteurs et runtimes explicitement injectés conservent leur chemin d'exécution
historique ; leur configuration de génération/modèles ne prétend pas implémenter
l'interface de mission 08. Le sélecteur de rendu personnalisé reste injectable.
`installation.PAYLOAD` contient les nouveaux modules et leurs dépendances.

```sh
python3 -m unittest discover -s tests -p 'test_focus_*.py'
python3 -m unittest discover -s tests
```

Résultat de la livraison initiale du 8 novembre 2026 : **99 tests Focus** et **361 tests de la suite
complète** réussis. Les tests couvrent lecture, défauts, rejets, modes et scénarios effectifs,
capacités IA, fournisseur désactivé/non connecté, modèle absent, liste vide,
500 éléments, touches de navigation/annulation, dimensions répétées jusqu'à
1×1, focus et curseur, Unicode/ASCII, monochrome/NO_COLOR, paires curses, consentements,
absence d'écho des secrets, sessions et reprise de génération, contexte et budget,
animations des profils historiques et saisie concurrente. Les essais PTY vérifient 256 et
16 couleurs, changement de thème persistant, streaming avec panneau, redimensionnements,
restauration canonique/écho et **la TUI installée** dans un HOME temporaire.

Recette locale réelle : catalogue Ollama `qwen2.5:3b`, sélection, température 0,
limite 256, mode Engineer ; réponse complète reçue avec onze rendus de la réponse (fragments puis état final),
panneau maintenu ouvert et brouillon conservé. Les rendus textuels ont été inspectés
visuellement en thèmes clair/sombre et ASCII. Les aperçus produits à partir du
renderer ne sont pas des captures d'un émulateur de terminal.

Les premiers contrôles ci-dessus ont été complétés par la qualification finale
décrite dans [le contrat d’intégration](focus-settings-integration.md). Aucun
service HTTPS externe réel n’est sollicité ; ses transports sont simulés sur
loopback avec une variable d’environnement fictive. Le terminfo `xterm-direct`
est absent de l’hôte Ubuntu et présent sur Kali ; les tests directs y sont exécutés. Les contrastes des couleurs de
base dépendent aussi de la palette personnalisée du terminal. Aucun test ne
certifie l'ensemble des émulateurs, les lecteurs d'écran ou une conformité WCAG.

## Comparaison avec les interfaces de référence

Versions locales identifiées : Codex CLI `0.167.0`, Claude Code `2.1.319`.
La comparaison suivante porte sur les interactions documentées et les contrôles
réalisés sur Focus. Les interfaces de référence n'ont pas subi ici le même
protocole PTY chronométré ; aucune parité globale n'est revendiquée.

| Interaction | Référence documentée | Résultat Focus |
| --- | --- | --- |
| Modèle et permissions depuis la conversation | Codex propose des commandes slash et un sélecteur de permissions. | `/models`, `/mode`, `/settings` fonctionnels ; permissions volontairement bornées. |
| Préserver la saisie à la fermeture d'un panneau | Claude Code décrit la conservation du mode d'édition et du curseur. | Brouillon, position du curseur et région contrôlés par tests ; éditeur réel de mission 03 qualifié lors de la finalisation. |
| Paramètres pendant une opération | Claude Code documente des réglages appliqués à différents moments du tour. | Panneau consultable pendant le flux ; changements du contexte/moteur refusés jusqu'à sa fin. |
| Catalogues, listes longues et défilement | Point d'évaluation d'ergonomie pour Focus ; aucune mesure comparative effectuée. | Catalogue réel, erreurs explicites, liste de 500 éléments et tailles répétées testées. |

Sources consultées : [commandes développeur OpenAI](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
et [mode interactif Claude Code](https://code.claude.com/docs/en/interactive-mode).
L'autocomplétion globale, les réglages d'éditeur avancés, les aides à l'accessibilité
et l'ensemble du comportement des références ne sont pas couverts par la mission 11.


## Finalisation après le commit initial

La livraison initiale `8bee6d5` est conservée. La finalisation utilise le catalogue
07 et le véritable éditeur 03, protège le brouillon lors de la saisie d’une valeur
numérique, gère l’annulation d’une revérification de modèle et transmet les
annulations de tours externes au transport. Les couleurs directes sont reconnues
même sans COLORTERM lorsque ncurses les annonce ; une initialisation de couleur
en échec descend réellement vers 256, 16 ou monochrome. Les couleurs d’accent
claires/sombres sont distinctes, avec contrôle de contraste sur les valeurs RGB
et les palettes 256 de référence. Le détail des interfaces, patches et vérifications
figure dans [focus-settings-integration.md](focus-settings-integration.md).
