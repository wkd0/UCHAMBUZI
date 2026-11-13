# Commandes UCHAMBUZI 2.0.0

Cette référence suit la branche de développement non publiée. Elle comprend
douze copies embarquées dans la candidate privée 2.0.0 ; la stable publique reste 1.0.0.

Saisissez ces commandes dans `uchambuzi` sur Kali. `/` ouvre la complétion.
L'accueil est Assist ; les commandes d'investigation demandent `/team 1`.

| Commande | Fonction |
| --- | --- |
| `/help` | Aide et alias du registre intégré |
| `/team` ou `/mode` | Sélecteur Assist (0), OSINT (1), Red (2), Blue (3), Purple (4) |
| `/team osint` ou `/team 1` | Activer OSINT ; rappel légal distinct des approbations d'outils |
| `/status` | Moteur, outils et dossier |
| `/theme [nom ou numéro]` | Sélecteur et aperçu des huit palettes |
| `/ai` | Choix du moteur local ou désactivation |
| `/ai off` ; `/ai qwen2.5:3b` | Désactiver l'IA ; choisir un modèle déjà présent |
| `/ai config` ou `/settings` | Choix et configuration Ollama, accès distants nommés OpenAI/Grok Responses ou Claude Code ; test de connexion |
| `/tips` | Afficher ou masquer les conseils contextuels |
| `/models` ou `/settings models` | Sélecteur des modèles locaux |
| `/tools [spécialité ou nom]` | Catalogue interactif par objectif et fiches explicatives |
| `/tools list` ; `/tools all` | Catalogue complet |
| `/tools setup` ou `/tools install all` | Préparer les douze copies embarquées, après accord global |
| `/tools install <nom>` | Installer une copie approuvée ; un paquet Kali peut demander apt |
| `/tools verify <nom>` | Vérifier l'artefact source ; les manifestes installés sont aussi contrôlés à la résolution |
| `/tools update <nom>` ; `/tools remove <nom>` | Maintenance d'une copie après confirmation |
| `/tools import <archive>` | Import local reconnu par son empreinte ; aucune URL arbitraire |
| `/pseudo <pseudo>` | WhatsMyName, Maigret, Blackbird, Social Analyzer, confirmation séparée |
| `/domaine <domaine>` | WHOIS, DNS, gau selon disponibilité |
| `/email <adresse>` | Holehe |
| `/archive <url>` | gau |
| `/photo <chemin>` | Lecture ExifTool et mat2 |
| `/analyze <cible>` | Qualification locale et recommandations |
| `/indicator <type> <valeur>` | Qualification avec type explicite |
| `/target <numéro>` | Proposition d'un hôte dérivé d'un email ou d'une URL |
| `/prepare <numéro>` | Préparer un choix de la dernière analyse, puis demander l'accord d'exécution |
| `/audit <chemin>` | Audit heuristique anti-injection du fichier |
| `/scenario` | Sélecteur de scénario du profil courant |
| `/scenario <alias> <cible>` | Exécuter un playbook par étapes approuvées |
| `/scenario off` | Revenir au mode libre |
| `/investigation` ; `/investigation list` | Sélecteur de dossiers |
| `/investigation status` ; `/investigation log` | État ou journal du dossier actif |
| `/investigation create <id>` ; `/investigation open <id>` ; `/investigation close` | Créer, ouvrir ou fermer un dossier |
| `/terminal` ; `! commande` | Shell Bash libre après approbation |
| `/copy` ; F6 | Copier la sélection ou la dernière réponse |
| `/copy native` ; F7 | Sélection native du terminal, puis Ctrl+Maj+C ; répéter pour réactiver la souris de l’application |
| `/report` | Export Markdown du dossier vérifié |
| `/search <texte>` | Recherche documentaire locale |
| `/methods [list ou action]` | Consultation et revue humaine des méthodes |
| `/details [numéro]` ; `/details search <texte>` | Consulter ou rechercher les résultats numérotés |
| `/copy commande` | Copier la dernière commande présentée pour approbation |
| `/context [numéro ou off]` | Choix du contexte technique |
| `/history` | Historique de saisie de la session |
| `/usage` ou `/tokens` | Budget en octets et compteurs de tokens |
| `/reset` | Réinitialiser la conversation courante |
| `/clear` ou `/cls` | Effacer la vue et réafficher l'accueil |
| Échap / Ctrl+C | Interrompre une génération IA |
| `/exit` ou `/quit` | Quitter |

Les six alias de playbook sont `domaine`, `image`, `email-pseudo`, `exposition`,
`telephone`, `archives`. Exemple local : `/scenario telephone +12025550123`.
Le playbook `email-pseudo` attend un pseudonyme ; pour un email, utiliser `/email`.
Le menu `/scenario` sélectionne un contexte ; ajouter une cible à la commande
pour démarrer les étapes d'un playbook. Une étape absente, bloquée ou refusée
reste non exécutée, même si le parcours arrive à son terme.

Un domaine, email, URL, pseudo reconnu ou chemin d'image accessible saisi seul
en OSINT suit le raccourci correspondant. En Assist, le texte reste une demande
conversationnelle. Les réponses de Red, Blue et Purple sont des messages locaux
d'indisponibilité. Les anciens huit profils ne constituent pas huit Teams actives.

Les filtres `/tools` sont `domain`, `infra`, `person`, `social`, `media`, `leaks`,
`web_archive`. Une présence au catalogue ne garantit pas un outil installé.
Aucune sortie d'outil ni réponse IA n'est exécutée comme commande libre.

## Confirmation, dossiers et réglages

Pour une approbation, taper `o` puis Entrée ; Entrée seule ou `n` refuse.
`/investigation open` ne demande pas de formulaire de cadre d'enquête. Ouvrir un dossier
avant les opérations permet de conserver les analyses, préparations et résultats.
Le journal est en clair et horodaté UTC, sans chaînage ni empreinte de traçabilité
SHA-256. Les contrôles de structure et de révision ne constituent pas une
vérification cryptographique et ne détectent pas toute modification du contenu.

Les préférences de lancement et les dossiers d'enquête sont dans
`<Documents XDG>/uchambuzi-data/`. Les copies d'outils gérées sont dans
`~/.local/share/uchambuzi-data/tools/` et l'historique Prompt Toolkit dans
`${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/`. Voir [installation](installation.md).
Les réglages interactifs IA et thème sont sous `${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/config/settings.json`. Les réglages explicites de lancement priment sur les valeurs sauvegardées.

Les raccourcis d'édition, la molette et le streaming sont détaillés dans le
[guide Textual](focus-textual-ux.md). Ctrl+C vide un brouillon ; sur saisie vide,
il interrompt la génération ou arme la sortie au repos. Ctrl+D quitte.


### Reprendre une conversation

Après création ou ouverture d’un dossier, le sélecteur propose de continuer sans
sauvegarde, de créer une conversation sauvegardée ou de reprendre une conversation
du dossier. La reprise contrôle structure, révision et association au dossier, sans empreinte SHA-256. Elle ne
rétablit aucune autorisation, aucun contexte d’outil ni réponse partielle. Les
échanges sont stockés sans chiffrement ; la détection de secrets reste partielle.
Voir les [emplacements et limites de conservation](installation.md#données-et-conservation).

### Dossiers, terminal libre et copie

`/investigation` ouvre le gestionnaire. Sélectionner « Créer un dossier » prépare
`/investigation create ` dans le prompt : compléter avec un identifiant et un titre.

```text
/investigation create exercice Premier exercice
/investigation status
/investigation rename Analyse de démonstration
/investigation list
/investigation close
/investigation open exercice
/investigation archive
/investigation open exercice
/investigation delete
```

`create` refuse un identifiant existant ; `open` refuse un identifiant absent.
`rename`, `archive` et `delete` concernent le dossier actif. Archiver ferme le dossier
avec scellement du journal ; le rouvrir permet de reprendre. Supprimer exige une
confirmation explicite et efface aussi les résultats et captures de ce dossier.
Les alias historiques `/case` et `/cases` restent acceptés.

En OSINT, après sélection d’un dossier, `! commande` exécute la syntaxe Bash libre :
pipelines, redirections et commandes interactives sont disponibles. L’approbation
porte sur la commande exacte. `/terminal` ouvre une session Bash interactive :
`exit` revient à UCHAMBUZI. Cette session est approuvée à son ouverture ; ses
commandes suivantes ne demandent pas une confirmation UCHAMBUZI individuelle.
Le shell dispose des droits de l’utilisateur Kali et peut utiliser sudo.

Chaque invocation commence dans `workspace/` du dossier actif. Avec `!`, les
changements de répertoire et de variables ne persistent pas entre invocations ;
utiliser `/terminal` pour garder cet état jusqu’à `exit`. Le shell est libre et
peut écrire ailleurs ; seuls sa capture et les fichiers conservés dans le dossier
sont rattachés à l’enquête. Aucun code proposé par l’IA n’est exécuté automatiquement.

Les captures brutes sont conservées dans `shell/`, avec horodatage et code
de retour inscrits au journal, sans empreinte de traçabilité. Le dernier extrait (24 000 octets maximum) devient
un contexte non fiable pour une question à l’IA ; `/context off` le retire.
Le journal d’une session interactive conserve une capture terminal, pas une liste
structurée de toutes les commandes internes. Une session libre peut modifier ses
propres fichiers : le journal local n’est pas une preuve d’inaltérabilité.

Sélectionner une réponse à la souris puis Ctrl+C copie le texte sélectionné.
F6 ou `/copy` copie la sélection, sinon la dernière réponse IA, sinon la dernière
sortie d’outil. L’envoi utilise OSC 52 et, dans une session graphique compatible,
xclip, xsel ou wl-copy si disponible. Si le terminal ne prend pas en charge ce
protocole, F7 puis sélection et Ctrl+Maj+C permettent la copie native du terminal,
même en SSH ; F7 réactive ensuite menus et molette. Maj+sélection fonctionne
également avec les terminaux qui proposent ce raccourci.


À la première frappe de `!` dans un prompt vide, la saisie passe en **Shell mode** :
préfixe `!`, fond distinct selon le thème courant et indication du mode. Entrée
prépare la commande pour approbation ; Échap revient à la conversation en conservant
le brouillon. Retour arrière dans un prompt shell vide quitte aussi ce mode.
Le collage de `! commande` et le rappel d’une commande shell réactivent ce mode.
Après l’envoi, le prompt revient à la conversation.


### Choisir et utiliser un outil

`/tools` ouvre le catalogue interactif en OSINT ; `/tools maigret` ouvre directement
sa fiche. Les sept objectifs et la liste complète sont consultables même quand
une copie n’est pas disponible. La découverte locale se déroule en arrière-plan.

Chaque fiche présente le rôle de l’outil, pourquoi le choisir, l’indice attendu,
les sorties attendues, les limites, le réseau, le niveau du catalogue et son état.
L’aide affiche les options qualifiées et les références locales disponibles.

Pour Maigret, Blackbird, Social Analyzer, Holehe, gau et PhoneInfoga, renseigner
l’indice puis choisir **Préparer**. Une commande individuelle exacte est construite
et soumise à approbation. Un dossier actif est requis. La commande travaille dans
`workspace/` ; stdout et stderr sont consignés dans le journal et un extrait
borné devient contexte non fiable pour une question à l’IA. Les fichiers natifs
restent soumis au comportement propre de l’outil ; Blackbird utilise sa copie de
travail protégée et ses rapports internes ne constituent pas des exports persistants.
Le parcours accompagné est limité à 30 secondes ; utiliser le shell pour une
session plus longue ou d’autres options.

```text
/tools run maigret pseudo_exercice
/tools run holehe analyste@example.org
/tools run gau example.org
/tools run phoneinfoga +12025550123
```

PhoneInfoga utilise ici uniquement l’analyse locale du numéro, avec les scanners
réseau et à clé désactivés : la commande proposée est passive et sans réseau,
même si le catalogue classe prudemment l’outil complet comme actif.

**Shell** remplit le mode `!` avec l’exécutable vérifié et une commande modifiable.
Sans indice, `--help` est préparé. Rien n’est exécuté avant Entrée puis approbation.
Les exécutables privés n’ont donc pas besoin d’être dans le PATH du terminal.
Les boutons **Installer** et **Vérifier** utilisent les opérations existantes et
actualisent ensuite l’état de la fiche. Une entrée sans artefact approuvé reste
indisponible et n’est pas installable depuis ce catalogue.

`/tools list` et `/tools all` conservent le tableau texte. Les sous-commandes
existantes setup/install/verify/update/remove/import restent disponibles.
La présence d’une fiche ne signifie pas que toutes les options natives sont intégrées.
