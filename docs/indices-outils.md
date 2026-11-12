# Prototype : indices et inventaire

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

Ce module autonome utilise Python 3 et sa bibliothèque standard. Dans la copie intégrée, le terminal le consomme via `parcours.py`; voir [la recette](recette-prototype.md). Depuis la racine du dépôt :

```python
import sys
sys.path.insert(0, 'src')
from indices_outils import classify, extract, inventory

indices = extract('Voir analyste@example.org et 192.0.2.1')
indice_explicite = classify('/tmp/exemple.pcap', 'file')
outils = inventory()  # présence dans PATH uniquement, sans lancer d'exécutable
versions = inventory(versions=True, timeout=2.0)  # contrôles locaux optionnels
```

Les exemples sont fictifs. `extract` repère des candidats dans du texte ; pour un candidat qui ne se prête pas à l'extraction automatique, `classify(valeur, type)` prend `email`, `domain`, `ip`, `url` ou `file`. Ces fonctions ne lisent pas le contenu du fichier indice et ne produisent ni n'exécutent de commande d'investigation. La présence est celle observée dans le PATH courant et ne prouve ni fonctionnement, ni absence ailleurs.

## Enrichissements du développement local

Les indices contiennent aussi un identifiant de présentation, des métadonnées, des relations explicites et leur provenance déclarée. Les métadonnées distinguent notamment IPv4/IPv6, hôte et port d'une URL, domaine d'un e-mail et informations `stat` d'un fichier. Le type MIME est estimé depuis l'extension, sans inspection du contenu ; il peut être faux. L'identifiant abrégé ne constitue pas une preuve d'identité ou d'unicité.

L'analyse regroupe les doublons tout en conservant leurs observations dans `duplicates`. Le classement propose un objectif supposé et affiche sa justification ; il ne transforme pas une recommandation en autorisation. La numérotation peut changer : choisir le numéro effectivement affiché. L'inventaire distingue aussi un exécutable trouvé mais inaccessible et expose son chemin résolu.

La fonction Python `hash_file` est disponible sur demande explicite avec SHA-256 ou SHA-512 ; elle n'est jamais appelée par l'analyse ordinaire. Elle lit le fichier entier, refuse les liens et les fichiers spéciaux, et recherche les changements observables pendant la lecture. Elle peut modifier l'atime et ne garantit ni stabilité absolue, ni signature, ni chaîne de conservation.

Le catalogue reste limité aux sept outils ci-dessous. La préparation de `whois`, `curl` et `tshark` reste refusée ; leurs recommandations sont documentaires. Aucune détection d'options dans une aide ne remplace les règles de version exacte.

## Contrats provisoires

Les résultats sont des dictionnaires sérialisables en JSON, à coordonner avec les intégrateurs :

- Indice : `type`, `original`, `normalized` (chaîne ou null), `validation` (`valid`, `invalid`, `unknown`), `ambiguities` (liste), `explanation`. `valid` signifie contrôle syntaxique ou local du sous-ensemble seulement, jamais existence réseau ou valeur probatoire. Un fichier absent/inaccessible est `unknown`, un répertoire est `invalid`.
- Outil : `id`, `name`, `installed` (booléen), `executable_path` (chaîne ou null), `detection_origin`, `version` (première ligne ou null), `version_origin`, `capabilities`, `indicator_types`, `prerequisites`, `documentation`. Les listes de capacités sont des descriptions provisoires, pas des vérifications de version ni des recommandations validées. Les URL de documentation sont des références d'origine proposées, non consultées pendant l'atelier ; leur contenu et leur correspondance avec les versions locales restent à vérifier par le chantier documentaire.

Le catalogue initial couvre DNS (`dig`), informations publiques (`whois`), type et métadonnées de fichier (`file`, `exiftool`), captures réseau (`tshark`), inspection statique (`strings`) et URL (`curl`). `dig` prend aussi en charge une IP pour une recherche inverse et, indirectement, un e-mail ou une URL après extraction et validation séparées du domaine ou de l'hôte. Aucun accès à une boîte ni téléchargement de page n'est impliqué. Ce sont des candidats pertinents pour ces familles, sans présomption d'installation ou de compatibilité ; la disponibilité est contrôlée au moment de l'appel. Les outils d'informations publiques s'appliquent notamment au domaine d'un e-mail après extraction explicite, sans prouver l'existence d'une boîte. Les fiches de commandes et les sources validées restent hors de ce module.

## Limites et sécurité

Les e-mails ne couvrent pas les parties locales Unicode ou citées ; les domaines utilisent le codec IDNA de Python (IDNA 2003), pas une validation IDNA 2008. La normalisation ne prouve pas l'identité du domaine. Seules les URL HTTP(S) sans identifiants sont acceptées ; la ponctuation terminale extraite d'une phrase est heuristique. Un chemin avec espaces peut être cité entre guillemets simples ou doubles dans `extract`, ou soumis directement à `classify` ; un chemin non cité peut être tronqué au premier espace et doit être confirmé. Les noms de fichiers relatifs sans préfixe explicite ne sont pas reconnus automatiquement. Une phrase peut contenir des candidats invalides, absents ou ambigus ; l'extraction ne détecte pas tous les formats et ne remplace pas une confirmation humaine. Les liens symboliques sont suivis lors du contrôle de fichier et leur cible peut changer ; la normalisation conserve les segments `..` pour ne pas changer leur cible. Une adresse IPv6 avec zone peut être reconnue, mais le module de préparation de commandes refuse les zones pour ses commandes. La reconnaissance et l'existence locale ne valent jamais autorisation d'utilisation.

Par défaut, l'inventaire ne lance aucun outil. L'option `versions=True` lance exclusivement les exécutables trouvés dans PATH avec un argument fixe de version, sans shell ni donnée utilisateur, avec délai, limite de sortie et interruption du groupe en cas d'échec. Ces exécutables doivent être de confiance : ce contrôle n'est pas un bac à sable et ne peut garantir l'absence d'effets d'un programme remplacé ou malveillant. Seuls les bandeaux usuels reconnus pour les sept outils sont conservés, exactement comme observés ; les autres restent inconnus, même s'ils proviennent d'une version valide. Les formats acceptés restent des heuristiques, et ne vérifient ni l'intégrité du binaire ni sa compatibilité. Un échec laisse la version inconnue. Sur Ubuntu, un essai `strace` avec versions a observé la création de sockets IP sans connexion IP et des tentatives de connexion locales au socket Unix de nscd ; l'inventaire sans versions n'a effectué aucun appel réseau observé. Ceci ne garantit pas le comportement d'autres exécutables ou environnements.

## Couverture et intégration

`python3 -m unittest discover -s tests -v` couvre e-mails valides et invalides, domaines IDN et classiques, IP, URL, fichiers présents/absents, indices multiples et ambigus, outil présent/absent, version inconnue et délai réel. Les régressions couvrent également ponctuation, chemins cités, liens symboliques, bandeaux attendus ou inattendus et erreurs d'exécution. Le test réseau simule l'interdiction d'appels Python ; l'observation système distincte est décrite ci-dessus. Les variantes IDNA, les permissions de fichiers et d'autres implémentations des outils nécessitent des tests supplémentaires. Aucun test Kali, installation ni recette intégrée n'a été effectué.

Le raccordement de ces fonctions à la CLI s'effectue via `parcours.py` sans modification unilatérale des interfaces. Le module documentaire consomme l'inventaire sans considérer les descriptions d'outils comme des preuves documentaires. Le module de commandes s'appuie sur des sources locales vérifiées et des champs normalisés. Le choix de langage, la liste des outils et les règles de compatibilité restent soumis à validation.

La sonde ExifTool utilise `-config "" -ver` dans cet ordre pour désactiver la
configuration personnelle avant la détection de version. Les chemins du PATH
doivent rester fiables ; aucune sonde ne constitue un bac à sable.
