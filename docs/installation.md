# Installation UCHAMBUZI 1.1.0 sur Kali

## Prérequis et paquet Debian

Cible qualifiée : **Kali Linux amd64**. Les bundles Python tiers ciblent CPython
**3.13** ; Python 3.14 peut rester l'interpréteur principal de l'application.
Le paquet déclare `python3.13`, `python3.13-venv`, `python3-rich`,
`python3-prompt-toolkit`, `python3-textual`, `tzdata` et `libc6`.
L'installation des prérequis système peut nécessiter un accès aux dépôts Kali.

```sh
sudo apt install ./uchambuzi_1.1.0-1_amd64.deb
type -a uchambuzi
uchambuzi --version
uchambuzi doctor
uchambuzi
```

Le chemin attendu est `/usr/bin/uchambuzi` ; les ressources sont sous
`/usr/share/uchambuzi`. Un ancien alias ou lanceur utilisateur peut avoir priorité.
Après installation : `dpkg -V uchambuzi` ne doit signaler aucune altération.
Le paquet public disponible reste la 1.0.0. Ces guides décrivent la candidate
privée 1.1.0 ; utilisez le paquet 1.1.0 seulement lorsqu'il vous est fourni et
validé. Voir les [ruptures et précautions](releases/1.1.0.md).

Dans l'application : `/team 1`, puis `/tools setup`, confirmer avec `o` puis
Entrée. Les douze copies sont installées depuis les artefacts locaux vérifiés,
sans téléchargement de dépendance Python. Un interpréteur incompatible ou absent
bloque l'installation ; l'application ne reconstruit pas automatiquement le bundle.
Les copies disponibles et leur niveau d'intégration sont décrits dans le
[catalogue](outils-osint.md).
Ollama est distinct : vérifier le moteur et les modèles déjà installés avec
`/models` et `/settings`. Le modèle local recommandé, actuellement en cours de
calibration, est `redsage-qwen3:8b-dpo`. Il n'est pas inclus dans le paquet.
Sur la machine hébergeant Ollama, il peut être préparé ainsi :

```sh
ollama pull hf.co/mradermacher/RedSage-Qwen3-8B-DPO-GGUF:Q4_K_M
ollama cp hf.co/mradermacher/RedSage-Qwen3-8B-DPO-GGUF:Q4_K_M redsage-qwen3:8b-dpo
```

Cette quantification est fournie par un tiers ; son téléchargement nécessite
Internet. Le modèle peut être changé dans `/settings` ; aucune installation ni
suppression de modèle n'est effectuée automatiquement par UCHAMBUZI.

## Fournisseurs IA distants facultatifs

`/settings` permet de sélectionner OpenAI ou Grok avec une API compatible
Responses, ou Claude via Claude Code CLI installé séparément. Choisissez le
modèle, l'adresse HTTPS du fournisseur ou de votre passerelle et le nom de la
variable d'environnement contenant la clé. Les suggestions de modèles sont
provisoires et leur disponibilité dépend du fournisseur. L'utilisateur reste
libre de sélectionner un autre modèle.

Par exemple, dans un shell Bash, pour préparer une clé OpenAI sans l'inscrire
dans l'historique des commandes :

```sh
read -rs -p 'Clé API : ' OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
uchambuzi
```

Dans `/settings`, indiquez `OPENAI_API_KEY` comme nom de variable, pas la clé.
L'équivalent par défaut est `XAI_API_KEY` pour Grok et `ANTHROPIC_AUTH_TOKEN`
pour Claude. La variable doit être présente dans l'environnement du processus
UCHAMBUZI. Claude Code doit être disponible dans le `PATH` ; UCHAMBUZI ne
l'installe pas. Une passerelle Claude doit autoriser l'utilisation du CLI.

Vous pouvez aussi créer plusieurs accès nommés dans `/settings`, avec une clé
saisie directement. Les profils sont enregistrés dans `providers.json` et les
clés dans `provider-secrets.json`, à côté des réglages interactifs, avec permissions
`0600`. Les clés ne sont pas chiffrées. Les variables d’environnement restent
utilisables sans sauvegarder leur contenu. Pour un accès Responses, la recherche
des modèles demande un accord avant d’envoyer la clé à l’adresse configurée ;
Claude Code utilise une saisie manuelle.

Avant chaque envoi distant, l'application présente le contenu préparé et la
destination et attend un accord explicite. Les réponses distantes s'affichent
après génération complète. Un serveur Ollama hors loopback utilise HTTP et
nécessite aussi un accord ; ce transport n'est pas chiffré. Les requêtes vers
`127.0.0.1` sont considérées locales, même si un tunnel les relaie ailleurs.

## Installation utilisateur depuis les sources

Sur Kali, après installation des dépendances système ci-dessus :

```sh
bash install.sh
~/.local/bin/uchambuzi --version
```

Le lanceur utilisateur et l'application sont gérés par manifeste. Ne pas mélanger
cette voie avec le paquet système sans examiner `type -a uchambuzi`.
La construction du paquet s'effectue sur Kali depuis le dépôt privé de
développement ; les scripts de packaging ne sont pas inclus dans l'arbre de
distribution. Le paquet attendu est `uchambuzi_1.1.0-1_amd64.deb`.

## Données et conservation

| Contenu | Emplacement |
| --- | --- |
| Réglages principaux, dossiers et rapports | `<Documents XDG>/uchambuzi-data/` |
| Préférences de lancement (`--save-config`) | `<Documents XDG>/uchambuzi-data/config/settings.json` |
| Profils IA nommés et clés facultatives | `${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/config/providers.json` et `provider-secrets.json` |
| Réglages interactifs IA et thème | `${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/config/settings.json` |
| Dossier d'enquête et journal | `<Documents XDG>/uchambuzi-data/cases/<id>/` |
| Copies d'outils gérées | `~/.local/share/uchambuzi-data/tools/<outil>/<version>/` |
| Historique du REPL Prompt Toolkit de repli | `${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/` |

Documents est résolu avec `XDG_DOCUMENTS_DIR`, puis `user-dirs.dirs`, sinon
`~/Documents`. Les expressions de configuration ne sont pas exécutées.
Dans Textual, l’ouverture ou la création d’un dossier propose de
continuer sans sauvegarde, de créer une conversation sauvegardée ou d’en reprendre
une. Les snapshots résident dans `cases/<id>/sessions/`, sans chiffrement, et
leur structure, leur révision et leur association au dossier sont contrôlées,
sans empreinte cryptographique. Seuls les échanges complets
acceptés sont repris dans le contexte IA ; ni les autorisations ni les fragments
de génération interrompue ne sont restaurés. Les détections de secrets et
d’injections restent partielles. Sauvegardez le dossier entier, conversations et
journal ensemble ; ces contrôles ne garantissent pas l'absence de modification
du contenu. Les dossiers créés ou réécrits en 1.1.0 ne sont pas utilisables avec
la 1.0.0. Fermez les anciennes sessions et sauvegardez avant mise à jour.

Les réinstallations préservent les données utilisateur. La maintenance par
manifeste préserve les fichiers inconnus et bloque les collisions au lieu de
les écraser. Les sauvegardes de migration restent privées.
`uchambuzi --model qwen2.5:3b --save-config` enregistre une préférence locale.

## Désinstallation

Paquet système : `sudo apt remove uchambuzi`, après sauvegarde privée des dossiers.
Installation utilisateur : `uchambuzi uninstall` retire les fichiers gérés et
conserve les données. Les options `--purge-data`, `--remove-model` et `--purge-ai`
sont des suppressions explicites ; ne les ajouter que pour retirer volontairement
les données ou les services concernés. Aucun retrait d'Ollama n'est nécessaire
pour mettre à jour UCHAMBUZI. Voir [maintenance](mise-a-jour.md).
