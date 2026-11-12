# UCHAMBUZI Focus — Moteur des profils historiques

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note pour 0.3.0-beta.2 : ce document décrit des composants ou recettes historiques.
> Le REPL courant présente quatre Teams ; seule OSINT est active.
> Les anciens profils restent internes et ne sont plus proposés par `/mode`.
> Voir [les commandes actuelles](commandes.md) et [les fonctionnalités](fonctionnalites.md).


**Document technique de référence — Mission 06**  
**Auteur :** Agy2  
**Date :** 8 novembre 2026  
**Statut :** Livré et testé  

---

## 1. Vue d'ensemble

Le moteur de modes d'UCHAMBUZI Focus dote l'assistant d'une spécialisation professionnelle réelle. Contrairement à un simple artifice visuel ou à un changement superficiel de ton, chaque mode structure en profondeur la posture analytique du modèle d'IA, ses méthodologies de travail, ses catégories d'outils prioritaires et ses formats de réponse.

Ce moteur est entièrement écrit en **Python 3 standard** (respect de la décision **D-025**, zéro dépendance pip obligatoire) et s'intègre rigoureusement aux contrats v1 définis dans `src/focus_contracts.py`.

---

## 2. Les profils historiques natifs

| N° | Mode | Spécialisation | Badge TUI | Token visuel | Outils Kali emblématiques |
|---|---|---|---|---|---|
| **01** | **Assist** | Assistant généraliste & pédagogique *(par défaut)* | `[01 ASSIST]` | `cyan` | `man`, `info`, `which`, `ss`, `ip` |
| **02** | **Trace** | Forensic, préservation de preuve & DFIR | `[02 TRACE]` | `blue` | `sleuthkit`, `autopsy`, `volatility3`, `sha256sum`, `fls` |
| **03** | **Intel** | Renseignement numérique, OSINT & Threat Intel | `[03 INTEL]` | `yellow` | `whois`, `dig`, `amass`, `theharvester`, `dnsrecon` |
| **04** | **Defend** | Défense Blue Team, SOC & réponse aux incidents | `[04 DEFEND]` | `green` | `journalctl`, `auditd`, `zeek`, `suricata`, `chainsaw` |
| **05** | **Assess** | Audit de sécurité & Red Team autorisée | `[05 ASSESS]` | `red` | `nmap`, `nikto`, `nuclei`, `gobuster`, `testssl.sh` |
| **06** | **Validate** | Purple Team & émulation d'adversaire MITRE | `[06 VALIDATE]` | `magenta` | `atomic-red-team`, `caldera`, `sigma-cli`, `sysmon` |
| **07** | **Engineer** | Ingénierie système, administration & durcissement | `[07 ENGINEER]` | `white` | `iptables`, `nftables`, `systemctl`, `sysctl`, `openssl` |
| **08** | **Coordinate** | White Team, coordination de crise & gouvernance | `[08 COORDINATE]` | `cyan` | `tabletop_planner`, `raci_generator`, `retex_template` |

---

## 3. Différences concrètes de comportement

### Exemple comparatif : « Comment analyser cette adresse IP ? » (`198.51.100.25`)

1. **Mode Trace (`trace`)** :
   - *Priorité* : Intégrité probatoire, absence d'altération et traçabilité.
   - *Méthode* : Extraction passive des flux pcaps horodatés, préservation des métadonnées de connexion, calcul d'empreinte SHA-256 des fichiers de capture, consultation des journaux en lecture seule stricte.
   - *Structure* : `[Intégrité & Preuves]`, `[Méthode forensique]`, `[Commandes sécurisées (lecture seule)]`, `[Limites & chaîne de conservation]`.

2. **Mode Intel (`intel`)** :
   - *Priorité* : Connaissance de la menace, cartographie de l'infrastructure et qualification des sources.
   - *Méthode* : Résolution inverse passive, recherche ASN, blocs BGP, historique WHOIS, corrélation CTI et détection de pivots (domaines associés, certificats SSL/TLS). Distinction formelle des faits observés et des hypothèses.
   - *Structure* : `[Qualification IoC]`, `[Infrastructure & Pivots]`, `[Corrélation CTI]`, `[Niveau de certitude & Sources]`.

3. **Mode Defend (`defend`)** :
   - *Priorité* : Réduction du risque opérationnel, détection SOC et confinement de l'incident.
   - *Méthode* : Triage dans les journaux d'authentification (`journalctl`, syslog), inspection de la télémétrie réseau (Zeek/Suricata), proposition de blocage réversible (`nftables`/`fail2ban`) et création d'une règle de détection Sigma préventive.
   - *Structure* : `[Triage & Risque]`, `[Analyse des journaux]`, `[Confinement d'urgence]`, `[Règles de détection]`.

4. **Mode Assess (`assess`)** :
   - *Priorité* : Respect strict du mandat écrit et évaluation non destructive.
   - *Méthode* : Vérification des Rules of Engagement (RoE) et du périmètre contractualisé. Scan de ports méthodique et non intrusif (`nmap`), inventaire des bannières et recherche de vulnérabilités connues sans exploit destructeur.
   - *Structure* : `[Périmètre & Autorisation]`, `[Constat technique]`, `[Validation sécurisée]`, `[Recommandations de remédiation]`.

5. **Mode Validate (`validate`)** :
   - *Priorité* : Validation de l'efficacité des défenses et couverture MITRE ATT&CK.
   - *Méthode* : Association de la technique adverse (ex: T1071 — Application Layer Protocol), élaboration d'un test atomique contrôlé et réversible, vérification de l'alerte attendue dans les journaux SOC et mesure de l'écart de visibilité (gap analysis).
   - *Structure* : `[Technique ATT&CK]`, `[Test atomique contrôlé]`, `[Télémétrie attendue]`, `[Calibration de détection]`.

---

## 4. Architecture logicielle

### 4.1 Modules créés
- `src/focus_modes.py` : Moteur complet des profils historiques, définitions immuables, compositeur d'instructions, registre extensible, observateurs d'événements, adaptateur de session et catalogue.
- `src/focus_profiles.py` : Pont d'intégration vers les contrats Focus, exposant `DEFAULT_PROFILES` et `FocusProfilesCatalog` compatibles avec `focus_contracts.Catalog`.
- `tests/test_focus_modes.py` : Suite de 17 tests couvrant les 15 exigences obligatoires de la mission 06, les tests comparatifs et les tests d'intégration avec un runtime réel/simulé.
- `tests/test_focus_profiles.py` : Tests de validation des contrats de profils et du catalogue.

### 4.2 Points d'intégration pour les autres missions

| Mission | Responsabilité | Interface fournie par Mission 06 |
|---|---|---|
| **Mission 07** *(Scénarios)* | Scénarios professionnels par mode | `FocusMode.scenario_compatibility`, `FocusModesCatalog.scenarios(profile_id)`, composition d'instructions acceptant `active_scenario`. |
| **Mission 08** *(Outils)* | Préparation de commandes et outils | `FocusMode.recommended_tool_categories`, `FocusMode.recommended_tools`. Permet au sélecteur d'outils de prioriser les catégories de la spécialité active. |
| **Mission 09** *(Permissions)* | Confirmations et gouvernance | Invariant strict vérifié : aucun changement de mode n'altère les permissions système (`UID`/`GID`/`EUID`). Les modes adaptent le raisonnement de l'assistant, jamais les autorisations de l'OS. |
| **Mission 11** *(Paramètres & TUI)* | Commande `/mode` & animations graphiques | `ModeEngine.switch_mode(id)` émet `ModeTransitionEvent` contenant `animation_hints` (`badge`, `accent_token`, `glyph`, `duration_ms`, `transition_type`). |

---

## 5. Garanties de sécurité et invariants

1. **Aucune élévation de privilèges** : Le basculement de mode est une opération purement logique en mémoire Python. Aucune commande shell ni modification des attributs de processus n'est déclenchée.
2. **Pas d'exécution automatique** : Conformément à **D-013** et au mandat **MANDAT.md**, toutes les commandes proposées restent des suggestions textuelles explicites soumises à confirmation humaine.
3. **Protection contre l'exécution de code arbitraire** : Le registre `ModeRegistry.register_custom_mode` valide strictement les types, rejette les objets callables/exécutables et sanctuarise les profils historiques natifs contre tout écrasement ou suppression.
4. **Isolation du contexte** : `ModeAwareConversationAdapter` purge les métadonnées transitoires de l'ancienne spécialité lors d'un changement de mode, empêchant toute contamination de directives entre investigations distinctes.
