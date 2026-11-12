# UCHAMBUZI Focus — Moteur des 24 scénarios professionnels et orchestration contextuelle

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note pour 0.3.0-beta.2 : ce document décrit des composants ou recettes historiques.
> Le REPL courant présente quatre Teams ; seule OSINT est active.
> Les anciens profils restent internes et ne sont plus proposés par `/mode`.
> Voir [les commandes actuelles](commandes.md) et [les fonctionnalités](fonctionnalites.md).


**Document technique de référence — Mission 07**  
**Auteur :** Agy2  
**Date :** 8 novembre 2026  
**Statut :** Livré et testé  

---

## 1. Vue d'ensemble et objectifs

Le moteur de scénarios professionnels d'UCHAMBUZI Focus dote chaque mode professionnel de cadres méthodologiques opérationnels précis. Alors que le **mode** établit la posture analytique générale et la spécialité métier (DFIR, CTI, SOC, Pentest, etc.), le **scénario** structure l'intervention concrète :

1. Les questions préalables indispensables et les données nécessaires ;
2. La méthodologie séquentielle étape par étape ;
3. Le schéma des paramètres requis et facultatifs validés sans exécution de code ;
4. La structure de réponse attendue imposée au modèle IA ;
5. Les catégories d'outils et exécutables Kali recommandés ;
6. Les limites légales, forensiques et précautions de non-perturbation ;
7. Les critères d'achèvement permettant de qualifier la fin du travail.

### Invariant majeur : Scénario facultatif
Le scénario n'est **jamais obligatoire** : l'utilisateur conserve la liberté totale de converser librement dans les profils historiques sans activer de scénario.

Ce développement respecte rigoureusement la décision **D-025** (Python 3 standard exclusif, zéro dépendance pip obligatoire) et s'intègre directement au moteur de la Mission 06 sans modifier ses contrats partagés.

---

## 2. Catalogue des 24 scénarios professionnels natifs

Le catalogue initial obligatoire compte **24 scénarios professionnels**, répartis équitablement à raison de 3 scénarios par mode :

```
                                  UCHAMBUZI FOCUS
                                         │
        ┌─────────────┬─────────────┬────┴────────┬─────────────┬─────────────┐
        ▼             ▼             ▼             ▼             ▼             ▼
   [01 ASSIST]   [02 TRACE]    [03 INTEL]    [04 DEFEND]   [05 ASSESS]   [06 VALIDATE]  ... [07 ENGINEER, 08 COORDINATE]
        │             │             │             │             │             │
        ├─ Technical  ├─ Digital    ├─ Infra      ├─ Incident   ├─ Security   ├─ ATT&CK
        │  Guidance   │  Evidence   │  Intel      │  Triage     │  Assessment │  Mapping
        ├─ Trouble-   ├─ Timeline   ├─ Indicator  ├─ Log        ├─ Vulnerabi- ├─ Detection
        │  shooting   │  Analysis   │  Enrichment │  Investig.  │  lity Review│  Validation
        └─ Script     └─ Memory     └─ Threat     └─ Threat     └─ Authorized └─ Purple Team
           Assistance    Forensics     Research      Hunting       Pentest       Exercise
```

### 2.1 ASSIST (Assistance générale & pédagogique)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `technical_guidance` | **Technical Guidance** | Expliquer en détail le fonctionnement, les concepts, la syntaxe et les options d'une commande ou protocole. | `man`, `info`, `which`, `apropos`, `tldr` | `[GUIDANCE]` |
| `troubleshooting` | **Troubleshooting** | Diagnostiquer méthodiquement une anomalie logicielle, réseau ou système sans altérer l'environnement. | `journalctl`, `dmesg`, `ss`, `ip`, `systemctl`, `lsof` | `[TROUBLE]` |
| `script_assistance` | **Script Assistance** | Concevoir, auditer et sécuriser des scripts techniques Shell/Python avec gestion stricte des erreurs et idempotence. | `bash`, `python3`, `shellcheck`, `shfmt` | `[SCRIPT]` |

### 2.2 TRACE (Digital Forensics & Incident Response)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `digital_evidence` | **Digital Evidence** | Consigner les scellés, calculer les empreintes SHA-256 et garantir la chaîne de conservation sur copie bit-à-bit. | `sha256sum`, `dc3dd`, `ewf-tools`, `sleuthkit`, `losetup` | `[EVIDENCE]` |
| `timeline_analysis` | **Timeline Analysis** | Reconstruire une chronologie unifiée en UTC à partir des horodatages MACB et des journaux d'activité. | `fls`, `mactime`, `log2timeline`, `plaso`, `sleuthkit` | `[TIMELINE]` |
| `memory_forensics` | **Memory Forensics** | Analyser une capture de RAM pour détecter processus masqués (DKOM), sockets actifs et injections malfind. | `volatility3`, `volatility`, `bulk_extractor`, `strings` | `[MEMORY]` |

### 2.3 INTEL (Renseignement cyber, OSINT & CTI)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `infrastructure_intelligence` | **Infrastructure Intelligence** | Cartographier passivement l'infrastructure adverse (adresses IP, ASN, BGP, sous-domaines, certificats TLS). | `whois`, `dig`, `amass`, `sublist3r`, `curl`, `jq` | `[INFRA]` |
| `indicator_enrichment` | **Indicator Enrichment** | Contextualiser et qualifier des indicateurs de compromission (IoC) par recoupement CTI en sources ouvertes. | `curl`, `jq`, `whois`, `dig`, `sha256sum` | `[ENRICH]` |
| `threat_research` | **Threat Research** | Caractériser les modes opératoires et campagnes de menace avec la taxonomie Diamond Model et MITRE ATT&CK. | `curl`, `jq`, `grep`, `python3` | `[RESEARCH]` |

### 2.4 DEFEND (Blue Team, SOC & Réponse aux incidents)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `incident_triage` | **Incident Triage** | Qualifier la sévérité d'une alerte, évaluer le rayon d'impact et définir des mesures conservatoires réversibles. | `journalctl`, `ss`, `iptables`, `nftables`, `lsof` | `[TRIAGE]` |
| `log_investigation` | **Log Investigation** | Interroger et corréler des journaux d'activité (auth, web, proxy) via des requêtes ciblées sans bruit opérationnel. | `grep`, `awk`, `journalctl`, `sed`, `jq`, `zgrep` | `[LOGS]` |
| `threat_hunting` | **Threat Hunting** | Formuler des hypothèses proactives de traque basées sur des TTPs et convertir les résultats en règles Sigma. | `yara`, `auditd`, `journalctl`, `ss`, `find` | `[HUNTING]` |

### 2.5 ASSESS (Audit technique & Évaluation autorisée)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `security_assessment` | **Security Assessment** | Établir la cartographie de surface d'attaque et le plan d'audit dans les limites strictes du mandat écrit. | `nmap`, `nikto`, `sslyze`, `curl`, `testssl` | `[ASSESS]` |
| `vulnerability_review` | **Vulnerability Review** | Évaluer l'exploitabilité réelle en contexte, le score CVSS environnemental et les mesures palliatives immédiates. | `cve-search`, `searchsploit`, `curl`, `jq` | `[VULN]` |
| `authorized_penetration_test` | **Authorized Penetration Test** | Valider de manière contrôlée des vecteurs d'intrusion avec preuves de concept (PoC) minimales non destructives. | `nmap`, `hydra`, `sqlmap`, `curl`, `wfuzz` | `[PENTEST]` |

### 2.6 VALIDATE (Purple Team & Validation MITRE ATT&CK)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `attck_mapping` | **ATT&CK Mapping** | Associer précisément les actions offensives simulées aux identifiants TTPs et Data Sources MITRE ATT&CK. | `python3`, `jq`, `curl` | `[ATTCK]` |
| `detection_validation` | **Detection Validation** | Vérifier l'émission d'alerte, la télémétrie capturée et mesurer le temps de détection (MTTD) face à un test atomique. | `auditd`, `journalctl`, `curl`, `python3` | `[DETECTION]` |
| `purple_team_exercise` | **Purple Team Exercise** | Synchroniser les simulations Red Team et la détection Blue Team en direct pour optimiser immédiatement les règles. | `auditd`, `journalctl`, `ss`, `yara`, `python3` | `[PURPLE]` |

### 2.7 ENGINEER (Ingénierie, Administration & Durcissement)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `system_hardening` | **System Hardening** | Construire une configuration de référence sécurisée (sysctl, services minimaux, droits) selon les guides ANSSI/CIS. | `sysctl`, `ss`, `systemctl`, `chmod`, `chown`, `auditd` | `[HARDEN]` |
| `network_security` | **Network Security** | Auditer et définir les règles de filtrage (nftables/iptables) avec politique DROP par défaut et anti-verrouillage. | `nft`, `iptables`, `ip`, `ss`, `tcpdump`, `wireguard` | `[NETSEC]` |
| `security_automation` | **Security Automation** | Concevoir des automatisations techniques idempotentes intégrant un mode simulation (`--dry-run`) et traces d'audit. | `python3`, `bash`, `systemd`, `cron`, `ansible` | `[AUTOMATION]` |

### 2.8 COORDINATE (Coordination, RoE & Gouvernance)

| Identifiant | Nom | Objectif professionnel | Outils Kali | Badge |
|---|---|---|---|---|
| `exercise_planning` | **Exercise Planning** | Concevoir un exercice de cybersécurité avec tableau d'injections scénarisées (MSEL) et grille d'observation. | `libreoffice`, `pandoc`, `python3` | `[EXERCISE]` |
| `rules_of_engagement` | **Rules of Engagement** | Formaliser la convention d'opération (RoE), les exclusions explicites et la procédure d'arrêt d'urgence. | `pandoc`, `git` | `[ROE]` |
| `after_action_review` | **After Action Review** | Conduire le retour d'expérience (RETEX / Post-Mortem) constructif avec plan d'actions correctives SMART. | `pandoc`, `python3`, `git` | `[RETEX]` |

---

## 3. Moteur d'orchestration contextuelle (`ContextOrchestrator`)

Le module `src/focus_orchestrator.py` intègre la classe `ContextOrchestrator` chargée de composer le prompt système envoyé au modèle de langage.

### 3.1 Ordre strict et déterministe de composition

```
1. En-tête et posture du Mode professionnel actif
2. Instructions professionnelles et méthodologie du Mode
3. Règles de présentation propres au Mode
4. [Si scénario actif] :
   - Titre, objectif et description du scénario
   - Instructions spécialisées du scénario
   - Méthodologie séquentielle du scénario
   - Structure de réponse attendue
   - Critères d'achèvement du travail
   - Prérequis et limites opérationnelles du scénario
   - Paramètres de travail validés (triés par nom)
   - [Si aucune cible] : Rappel des questions et données requises
5. Contrôle de présence effective des outils sur le PATH local :
   - Outils vérifiés présents
   - Outils absents signalés avec consigne stricte anti-hallucination
6. Contexte d'investigation courant (cible, indice actif)
7. Ressources de travail explicitement accessibles
8. Contraintes de session (temps, budget, isolation)
9. Socle invariable des règles communes de sécurité et déontologie
```

### 3.2 Contrôle effectif des outils et garde-fous anti-hallucination

L'orchestrateur inspecte le `PATH` local via `shutil.which` (sans aucune exécution de binaire).
- Si un outil recommandé est absent du système (par exemple `volatility3` non installé), une section dédiée est injectée :
  ```text
  --- OUTILS RECOMMANDES NON TROUVES SUR LE SYSTEME LOCAL ---
  Outils absents du PATH : volatility3.
  CONSIGNE STRICTE : N'invente aucun résultat, fausse sortie ou version pour ces outils absents. Signale leur absence à l'utilisateur et propose des alternatives locales ou des procédures d'installation officielles.
  ```

### 3.3 Gestion des investigations avec données manquantes

Si l'utilisateur active un scénario d'investigation sans spécifier d'indice ni de cible, l'orchestrateur injecte un rappel explicite :
```text
--- DONNEES REQUISES ET QUESTIONS PREALABLES DU SCENARIO ---
Certaines données nécessaires à ce scénario n'ont pas encore été fournies :
  ? Chemin du fichier image bit-à-bit ou artefact à examiner.
  ? Empreinte SHA-256 de référence si disponible.
CONSIGNE STRICTE : Demande explicitement à l'utilisateur de fournir ces données ou de préciser son périmètre avant de formuler des recommandations avancées.
```

---

## 4. Gestion du cycle de vie et transitions (`ScenarioManager`)

`ScenarioManager` synchronise l'état du mode actif et du scénario actif :

### 4.1 Changement de mode avec désélection automatique
Lorsqu'un utilisateur passe d'un mode à un autre (ex: `Trace + Digital Evidence` vers `Validate`), `ScenarioManager` détecte que `digital_evidence` n'est pas compatible avec `validate`.
Il désélectionne automatiquement le scénario, purge les paramètres et émet un `ScenarioTransitionEvent` avec `new_scenario_id=None`.

**Résultat :** Les consignes du scénario précédent cessent immédiatement de s'appliquer. Aucune consigne orpheline ne persiste dans le prompt.

### 4.2 Événements exploitables par la TUI

Chaque transition émet un événement structuré `ScenarioTransitionEvent` contenant des indices pour la future TUI (Mission 11) :

```python
@dataclass(frozen=True)
class ScenarioTransitionEvent:
    previous_scenario_id: str | None
    new_scenario_id: str | None
    mode_id: str
    parameters: Mapping[str, Any]
    timestamp: float
    tui_metadata: ScenarioTUIMetadata | None
    reason: str = ''
    animation_hints: Mapping[str, Any] = field(default_factory=dict)
```

Indices d'animation fournis :
- `transition_type` : `'scenario_select'`, `'scenario_deselect'`
- `badge` : e.g. `'[EVIDENCE]'`, `'[LIBRE]'`
- `glyph` : e.g. `'📁'`, `'💬'`
- `duration_ms` : e.g. `100`, `80`

---

## 5. Scénarios personnalisés (`custom=True`)

Le registre `ScenarioRegistry` permet d'enregistrer des scénarios personnalisés répondant à des besoins opérationnels spécifiques :

1. **Validation stricte** : types de champs vérifiés, identifiant slug `^[a-z0-9][a-z0-9_-]{1,47}$`, listes de chaînes non vides.
2. **Interdiction d'exécution de code** : rejet absolu de tout objet exécutable ou callable dans la définition.
3. **Protection des 24 natifs** : interdiction formelle d'écraser (`register_custom_scenario`) ou de supprimer (`unregister_custom_scenario`) l'un des 24 scénarios de base.
4. **Schéma de paramètres typé** : chaque paramètre supporte les types `'string'`, `'integer'`, `'boolean'`, `'choice'`, `'path'`, `'ip_or_domain'`, `'list'` avec validation et valeurs par défaut.

---

## 6. Commandes interactives TUI / CLI

La classe `ScenarioCommandHandler` expose l'analyseur des commandes `/scenario` et `/mode` :

| Commande | Action | Exemple |
|---|---|---|
| `/scenario` | Affiche l'état du scénario actif et ses paramètres | `/scenario` |
| `/scenario list [mode]` | Liste les scénarios disponibles pour un mode | `/scenario list trace` |
| `/scenario select <id> [k=v ...]` | Sélectionne un scénario avec paramètres optionnels | `/scenario select digital_evidence evidence_type=memory_dump` |
| `/scenario show <id>` | Affiche la fiche détaillée d'un scénario | `/scenario show timeline_analysis` |
| `/scenario clear` | Revient à la conversation libre dans le mode actif | `/scenario clear` |
| `/scenario params [k=v ...]` | Met à jour les paramètres du scénario actif | `/scenario params timezone=UTC` |
| `/mode <id>` | Bascule vers un mode professionnel | `/mode intel` |
| `/team` | Liste les quatre Teams, OSINT seule active | `/team` |
| `/mode reset` | Réinitialise vers Assist par défaut | `/mode reset` |

---

## 7. Preuve de spécialisation : Tests comparatifs

Les tests démontrent que la spécialisation n'est pas cosmétique :

### Même question dans deux scénarios du même mode (`TRACE`) :
- **Digital Evidence** : focalise l'analyse sur l'empreinte SHA-256, les scellés physiques, le montage passif `loop ro` et le journal de manipulation légale.
- **Timeline Analysis** : focalise l'analyse sur la normalisation UTC, les horodatages MACB (fls/mactime) et la détection d'antidatage (timestomping).

### Même question dans deux modes différents :
- **Defend + Incident Triage** : évalue la sévérité P1-P4, le rayon d'impact et les mesures conservatoires réversibles (blocage pare-feu temporaire).
- **Assess + Authorized Penetration Test** : valide le mandat signé, les RoE, la reconnaissance non intrusive et la preuve de concept minimale non destructive.

---

## 8. Validation et couverture des tests

Une suite exhaustive de 28 tests unitaires et d'intégration a été livrée dans `tests/test_focus_scenarios.py` :
- Les 24 exigences du mandat sont validées point par point.
- Tous les 312 tests de régression de l'ensemble du projet réussissent (100% OK).
- Zéro dépendance pip externe.
- Headers réglementaires conformes aux hooks Git locaux.

---

## 9. Points de raccordement pour Codex3 (Intégration finale)

Dans le cadre de l'ordre de finalisation des missions 06 et 07, les adaptateurs autonomes et ponts suivants ont été intégrés dans `src/focus_orchestrator.py`, `src/focus_profiles.py` et `src/focus_modes.py` pour un branchement immédiat et transparent par le coordinateur `Codex3` :

### 9.1 Raccordement TUI et Sélecteurs (Mission 11)
- **Signature double pour `get_scenario`** : `FocusProfilesCatalog.get_scenario(profile_id, scenario_id)` et `FocusProfilesCatalog.get_scenario(scenario_id)` sont toutes deux supportées (appel direct par `focus_settings_ui.py` ligne 256/410).
- **Génération d'éléments pour sélecteurs TUI** :
  - `FocusProfilesCatalog.scenario_items(profile_id=None)` génère des instances `focus_selectors.Item` compatibles avec les menus de sélection TUI, incluant l'option standard `Item('off', 'Aucun scenario (conversation libre)')`.
  - `FocusProfilesCatalog.mode_items()` génère les `Item` pour les profils historiques.
- **Support de la commande `/scenario off`** dans `ScenarioCommandHandler` pour correspondre à la sélection TUI.

### 9.2 Pont Sessions et Persistance (Mission 09)
- **`SessionScenarioBridge`** (`src/focus_orchestrator.py`) :
  - `sync_to_session(session)` : sérialise de manière sûre le mode actif, le scénario actif, les paramètres validés et les métadonnées TUI dans `session.data`.
  - `restore_from_session(session)` : restaure l'état opérationnel complet depuis la session persistée.
  - **Invariants d'isolation et de sécurité** :
    - Filtre automatiquement les clés sensibles (mots de passe, tokens, clés privées).
    - Purge les instructions transitoires et les autorisations temporaires (aucun droit d'exécution implicite conservé entre sessions ou transitions).

### 9.3 Raccordement Outils et Audit de Versions (Mission 10)
- **`ToolServiceBridge`** (`src/focus_orchestrator.py`) :
  - `inspect_tools_for_scenario(scenario_id)` s'appuie sur `focus_tools.FocusToolService` pour auditer le statut réel des outils préconisés sur le système local.
  - Distingue formellement :
    1. Outil vérifié présent avec version identifiée.
    2. Outil présent mais version non vérifiée (signalée obligatoirement comme `inconnue`).
    3. Outil manquant sur le système local (marqué comme absent avec interdiction d'inventer des résultats).
- **Consignes strictes anti-hallucination** dans le prompt composé :
  - Interdiction de simuler ou deviner la sortie d'un outil non exécuté.
  - Approbation humaine préalable obligatoire avant toute exécution de commande.

### 9.4 Adaptateur IA Streaming (Mission 08)
- **`ScenarioAIAdapter`** (`src/focus_orchestrator.py`) :
  - `stream_turn(turn_id, user_text)` relie le `ScenarioManager` à `FocusAI.stream(...)`.
  - Compile dynamiquement l'instruction système complète (Règles globales → Mode actif → Scénario facultatif → Paramètres validés → Avertissements outils/données requises) et l'injecte dans le modèle.
  - Isole strictement les contextes entre tours et lors des changements de scénarios.

### 9.5 Validation réelle avec le modèle local
- La suite de tests d'intégration croisée `tests/test_focus_integration.py` a été exécutée avec succès contre le serveur local Ollama (`qwen2.5:3b` sur `127.0.0.1:11434`), validant la chaîne complète de streaming de réponse IA sous cadrage professionnel strict.

