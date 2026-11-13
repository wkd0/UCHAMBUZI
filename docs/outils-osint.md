# Outils OSINT — candidate privée 2.0.0

Cette candidate privée complète les six copies de la version publique 1.0.0
par six nouvelles copies vérifiées. Le paquet public 1.0.0 reste distinct.

`data/tools/catalog.json` est la liste blanche de référence. La fiche `/tools <nom>`
présente version, source, activité et état détecté. Le catalogue distingue les
paquets Kali, douze copies embarquées et le moteur natif WhatsMyName.

## Installation et intégration

L’état installé indique la présence de l’outil, pas la prise en charge de toutes
ses options. La liste et les fiches affichent séparément l’intégration :

| Niveau | Ce qui est disponible |
| --- | --- |
| Action accompagnée | Préparation individuelle avec `/tools run`, pour six des douze copies embarquées. |
| Parcours intégré | Opérations définies dans un raccourci ou scénario indiqué sur la fiche, par exemple `/domaine` pour dig ou `/photo` pour mat2. |
| Shell et aide | Fiche et documentation ; utilisation de la syntaxe native via le shell, sans parcours intégré, par exemple nmap ou amass. |
| Moteur natif | WhatsMyName, accessible via `/pseudo`, sans exécutable shell. |
| À venir | Copie vérifiée non distribuée ; aucun parcours annoncé comme disponible. |

Pour Amass v5.1.3, voir le [parcours local et le diagnostic du moteur](amass-v5.md) :
`enum -h` peut démarrer le moteur et attendre le réseau. La présence du paquet
ne valide pas une énumération ; `subs` permet une lecture SQLite locale séparée.

Les parcours affichés proviennent des raccourcis et étapes implémentés. Un outil
simplement cité comme alternative n’est pas présenté comme un parcours intégré.
Chaque parcours peut aussi comprendre des étapes dont l’outil est absent ; leur
présence locale et l’approbation humaine restent nécessaires.

Le bouton **Aide** charge les références sans bloquer la navigation : `man` local
si l’outil est présent, puis fiche embarquée, puis `--help` si nécessaire. Il
indique la source et si l’extrait est tronqué. La lecture de cette aide ne vérifie
pas la version installée. Les outils du catalogue sont reconnus par la
recherche documentaire du dialogue IA, avec deux outils au maximum dans l’ordre
de la demande et 2 000 caractères par extrait. Ce contexte précise aussi les
parcours disponibles ; il ne constitue pas une autorisation d’exécuter.

| Copie embarquée | Version figée | Accès dans la CLI |
| --- | --- | --- |
| gau | 4eabace ; annonce 2.2.4 | `/archive`, `/domaine`, playbooks |
| maigret | 0.6.6-21577cf | `/pseudo`, playbook `email-pseudo` |
| holehe | 1.61-14da70f-r1 | `/email` |
| phoneinfoga | 2.11.0 | `/scenario telephone <numéro E.164>` |
| social-analyzer | 0.45-c585f42-r1 | `/pseudo`, playbook `email-pseudo` |
| blackbird | 471ef970 | `/pseudo` |
| subfinder | 2.17.0 | Playbooks et shell ; parcours indiqués sur la fiche |
| httpx | 1.12.0 | Playbooks et shell ; parcours indiqués sur la fiche |
| dnsx | 1.3.1 | Playbooks et shell ; parcours indiqués sur la fiche |
| photon | 1.3.0-r1 ; bannière amont 1.2.2 | Shell et aide |
| trufflehog | 3.99.8 | Shell et aide |
| gitleaks | 8.30.1 | Shell et aide |

`/tools setup` ou `/tools install all` prépare les douze copies après accord.
Les bundles Python ciblent amd64 et CPython 3.13. L'installateur sélectionne cet
interpréteur même si Python 3.14 est l'interpréteur système. Les wheels sont
installés avec `--no-index` dans des environnements isolés. Aucune récupération
amont implicite. Les binaires Go sont livrés exécutables.

`/tools verify <nom>` vérifie l'artefact source. Lorsqu'un exécutable installé est
résolu, son manifeste est également vérifié : un fichier ajouté ou altéré hors
cache de bytecode bloque la résolution. Une installation altérée n'est pas
remplacée automatiquement. Les versions ne changent qu'avec un catalogue approuvé.

## Limites des parcours

- `/pseudo` propose WhatsMyName, Maigret, Blackbird et Social Analyzer séparément.
- `/email` propose Holehe. Le playbook `email-pseudo` prend un pseudonyme et
  n'envoie plus celui-ci à un outil exigeant une adresse email.
- PhoneInfoga désactive les scanners à clé et la lecture d'un fichier `.env`
  utilisateur. La première étape est locale ; la deuxième produit des liens
  de recherche. Ces liens ne constituent pas des résultats de recherche vérifiés.
- Blackbird utilise `--username`, désactive les mises à jour automatiques et
  bloque les options IA à clé dans son lanceur géré.
- Les outils mixtes sont classés actifs par précaution. Chaque commande
  disponible attend sa confirmation ; les outils absents sont signalés.
- Le parcours archives enchaîne gau et curl après approbation explicite.
- Les sources publiques peuvent imposer CAPTCHA, authentification, quotas ou
  indisponibilités. Une erreur ou un délai dépassé ne prouve pas l'absence d'indice.

Consulter [THIRD_PARTY](../THIRD_PARTY.md) pour les licences conservées et
[vendor](../vendor/README.uchambuzi.md) pour les révisions et la reconstruction.
La [note 2.0.0](releases/2.0.0.md) décrit la candidate et sa compatibilité ; la [note V1](releases/1.0.0.md) reste historique.
