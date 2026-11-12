# Mise à jour et maintenance sous Kali Linux

> Version publiée : 1.0.0 (12 novembre 2026). Utiliser Python 3.13 et python3.13-venv pour les bundles ; voir les [commandes courantes](commandes.md), le [changelog](../CHANGELOG.md) et la [recette V1](releases/1.0.0.md).

Ces procédures s’exécutent sur Kali. Fermez les sessions UCHAMBUZI avant une
mise à jour et conservez une sauvegarde privée de vos dossiers d’enquête.
Utilisez une version validée et un seul mode d’installation à la fois.

## Identifier l’installation utilisée

```bash
type -a uchambuzi
uchambuzi --version
uchambuzi doctor
```

Le paquet Debian fournit `/usr/bin/uchambuzi` et les fichiers applicatifs dans
`/usr/share/uchambuzi`. Une installation utilisateur utilise `~/.local/bin` et
`~/.local/share/uchambuzi`. Un ancien lanceur utilisateur peut masquer celui du
paquet ; `type -a` permet de le détecter. Pour contrôler le paquet explicitement,
utilisez `/usr/bin/uchambuzi --version`.

Les données utilisent plusieurs racines. Les dossiers d’enquête, sessions,
audits et préférences Focus sont sous `<Documents>/uchambuzi-data/` (Documents
XDG, sinon `~/Documents`). Les réglages IA, le thème et l’historique des commandes
sont sous `${XDG_DATA_HOME:-~/.local/share}/uchambuzi-data/`. Les copies d’outils
gérées résident dans `~/.local/share/uchambuzi-data/tools/`. Préservez ces données
et votre configuration ; une mise à jour ne demande pas de désinstallation avec purge.

## Mettre à jour par paquet Debian

Obtenez le `.deb` validé par votre canal de distribution et contrôlez son empreinte
avec la référence reçue par un canal de confiance. Depuis son répertoire sur Kali :

```bash
sudo apt install ./uchambuzi_1.0.0-1_amd64.deb
/usr/bin/uchambuzi --version
/usr/bin/uchambuzi doctor
/usr/bin/uchambuzi
```

Adaptez le nom au paquet reçu. `apt` peut accéder aux dépôts pour résoudre les
dépendances système ; une installation entièrement hors ligne exige que ces
paquets soient déjà installés ou disponibles localement. Les artefacts `vendor/`
sont inclus dans le paquet, sans téléchargement depuis les dépôts des outils.
Le candidat cible amd64 ; ses bundles Python nécessitent Python 3.13 sur Linux
x86_64. Il n’est pas annoncé comme compatible avec une autre architecture.

## Mettre à jour depuis un dépôt Git local

Dans votre copie de sources sur Kali, vérifiez d’abord la branche, les différences
et la provenance du dépôt. Ne remplacez pas des modifications locales inconnues.
Pour une branche de distribution validée dont le suivi distant est configuré :

```bash
cd /chemin/vers/UCHAMBUZI
git status -sb
git diff
git pull --ff-only
```

`git pull` utilise le réseau, sauf si le distant est local. Un refus de fusion
rapide exige d’examiner la divergence ; ne lancez pas de réinitialisation forcée.
Le candidat local peut précéder la version publiée : un pull ne fournit que les
commits effectivement disponibles sur le distant configuré.

Pour mettre à jour une **installation utilisateur** depuis cette source validée :

```bash
uchambuzi update --source /chemin/vers/UCHAMBUZI
uchambuzi --version
uchambuzi doctor
uchambuzi
```

Pour la première installation utilisateur, exécutez `bash install.sh` depuis les
sources. Pour une installation Debian, conservez la voie `.deb` : un `git pull`
seul ne modifie pas `/usr/share/uchambuzi`.

## Gérer les outils dans le REPL

| Commande | Effet réel |
| --- | --- |
| `/tools` | Liste le catalogue et les états locaux. |
| `/tools list`, `/tools all` | Affiche le catalogue complet. |
| `/tools setup`, `/tools install all` | Vérifie et propose la préparation groupée des artefacts vendor après confirmation. |
| `/tools social` | Filtre par spécialité. |
| `/tools gau` | Affiche provenance, version, licence et disponibilité. |
| `/tools install gau` | Vérifie puis installe la copie figée de `vendor/`, après `[o/N]`. |
| `/tools update gau` | Tente d’installer la version du catalogue courant ; ne recherche aucune version distante. |
| `/tools verify gau` | Vérifie le SHA-256 de l’artefact source, sans réinstallation. |
| `/tools remove gau` | Retire la version gérée correspondant au catalogue après `[o/N]`. |
| `/tools import /chemin/artefact` | Importe un fichier dont l’empreinte correspond exactement à une entrée approuvée. |

Les binaires et bundles approuvés s’installent entièrement hors ligne. Les bundles
contiennent les dépendances ; pip utilise `--no-index`. Une empreinte incorrecte,
un artefact absent ou une licence `NOASSERTION` bloque l’installation. L'empreinte confirme l'identité locale de l'artefact par rapport au catalogue ; elle ne prouve pas la conformité juridique de la redistribution.

`update` réutilise l’installation : si la même version existe déjà, l’opération
est refusée comme « déjà installée ». Il faut une nouvelle version approuvée du
catalogue pour obtenir une version plus récente. Les anciennes versions ne sont
pas supprimées automatiquement. `remove` vise uniquement la version courante du
catalogue, sans toucher aux dossiers d’enquête ni aux paquets Kali.

La résolution d’un exécutable géré contrôle aussi son manifeste et ses fichiers
installés. Cette vérification est distincte du contrôle de l’artefact effectué
par `/tools verify`. Après une altération, conservez vos éléments utiles au
diagnostic puis retirez et réinstallez la version approuvée.

Pour un outil système Kali, `install` et `update` proposent `apt-get install` puis
demandent confirmation. Aucun `sudo` n’est ajouté : les droits et l’accès aux
paquets restent à la charge de l’utilisateur. `verify` et `remove` ne gèrent pas
les paquets système ; utilisez le gestionnaire de paquets Kali pour ceux-ci.

## Contrôler après mise à jour

Dans le REPL, consultez `/team`, `/tools`, `/tools gau`, `/models` et `/status`.
Avec un modèle déjà présent dans Ollama, sélectionnez `/ai qwen2.5:3b`.
Ouvrez un dossier d’exercice avec `/investigation create controle-mise-a-jour`, puis consultez
`/investigation log` et `/report`. Pour un contrôle local des métadonnées, utilisez
`/photo /chemin/image-exercice.png` et approuvez chaque lecture proposée.

La consultation du catalogue ne lance pas d’investigation. Les recherches en
ligne restent soumises à votre accord, même après une installation hors ligne.
Voir les [commandes](commandes.md) et les [outils OSINT](outils-osint.md).
