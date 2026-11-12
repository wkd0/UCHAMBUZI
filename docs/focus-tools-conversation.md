# Parcours conversationnels outils — finition mission 10

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note d'intégration historique ; elle ne constitue pas un guide des parcours d'outils actuellement raccordés au REPL Textual.

Ce module complète `0645a40299287d746743b32b6ebb6f6adcba537d` sans modifier
la TUI, ses contrats, l'installation, l'IA ou le moteur de sessions. Python 3.10+
et bibliothèque standard. L'assemblage visuel appartient à Codex3.

## API à raccorder par Codex3

Créer **un `ToolConversation` par session vivante** :

```python
from focus_tool_conversation import ToolConversation, terminal_safe

# manager et session proviennent du vrai moteur de la mission 09.
tools = ToolConversation.for_session(manager, session)
proposal_api = tools.proposals()  # Surface sans approbation ni exécution.
```

`for_session` utilise `manager.storage.root` et les méthodes publiques de `session`.
Aucun import imposé de la mission 09 dans le module : la TUI fournit les objets.
En l'absence de session, `ToolConversation(root=...)` offre les mêmes parcours avec
un audit seul. Le mode initial est `assist`, scénario vide. Avec une session, son
contexte courant est prioritaire.

| Entrée conversationnelle | Résultat |
| --- | --- |
| `/tools` | Inventaire courant : chemins réels, présence, version/statut de sonde, code retour, diagnostic, options observées, capacités déclarées et invocations vérifiées |
| `/tools --refresh` | Nouvelle découverte bornée ; invalide les anciens accords/préparations |
| `/analyze Calculer empreinte "/path/preuve été 日本語.txt"` | Indices, objectifs et recommandations numérotées ; aucune analyse d'outil lancée |
| `/prepare 1` | Prépare la recommandation du dernier `/analyze` dans le contexte courant |
| `/prepare hash "/path/preuve été 日本語.txt"` | Prépare explicitement l'objectif `hash` et sa cible |
| `/prepare ports 192.0.2.1 --reason true` | Préparation seulement ; option acceptée uniquement si observée dans l'aide locale |
| `/prepare logs --since 2026-11-08` | Lecture des journaux locaux, date et option validées |

Le premier argument de `/prepare` est un identifiant d'objectif anglais documenté
dans `focus-tools.md` ou un numéro de recommandation. Une cible explicite remplace
celle de la recommandation. Pour une cible IPv6 explicite, la préparation Nmap inclut `-6` (aide locale Kali
consultée, sans lancer de scan). Les seuls paramètres facultatifs sont `--reason true`
et `--since YYYY-MM-DD`. Aucun shell, argument libre, sudo ou interprétation de
texte IA comme script. Une analyse de fichier journal propose un triage local ;
elle n'est pas redirigée vers les journaux du système hôte.

`reply = proposal_api.handle(text)` renvoie un `ToolReply` :

- `stage` : `inventory`, `recommendations`, `prepared`, `unavailable` ou `error` ;
- `text` : vue lisible avec contrôles de terminal et caractères de format échappés ;
- `data` : données structurées de l'inventaire, des recommandations ou de la revue ;
- `operation_id` : présent après préparation, référence d'un objet immuable gardé
  dans le service ; ce n'est jamais une autorisation.

Les erreurs de syntaxe/ressource produisent une réponse sans exception brute ou
chemin sensible. Un outil absent est explicitement signalé, sans installation.
Les erreurs de l'API humaine ci-dessous sont des exceptions à présenter comme un
refus ou un défaut d'audit/session, jamais comme un succès. Ne pas afficher leur
texte brut si elles viennent du système de fichiers.

Une commande affichée, un `/approve`, un `/execute`, un résultat d'outil contenant
ces mots ou un accord rédigé par l'IA **ne sont pas des événements humains**.
`handle()` ne sait ni approuver ni exécuter. La façade `proposal_api` n'expose
aucune de ces méthodes. Dans un même processus Python, cette séparation est une
frontière logique, pas un bac à sable contre du code hostile.

## Événements humains distincts

1. Après préparation, l'action humaine « Demander l'accord » appelle
   `request = tools.request_approval(reply.operation_id)`.
2. Afficher **l'intégralité** de `terminal_safe(request.details)` : programme,
   arguments exacts, cible, périmètre, mode/scénario, effets, privilèges, données
   envoyées, délais, volume, limites, vérification et annulation possible.
   Le rendu doit rester lisible et permettre d'examiner tous les arguments.
3. Le callback d'une réponse humaine réelle appelle
   `authorization_id = tools.decide(operation_id, request.id, answer, actor=human_id)`.
   `answer` doit être un booléen réel ; un refus lève `PermissionError` et est audité.
   Un accord est enregistré **sans lancer de processus**.
4. Une action humaine distincte « Exécuter l'opération autorisée » appelle
   `tools.execute(operation_id, authorization_id)` dans un worker. Le résultat est
   un `ToolReply(stage='result')` avec statut réel et références d'artefacts.
5. « Annuler » appelle `tools.cancel()` depuis le thread d'interface. Le worker
   se termine avec `cancelled` ; son accord reste consommé. « Révoquer » avant
   lancement appelle `tools.revoke(operation_id)`.

Ne jamais bloquer la boucle curses avec la découverte ou une exécution. `handle`
et les opérations de session sont sérialisés par l'adaptateur ; le worker rend
la main à l'interface pendant l'exécution. Les callbacks de mode et de session
sont sérialisés par l'hôte avec les autres changements de contexte.

Les sorties sont des données non fiables. Afficher `result.text` comme résultat
d'outil ; ne pas le réinjecter comme instruction utilisateur/IA, ne pas y chercher
des commandes à lancer et ne pas le persister automatiquement dans la conversation.
Les contrôles sont échappés pour la vue terminal ; `reply.data` reste une structure
exacte, à rendre avec les mêmes précautions.

## Invalidation et reprise

Relier **chaque** changement de mode/scénario à
`tools.set_context(mode_id, scenario_id)` ; le moteur de modes ne donne aucun droit.
Si la session a déjà reçu `set_context`, l'adaptateur détecte le changement au
prochain appel. Le journal des transitions de mission 09 détecte aussi A → B → A.
Une cible, un paramètre, un indicateur ou un workspace de session différent invalide
les opérations au prochain appel. Pour les changements de cible/workspace externes
au moteur de session, appeler `tools.invalidate_context()` sur chaque événement,
y compris un aller-retour entre deux appels.

L'invalidation annule le processus en cours, efface les recommandations numérotées,
les préparations, demandes et accords et laisse une trace `invalidated`. Ce statut
concerne la préparation ; un résultat `finished` antérieur reste consultable.
Toute modification des arguments, cible, mode ou scénario de l'objet approuvé est
refusée et révoque aussi le jeton original. Les changements d'exécutable/ressource,
l'expiration, le refus, la révocation et la consommation interdisent tout rejeu.

Avant de fermer ou remplacer une session : `tools.close()`, attendre la fin du
worker, puis `session.close()`. À la réouverture, créer un **nouvel** adaptateur.
Ne pas sérialiser les objets d'approbation ni conserver l'ancien adaptateur.
Les identifiants présents dans l'audit ne permettent pas de restaurer un accord.
Même si l'hôte oublie de fermer l'adaptateur avant la session, l'écriture obligatoire
de référence dans la session fermée échoue avant le lancement du processus.

Les opérations privilégiées ou modifiantes restent refusées, même après accord.
La revue l'annonce. Ne pas contourner ce refus par un shell, un autre exécuteur ou
un sudo implicite.

## Audit réel avec la mission 09

Chaque événement écrit dans `<manager.storage.root>/audit/tools/events.jsonl` est
référencé automatiquement par `session.add_message(role='tool', allow_tool=True)`.
La session conserve ID d'opération/événement, UTC, décision/statut, ID opaque
d'autorisation, références et empreintes des sorties capturées. L'audit contient
également la version, le risque, les temps effectifs, le PID et le code retour.
Le chemin de référence en session est relatif : `audit/tools/events.jsonl`.

`tools.audit_events(operation_id)` lit les événements expurgés de **cette session**,
y compris après réouverture, sans recréer l'opération ni son autorisation. La
lecture est limitée à un journal de 4 Mio ; au-delà, une consultation externe est
nécessaire. Le fichier est verrouillé en lecture/écriture et les symlinks directs
sont refusés.

Le texte des arguments/cibles/scénarios et les sorties brutes ne sont pas persistés.
Le mode validé est conservé, les champs sensibles sont corrélés par HMAC. Les
empreintes SHA-256 portent sur les octets capturés, un préfixe en cas de dépassement.
`retained=False` indique qu'aucun fichier de preuve n'a été conservé. Cet audit
**n'est pas un enregistrement exhaustif permettant le rejeu de la commande**.

Une erreur d'audit/référence session avant lancement bloque l'exécution. Une panne
après lancement peut laisser une trace sans fin : le résultat est indéterminé,
l'accord n'est pas réutilisable. Vérifier l'état réel avant toute nouvelle action.
Si l'historique de mission 09 est désactivé, la session applique sa politique de
non-conservation ; l'audit technique indépendant reste sur disque. La conservation
volontaire de preuves ou des résultats bruts appartient aux API existantes de
ressources/session et à une décision humaine distincte.

## Qualification Kali et recette reproductible

Les tests se répartissent explicitement en trois niveaux :

- **Doubles sûrs** : refus, accord unique, expiration, révocation, altération,
  contexte, délais, interruption, erreurs, volume et absence de secrets.
- **Outils réellement installés sur Kali** : découverte et parcours `/tools` →
  `/prepare` → demande → accord de recette → exécution locale → audit, sur fichiers
  temporaires avec accents, espaces et caractères japonais. `file`, `sha256sum`,
  `strings`, `exiftool` et lecture de signatures `binwalk` ; aucun scan actif,
  DNS/WHOIS, capture vive, privilège ou modification système.
- **TUI assemblée** : non testée ici ; réservée à Codex3. La présente recette exerce
  le même adaptateur et les vraies sessions, sans contrôleur visuel.

L'absence d'outil sur Kali est exercée avec un PATH temporairement vide pour la
seule découverte (aucun paquet retiré). La version inconnue est exercée avec un
petit exécutable synthétique sans version, lancé réellement sur Kali ; ce cas
n'est pas présenté comme le comportement d'un outil système installé.

Qualification constatée sur Kali Rolling 2026.3 / Python 3.13.15 :

- `binwalk --help`, environnement avec `HOME=/nonexistent` : code 0 et sortie vide.
  Avec HOME temporaire existant : bannière **Binwalk v2.4.3**, code 0. Le moteur
  utilise désormais un HOME privé existant et jetable, sans charger la configuration
  de l'utilisateur. La version est détectée depuis l'exécutable, pas déduite du paquet.
  Le paquet installé annonce séparément `2.4.3+dfsg1-3`.
- `tshark -v`, y compris environnement réduit : code **8**, erreur `Dissector bug`
  et nom de filtre invalide. Le moteur expose `probe_diagnostic='dissector_error'`,
  `probe_returncode=8` et **aucune version vérifiée**. Le paquet installé annonce
  `4.4.7-1+b1` ; cette métadonnée n'est pas une preuve de version exécutable ni de
  fonctionnement. La cause interne du dissecteur n'a pas été établie et aucun
  paquet, plugin ou fichier de configuration n'a été modifié pour la masquer.

Commandes de test (MISSION09_SRC désigne le dossier `src` de la référence mission 09) :

```sh
PYTHONPATH=src:"$MISSION09_SRC" python3 -m unittest discover -s tests -p 'test_focus_tool*.py' -v
PYTHONPATH=src:"$MISSION09_SRC" python3 -m unittest discover -s tests -p 'test_focus_permissions.py' -v
PYTHONPATH=src:"$MISSION09_SRC" python3 -m unittest discover -s tests -v
# Uniquement sur la Kali de recette autorisée :
FOCUS_KALI_TESTS=1 PYTHONPATH=src:"$MISSION09_SRC" python3 -m unittest discover -s tests -p 'test_focus_tool*.py' -v
```

Sans mission 09 sur PYTHONPATH, les tests de sessions sont explicitement ignorés.
Sans `FOCUS_KALI_TESTS=1`, les cinq tests de recette Kali sont ignorés. Ces omissions
ne constituent pas des succès de recette. Les fixtures, HOME isolés et racines de
sessions sont temporaires. Aucun document interne ni donnée d'enquête n'est requis.

Résultats de finition du 8 novembre 2026 :

| Vérification | Résultat observé |
| --- | --- |
| Régression Ubuntu / Python 3.14 avec les modules de session mission 09 | 352 cas découverts : **347 réussis**, 5 tests Kali opt-in ignorés ; 17,704 s |
| Parcours outils + recette sur Kali Rolling / Python 3.13.15 | **59 réussis**, aucun ignoré ; 7,143 s |
| Permissions sur Kali | **9 réussis**, aucun ignoré ; 0,013 s |
| Total ciblé Kali | **68 tests réussis** |
| Interfaces mission 09 utilisées | Modules de `43bccf1`, lecture depuis une copie de recette isolée ; aucun changement de leurs fichiers |
| TUI Codex3 | Non assemblée ni testée ici ; branchement documenté ci-dessus |

Les 23 tests conversationnels incluent quatre tests avec les sessions réelles :
audit après réouverture sans restauration d'accord, aller-retour de mode,
changement de cible et refus avec session fermée. Les cinq tests Kali comprennent
les vrais outils installés et deux parcours d'indisponibilité/version inconnue dans
des environnements PATH contrôlés explicitement synthétiques. La recette des vrais
outils ne doit pas être confondue avec ces doubles ni avec une recette TUI.
