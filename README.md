<p align="center">
  <img src="assets/branding/logo/uchambuzi-lockup-horizontal-opaque.svg" alt="UCHAMBUZI" width="520">
</p>

<p align="center">
  Assistant local pour l’OSINT, le forensic et la cybersécurité.
</p>

UCHAMBUZI est un assistant de terminal qui aide à qualifier des indices,
retrouver les outils adaptés et préparer des opérations d’investigation. Il
garde l’enquêteur dans la boucle : chaque opération proposée est expliquée,
classée passive ou active dans les parcours intégrés, puis soumise à son
approbation avant exécution. Le shell libre est identifié séparément.

**Version : 1.0.0 · Kali Linux amd64 · 12 novembre 2026**

Cette version inclut le catalogue OSINT interactif, le shell libre approuvé,
la reprise des conversations par dossier et les accès IA nommés. Voir la
[qualification V1.0.0](docs/releases/1.0.0.md) et le [changelog](CHANGELOG.md).

[Fonctionnement](#fonctionnement) · [Installation](#installation) ·
[Démarrage rapide](#démarrage-rapide) · [Commandes](docs/commandes.md) ·
[Limites et sécurité](#contrôle-et-traçabilité) · [Documentation](#documentation)

---

## Fonctionnement

Lancez `uchambuzi` pour ouvrir le REPL Textual, rendu avec Rich. L’interface
propose saisie multiligne, historique, complétion des commandes `/`, thèmes,
réponses Markdown et génération IA locale en streaming. Les réponses des
fournisseurs distants apparaissent après leur génération. La sélection à la souris
est copiée au relâchement si le terminal prend en charge le presse-papiers ;
F6 ou `/copy` copie la dernière réponse, `/copy commande` la dernière commande
présentée pour approbation. Les résultats numérotés se développent avec
`/details N` et se recherchent avec `/details search texte`. Le conseil de
saisie s'affiche ou se masque dans le menu `/tips`.

Après ouverture d'une enquête, on peut choisir de sauvegarder une conversation
ou de reprendre une conversation liée à ce dossier. Les échanges sont stockés
localement sans chiffrement, dans le dossier ; leur empreinte est enregistrée
dans le journal SHA-256 et vérifiée à la reprise. Aucune autorisation antérieure
n'est réactivée et les fragments d'une réponse interrompue ne sont pas conservés.
Les opérations restent consultables avec `/investigation log`. La détection de
secrets et d'injections reste partielle. Le journal n'est pas signé ni ancré à
l'extérieur : la restauration simultanée d'un ancien journal et d'une ancienne
conversation ne peut pas être détectée par ce seul mécanisme.

La session commence en **Assist**, pour le dialogue général. Choisissez
`/team 1` pour activer l’**OSINT Team**. Les équipes Red, Blue et Purple sont
présentées dans le sélecteur et restent indisponibles dans cette version.

Les commandes `/analyze` et `/indicator` qualifient localement un indice et
présentent des pistes. Les raccourcis OSINT ouvrent des parcours ciblés :

| Parcours | Exemples de commandes | Outils et fonctions proposés |
| --- | --- | --- |
| Pseudonyme | `/pseudo enquete_demo` | WhatsMyName, Maigret, Blackbird, Social Analyzer |
| Adresse email | `/email analyste@example.org` | Holehe |
| Domaine | `/domaine example.org` | WHOIS, DNS, gau selon disponibilité |
| Archives web | `/archive https://example.org` | gau |
| Image locale | `/photo /chemin/image.png` | Lecture de métadonnées avec ExifTool et mat2 |
| Scénario guidé | `/scenario telephone +12025550123` | Étapes PhoneInfoga locales et liens de recherche |

`/tools` ouvre un catalogue interactif par objectif. Chaque fiche explique le
rôle de l’outil, pourquoi le choisir, les indices attendus, les résultats et les
limites. Pour les six copies embarquées, **Préparer** construit une commande
individuelle soumise à approbation ; **Shell** prépare le chemin vérifié dans la
saisie libre, sans exécution immédiate. Les autres entrées restent consultables
avec leur état et leur niveau d’intégration explicites.

Les six copies tierces embarquées sont **gau, Maigret, Holehe, PhoneInfoga,
Social Analyzer et Blackbird**. Elles sont figées et vérifiées par empreinte
SHA-256. `/tools setup` les prépare à partir des artefacts locaux ; leur présence
au catalogue ne signifie pas qu’elles sont déjà installées.

`/investigation` rassemble les dossiers : créer, ouvrir, renommer, fermer,
archiver ou supprimer après confirmation. En OSINT avec un dossier actif,
`! commande` lance une commande Bash libre après approbation ; `/terminal`
ouvre une session interactive jusqu’à `exit`, y compris pour sudo et les outils
Kali non intégrés au catalogue. Les captures sont conservées dans le dossier et
leur dernier extrait peut être interprété par l’IA locale sur demande.
Le shell garde les droits de l’utilisateur et peut écrire hors du dossier.
L’approbation de `/terminal` couvre la session entière.

## Contrôle et traçabilité

- **Approbation avant action** : une recherche ou commande proposée attend
  `o` puis Entrée. Entrée seule refuse. Les outils absents ou les étapes refusées
  ne sont pas exécutés.
- **Contexte d’enquête** : `/investigation create <id>` ouvre un dossier qui reçoit les
  événements consignés. `/report` exporte un rapport Markdown après contrôle.
- **Intégrité locale** : le journal est horodaté en UTC et chaîné par SHA-256.
  Ce contrôle révèle des altérations de la chaîne conservée ; il ne remplace pas
  une signature externe ni une conservation probatoire indépendante.
- **Données non fiables** : les sorties et fichiers analysés sont traités comme
  des données ; leur contenu n’est pas exécuté comme une commande. La détection
  d’injection reste heuristique.
- **Résultats à recouper** : les services publics peuvent changer, limiter ou
  refuser les requêtes. Une erreur ou un résultat négatif ne prouve pas
  l’absence d’un compte ou d’un indice.

Les parcours OSINT intégrés ne nécessitent ni compte ni clé API. Les recherches
sur des services Internet nécessitent une connexion et une approbation. Le
dialogue IA local utilise Ollama et un modèle déjà installé ;
`redsage-qwen3:8b-dpo` est le modèle local recommandé et choisi par défaut ; il
doit être installé séparément dans Ollama. Il reste en cours de calibration et
ses réponses doivent être vérifiées ; sa licence n'a pas encore été établie pour
la distribution du projet. Un autre modèle installé peut être choisi
dans `/settings` ; ses réglages propres restent ceux de son fournisseur.
`/ai off` laisse disponibles les fonctions déterministes. Voir le
[guide d’installation](docs/installation.md) pour préparer le modèle recommandé.

Le menu `/settings` permet aussi de choisir OpenAI ou Grok via une API compatible
Responses, ou Claude via Claude Code CLI installé séparément. Vous pouvez créer
plusieurs accès nommés, chacun avec son adresse HTTPS, sa famille, son modèle et
sa clé. Les clés saisies sont enregistrées dans un fichier distinct accessible
au seul utilisateur (permissions `0600`) ; ce fichier n'est pas chiffré. Il est
aussi possible d'utiliser le nom d'une variable d'environnement sans enregistrer
la clé. Pour les accès Responses, « Rechercher les modèles » demande votre accord
avant de transmettre la clé à l'adresse indiquée ; une saisie manuelle reste
possible. Pour Claude Code, saisissez le modèle manuellement. Les modèles et
adresses suggérés ne garantissent pas leur disponibilité chez votre fournisseur.
UCHAMBUZI applique des consignes expérimentales adaptées aux familles et aux
modèles reconnus, sans forcer de température. Avant chaque envoi distant, il
présente le contenu préparé et sa destination et demande une approbation. Claude
Code peut ajouter des métadonnées propres à son client.

Pour une question explicite sur les caractéristiques de sa machine, l'assistant
peut lire un inventaire local limité : système, processeur, mémoire et partition
racine. Ces informations concernent la machine qui exécute UCHAMBUZI, pas
nécessairement celle qui héberge Ollama. Le GPU, les autres disques et les
logiciels ne sont pas inventoriés par cette fonction. L'inventaire n'est pas
ajouté automatiquement aux requêtes API distantes ni aux serveurs Ollama configurés
hors loopback ; un tunnel local peut néanmoins relayer Ollama vers une autre machine.

## Installation

Le paquet utilisateur est destiné à **Kali Linux amd64**. Récupérez
`uchambuzi_1.0.0-1_amd64.deb` depuis la
[page des releases de la distribution officielle](https://github.com/wkd0/uchambuzi/releases),
puis installez-le :

```sh
sudo apt install ./uchambuzi_1.0.0-1_amd64.deb
uchambuzi --version
uchambuzi doctor
uchambuzi
```

Textual, Rich et Prompt Toolkit sont fournis par les paquets système. Les
bundles Python des outils embarqués utilisent Python 3.13 et
`python3.13-venv`, même si une version plus récente est le Python principal.
L’installation de ces dépendances système peut nécessiter l’accès aux dépôts
Kali. Une fois les prérequis installés, les copies d’outils se préparent hors
ligne depuis les bundles livrés.

Pour installer depuis les sources ou consulter les emplacements des données,
suivez le [guide d’installation](docs/installation.md). UCHAMBUZI est un
assistant et une interface d’orchestration ; il ne remplace ni les outils
spécialisés ni le jugement de l’enquêteur.

## Démarrage rapide

Dans UCHAMBUZI, sélectionnez l’équipe OSINT, ouvrez un dossier d’exercice et
préparez les copies locales :

```text
/team 1
/investigation create exercice-v1
/tools setup
/tools list
/analyze 192.0.2.1
/report
```

`192.0.2.1` est une adresse réservée à la documentation. `/tools setup` demande
un accord global pour préparer les outils. Chaque opération d’investigation
requiert ensuite sa propre approbation. Pour un premier parcours guidé, essayez
`/pseudo enquete_demo` ou `/scenario telephone +12025550123` avec des données
fictives.

## Documentation

- [Index des guides](docs/README.md)
- [Installation, prérequis et données](docs/installation.md) · [maintenance](docs/mise-a-jour.md)
- [Référence des commandes](docs/commandes.md) · [première session](docs/utilisation-terminal.md)
- [Interface Textual](docs/focus-textual-ux.md) · [Assist et Teams](docs/assist-teams.md)
- [Fonctionnalités V1](docs/fonctionnalites.md) · [outils OSINT et limites](docs/outils-osint.md)
- [Composants tiers et licences](THIRD_PARTY.md) · [sources vendor](vendor/README.uchambuzi.md)
- [Changelog](CHANGELOG.md) · [qualification V1.0.0](docs/releases/1.0.0.md)

## Développement

Le dépôt de développement contient le code source, les guides et les éléments
internes de recette. Les instructions de contribution et de qualification sont
conservées dans le dépôt privé ; la distribution publique présente uniquement
les éléments destinés aux utilisateurs.
