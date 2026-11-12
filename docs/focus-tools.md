# Focus : outils, commandes et approbations humaines

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note pour 0.3.0-beta.2 : ce document décrit des composants ou recettes historiques.
> Le REPL courant présente quatre Teams ; seule OSINT est active.
> Les anciens profils restent internes et ne sont plus proposés par `/mode`.
> Voir [les commandes actuelles](commandes.md) et [les fonctionnalités](fonctionnalites.md).


Composants autonomes de la mission 10, depuis `d941077`. La finition ajoute
[un adaptateur conversationnel directement raccordable](focus-tools-conversation.md). Python 3.10+,
bibliothèque standard exclusivement. Aucun changement du lanceur, de la TUI,
des moteurs IA, des sessions ou de l'installation. Les anciens écrans ne sont
pas raccordés automatiquement à ce service.

## Interfaces d'intégration

- `/tools` : `ToolRegistry().discover()` retourne des `InstalledTool` : chemin
  résolu, présence, version/statut de sonde, options observées dans l'aide,
  identité du fichier exécutable, invocations effectivement réussies.
- `/analyze` : `ProposalTools(service).analyze(texte, mode=...)` extrait des
  indicateurs et objectifs français et retourne des recommandations expliquées.
- `/prepare` : `ProposalTools.prepare(ToolRequest)` respecte le contrat Focus v1
  `ToolService.prepare -> ToolResult`. Le résumé JSON comprend l'identifiant de
  l'opération ; `service.get_prepared(id)` restitue la structure immuable complète.
  La commande d'affichage utilise `shlex.join` ; seule la structure `program` et
  `args` est exécutable. Aucun parsing de texte IA en commande exécutable.
- Les scénarios 07 peuvent transmettre `mode` et `scenario` à
  `prepare_operation`. Les catégories sont celles de `FocusMode` de la mission 06.
  Chaque mode expose aussi les catégories encore absentes du catalogue initial.
  Aucun mode ne donne une permission d'exécution.
- L'IA 08 reçoit uniquement `ProposalTools`. L'hôte humain garde l'autorité et le
  service complet. Ne jamais transformer un booléen ou appel d'outil produit par
  l'IA en décision humaine. Le protocole partagé de confirmation sert au rendu
  et au retour de l'interface ; sa simple possession ne vaut pas autorisation.

Le coordinateur doit raccorder ces API aux futures interactions TUI, aux scénarios
et à l'hôte humain. Aucune évolution de `focus_contracts.py` n'est nécessaire :
`ToolResult` reste une vue textuelle ; les arguments structurés et jetons restent
propres au service. Aucun autre fichier d'agent n'a été modifié.

## Cycle d'une opération

```python
from focus_contracts import ConfirmationDecision
from focus_permissions import HumanApprovalAuthority
from focus_tool_audit import ToolAudit
from focus_tools import FocusToolService, ProposalTools

authority = HumanApprovalAuthority(ttl=120)
service = FocusToolService(audit=ToolAudit(), authority=authority)
ai_tools = ProposalTools(service)
operation = service.prepare_operation("hash", {"target": "/path/to/working copy"},
                                      mode="trace", scenario="file_triage")
request = service.request_approval(operation)
# L'interface humaine affiche request.details dans son intégralité et attend
# la réponse réelle de l'utilisateur. Elle fournit aussi son identité locale.
# decision = ConfirmationDecision(request.id, approved=human_answer)
# approval = service.decide_approval(operation, request, decision, actor=human_id)
# result = service.execute(operation, approval, authority=authority,
#                          cancel=threading.Event())
```

La décision est refusée si la demande ne correspond pas, si elle est expirée,
refusée ou déjà décidée. Le jeton est lié à l'intégralité de l'opération : ID,
programme, arguments, cible, périmètre, mode, scénario, bornes et identités des
fichiers. Il expire, est révocable et n'est consommable qu'une fois, même après
un échec. Un changement d'exécutable ou de ressource impose une nouvelle
préparation et un nouvel accord. Les autorisations ne survivent pas au processus.

`request_approval`, `decide_approval` et `execute` appartiennent exclusivement à
l'hôte humain. Les utiliser garantit la trace des demandes et refus, même sans
exécution. Les méthodes directes de l'autorité servent au contrôle interne et aux
tests ; elles ne journalisent pas les décisions à elles seules.

## Catalogue et préparation

Le catalogue couvre `ip`, `ss`, `dig`, `whois`, `nmap`, `exiftool`, `tshark`,
`file`, `sha256sum`, `strings`, `binwalk`, `journalctl`, `nft`, `man`, `systemctl`.
Les opérations sont respectivement `interfaces`, `sockets`, `dns`,
`registration`, `ports`, `metadata`, `pcap`, `identify`, `hash`, `strings`,
`signatures`, `logs`, `ruleset`, `manual`, `services`.

L'absence d'exécutable interdit sa préparation. La présence ne prouve aucune
capacité. Une sonde de version réussie prouve seulement la version annoncée ;
`verified_capabilities` reste vide jusqu'à une invocation contrôlée réussie,
marquée `invocation:<operation>`. Ce marqueur ne certifie pas la validité
sémantique du résultat ni tous les usages de l'outil.

Découverte : budget de 12 secondes par défaut (maximum 60), 0,7 seconde par
sonde (maximum 3), sorties de version limitées à 16 Kio et d'aide à 32 Kio.
Aucun accès réseau demandé, aucune installation, aucun privilège supérieur.
Les sondes utilisent uniquement les options fixes intégrées. Le budget borne les
processus lancés ; la résolution PATH/stat reste dépendante du système de fichiers.
Une erreur, un délai, une version inconnue et un outil absent restent distincts.
`load_descriptions(JSON)` accepte uniquement des descriptions bornées, sans
programme, sonde, code, import, shell ou gabarit exécutable. Un nouvel outil
exécutable nécessite une revue du code de préparation et des sondes.

Les cibles IPv4/IPv6, domaines IDNA, URL HTTP(S) et chemins Unicode sont validés.
Les chemins doivent désigner des fichiers réguliers lisibles ; les chemins
relatifs nécessitent le type fichier explicite ou un préfixe `./`. Dans une
phrase, citer les chemins contenant des espaces. Un chemin absent est identifié
comme tel, sans inventer son contenu. L'analyse de français est déterministe et
limitée à des mots clés : elle n'invente ni OS, ni ports ouverts, ni vulnérabilités.
Les URL avec identifiants, requête ou fragment sont refusées ; les opérations DNS,
WHOIS et ports n'utilisent que l'hôte de l'URL, affiché comme cible exacte.
DNS utilise une requête A sur domaine et une requête inverse sur IP.

Les options supplémentaires acceptées sont volontairement limitées : `reason`
(`true`) pour Nmap et `since` (date ISO valide) pour journalctl. Elles nécessitent
l'observation de `--reason`/`--since` dans l'aide locale. Aucun argument libre.
Leur présence dans l'aide ne certifie pas leur bon fonctionnement. Toute
préparation indique sa compatibilité non vérifiée fonctionnellement, même avec
une version connue. Le manuel local se prépare par `manual` avec un sujet du
catalogue ; les aides et versions sont recueillies par les sondes bornées.

## Risques et politique

| Catégorie | Exemple / politique |
| --- | --- |
| `local_read` | Fichier, hash, interfaces, sockets, journaux ; accord explicite |
| `passive_intelligence` | WHOIS ; accord explicite, envoi de cible déclaré |
| `network` | DNS ; accord explicite, cible divulguée au résolveur |
| `authorized_active` | Nmap TCP connect 1–1024 sur une cible ; accord explicite et périmètre affiché |
| `local_change` | Représentable mais refusée par cet exécuteur |
| `privileged_or_disruptive` | Lecture nft préparée, exécution refusée |

La classification appartient aux gabarits de code, jamais à une étiquette IA.
Les opérations inconnues sont rejetées. Aucun gabarit de modification n'est
fourni. `sudo`, root, divergence UID/EUID et exécutables SUID/SGID sont refusés.
Un hôte ne doit jamais relancer automatiquement une commande refusée avec sudo.
La lecture de captures est limitée à 100 paquets et sans résolution de noms ;
aucune capture vive, extraction binwalk, écriture ExifTool, suppression de journal,
installation de règle ou changement de service n'est fourni.

Avant accord : programme/arguments, cible, périmètre, catégorie, mode, scénario,
version/compatibilité, effets, privilèges, données envoyées, délai et volume de
sortie sont présentés. Les effets incluent l'atime, les traces système, les
connexions actives, la détection et la charge possibles. Aucun paquet envoyé ne
peut être annulé. Le code retour et la sortie doivent être examinés par l'humain.

## Processus et audit

L'exécution utilise `Popen` sans shell, stdin fermé, cwd `/`, environnement réduit
sans secrets hérités et HOME temporaire existant (supprimé à la fin), session/process group isolé. Délai de 10 s et sortie cumulée
de 64 Kio par défaut ; maxima de 300 s et 4 Mio. Annulation par `threading.Event`.
Le groupe est tué à l'arrêt, y compris les descendants conservant une pipe ouverte.
Les statuts sont `succeeded`, `failed`, `spawn_error`, `timeout`, `cancelled`,
`output_limit`. Un arrêt forcé ne devient pas un succès. Les sorties sont en
mémoire bornée ; ce n'est pas un bac à sable CPU/mémoire ni un conteneur.

`ToolAudit(root=..., session=...)` utilise `<root>/audit/tools/events.jsonl`,
fichier 0600, répertoire 0700, verrou et fsync. L'exécution exige un audit
fonctionnel avant lancement. Les événements séparent préparation, demande,
décision, demande de lancement et fin. Le résultat précise début/fin effectifs
et PID après création du processus (absents sans processus lancé). Ils comprennent
ID, UTC, mode, version, risque, identité de
l'autorisation, statut, code retour et références/empreintes SHA-256 des sorties
capturées. Sur dépassement de volume, l'empreinte porte uniquement sur le préfixe
capturé ; `retained=False` rappelle que ces sorties ne sont pas persistées.

Pour préserver les secrets, arguments, cible, périmètre, scénario et identité
humaine sont corrélés par HMAC avec une clé locale privée, sans leur texte brut.
Le programme est identifié par son ID de catalogue. L'audit est donc une trace
technique expurgée, pas un moyen de rejouer la commande exacte. La commande exacte
reste dans l'objet en mémoire et dans la revue humaine. Ni stdout/stderr bruts ni
exception système susceptible de contenir un secret ne sont enregistrés.

Par défaut, le chemin utilise `focus_storage.default_data_dir` de mission 09
lorsqu'il est intégré, sinon `~/Documents/uchambuzi-data`. L'intégrateur peut
fournir `session_manager.storage.root` pour suivre exactement le stockage utilisateur.
Chaque événement est désormais référencé automatiquement dans la session liée.
`attach_to_session(operation_id)` reste disponible pour une référence technique via
`Session.add_message(... allow_tool=True)` ; aucune seconde session n'est créée.
La conservation de données d'investigation exige un choix humain distinct et
l'API de ressources/session existante. Aucun artefact réel d'enquête dans Git.

Limites de sécurité : l'autorité Python et sa façade sont une frontière logique
dans un hôte de confiance, pas une isolation contre du code Python hostile dans
le même processus. PATH, exécutables, bibliothèques/plugins système et ancêtres du
répertoire de stockage doivent être de confiance. Les vérifications stat réduisent
les changements entre préparation et lancement sans éliminer les courses TOCTOU.
L'audit n'est pas inviolable contre le propriétaire du compte ; pas de chaîne de
preuve judiciaire ni de signature externe. Une panne après début peut laisser une
opération sans fin enregistrée : elle doit être traitée comme indéterminée.

## Vérification de livraison

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_focus_tools.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_focus_permissions.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Les tests utilisent des exécutables factices et fichiers temporaires. Ils couvrent
présence/absence, versions et erreurs de sonde, délais, validation/Unicode,
arguments sans shell, compatibilité inconnue/incompatible, six risques,
accord exact/expiré/réutilisé/refusé, fausse autorité, mutation de ressource ou
exécutable, erreurs/annulation/volume/descendants, audit sans secrets, privilèges,
symlinks d'audit, profils historiques sans réseau et contrats Focus.

Résultats historiques de la première livraison du 8 novembre 2026 (`0645a40`) :

- Ubuntu, Python 3.14 : **324 tests de régression réussis**, dont 40 tests
  outils/permissions ; dernière exécution en 17,868 secondes.
- Kali Rolling 2026.3, Python 3.13.15 : **40 tests ciblés réussis** (31 outils,
  9 permissions). Inventaire réel sans installation ni élévation.
- Sur fichiers temporaires Unicode : `file`, `sha256sum`, `strings` réussis sous
  Ubuntu ; mêmes outils et `exiftool` réussis sous Kali, après refus sans accord
  puis décision du banc de recette explicitement autorisé par la mission.
- Kali : versions détectées notamment Nmap 7.991, ExifTool 13.55, file 5.47,
  sha256sum 9.10, nftables 1.1.7, systemd 262. La sonde de `tshark` échoue avec
  une erreur de dissecteur de l'installation réelle ; `binwalk` reste de version
  inconnue. Aucune réparation de ces outils n'a été entreprise.
- Raccordement réel au stockage mission 09 : session temporaire créée, référence
  d'audit ajoutée, session fermée puis rouverte avec la référence conservée.
- Contrat Focus inchangé entre le socle mission 06 et la référence mission 08.

Aucun scan ni requête DNS/WHOIS réel n'a été lancé. Leurs préparations et la
politique d'accord sont testées avec des doubles ; aucune compatibilité active
universelle n'est revendiquée. Les limites de l'extracteur français, de la
compatibilité des options, de l'audit expurgé et de l'isolation sont exposées
ci-dessus pour l'intégrateur.

Les résultats de finition, la qualification de binwalk et les procédures TUI sont
dans [focus-tools-conversation.md](focus-tools-conversation.md). Les autorisations
sont invalidées sur changement de contexte et toute tentative altérée révoque aussi
le jeton original. Les identifiants d’autorisation dans l’audit sont des références
opaques ; ils ne suffisent jamais à reconstruire un accord.
