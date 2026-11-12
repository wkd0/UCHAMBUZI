# Architectures d'intelligence artificielle et intégration des modèles

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Périmètre historique du candidat Textual : le parcours local Ollama est prévu ; l'adaptateur OpenAI présent dans les modules expérimentaux est refusé par l'interface Textual tant qu'elle ne peut pas afficher et recueillir le consentement requis. Les architectures décrites sont des options et contrats, pas une validation de bout en bout.

Dans la version 1.0.0, les accès Responses et Claude Code sont disponibles avec consentement ;
les profils nommés et le stockage facultatif des clés sont décrits dans le
[guide courant](installation.md#fournisseurs-ia-distants-facultatifs). Les sections
ci-dessous conservent les contrats et options historiques.

UCHAMBUZI propose une architecture modulaire et découplée pour l'assistance par intelligence artificielle. Le cœur de l'application (reconnaissance d'indices, inventaire des outils, recherche documentaire locale, préparation de commandes) fonctionne de manière autonome. Lorsqu'une capacité conversationnelle est souhaitée, UCHAMBUZI peut s'appuyer sur plusieurs topologies d'exécution.

---

## 1. Principes directeurs de l'intégration IA

1. **Assistance et non substitution** : le moteur IA sert d'aide au dialogue, à la clarification des objectifs et à la synthèse documentaire. Il ne pilote aucun outil et ne valide aucune commande à la place de l'enquêteur.
2. **Priorité au mode local** : pour préserver le secret professionnel, l'étanchéité des enquêtes et l'intégrité de la chaîne de conservation des preuves numériques, le fonctionnement local et hors ligne reste le mode privilégié par défaut.
3. **Séparation étanche des données** : le contexte technique structuré (indices, références, avertissements) est transmis au modèle comme donnée utilisateur non vérifiée, jamais comme directive système.
4. **Indépendance vis-à-vis des runtimes** : UCHAMBUZI communique via des interfaces d'adaptateurs standardisées (protocoles HTTP/REST locaux ou distants), permettant d'adapter le moteur sous-jacent selon l'environnement de travail.

---

## 2. Synthèse des trois architectures

| Caractéristique | Architecture A (Locale) | Architecture B (Équipement local dédié) | Architecture C (API distante facultative) |
| --- | --- | --- | --- |
| **Emplacement du moteur IA** | Même machine (Kali Linux) | Autre équipement sur réseau privé local | Fournisseur cloud externe |
| **Accès réseau requis** | Aucun (loopback 127.0.0.1) | Réseau local privé (tunnel sécurisé) | Accès Internet (HTTPS port 443) |
| **Confidentialité forensique** | Dépend de l'isolation du runtime et du poste | Forte (données restreintes au réseau privé) | Dépendante de la politique du tiers |
| **Ressources requises** | Partagées avec Kali Linux | Déportées sur l'équipement dédié | Très faibles sur la machine locale |
| **Statut dans UCHAMBUZI** | **Runtime local disponible ; interface à recetter** | **Cible non qualifiée** | **Adaptateur expérimental ; refusé par l'interface Textual actuelle** |

---

## 3. Architecture A — IA locale sur Kali Linux

Dans cette architecture, UCHAMBUZI et le moteur d'inférence s'exécutent sur la même machine Kali Linux (qu'il s'agisse d'une installation sur machine physique ou d'une machine virtuelle dédiée).

```
+-------------------------------------------------------------+
|                     Machine Kali Linux                      |
|                                                             |
|  +-------------------+              +--------------------+  |
|  |     UCHAMBUZI     |   HTTP REST  |   Moteur IA local  |  |
|  |  (Terminal CLI)   | -----------> | (ex. Ollama local) |  |
|  |                   | <----------- |                    |  |
|  +-------------------+  127.0.0.1   +--------------------+  |
|                                                |            |
|                                                v            |
|                                       +------------------+  |
|                                       |   Modèle local   |  |
|                                       |  (ex. compact)   |  |
|                                       +------------------+  |
+-------------------------------------------------------------+
```

### Avantages
- **Autonomie totale** : fonctionne sans connexion Internet ni équipement tiers.
- **Maîtrise des flux** : le client utilise loopback. Vérifier le runtime, ses alias et son isolation ; ce raccordement ne garantit pas à lui seul que les données restent sur la machine.
- **Simplicité opérationnelle** : un seul système à administrer.

### Contraintes et ressources
- Les ressources matérielles (processeur, mémoire vive, carte graphique éventuelle) sont partagées entre le système d'exploitation, les outils d'investigation et le moteur d'inférence.
- Le choix du modèle dépend de la mémoire vive disponible. La recette disponible porte sur qwen2.5:3b ; elle ne démontre pas une fluidité générale ni la compatibilité des autres modèles.
- Aucun comparatif de performances entre installation physique et VM n'a été réalisé dans cette recette.

### Statut opérationnel
L'adaptateur `OllamaRuntime` d'UCHAMBUZI est opérationnel pour dialoguer avec un service local écoutant sur `127.0.0.1` (port standard 11434). Il applique un délai d'attente borné (`--timeout`), vérifie le nom du modèle et refuse expressément les suffixes `:cloud`.

---

## 4. Architecture B — IA sur un équipement local dédié

Dans cette configuration, UCHAMBUZI s'exécute sur le poste de travail Kali Linux, tandis que le moteur d'inférence est hébergé sur une autre machine du réseau local privé (serveur d'inférence local ou station de travail dédiée disposant de ressources matérielles adaptées).

```
+--------------------------+                     +---------------------------+
|    Poste Kali Linux      |                     |  Équipement local dédié   |
|                          |                     |    (Serveur / Station)    |
|  +--------------------+  |    Tunnel privé     |  +---------------------+  |
|  |    UCHAMBUZI       |  |     sécurisé        |  |   Moteur d'inférence|  |
|  |  (Terminal CLI)    |  |  (ex. tunnel SSH)   |  |   (ex. Ollama /     |  |
|  |                    |  | ==================> |  |   llama-server)     |  |
|  | Raccord loopback   |  |                     |  +---------------------+  |
|  | local redirigé     |  | <================== |             |             |
|  +--------------------+  |                     |             v             |
|                          |                     |  +---------------------+  |
|                          |                     |  |  Modèle de grande   |  |
|                          |                     |  |  capacité           |  |
|                          |                     |  +---------------------+  |
+--------------------------+                     +---------------------------+
```

### Avantages
- **Décharge du poste de travail** : les calculs d'inférence lourds ne mobilisent pas les ressources du poste d'investigation.
- **Modèles de plus grande capacité** : permet d'exploiter des modèles plus riches (7B, 14B ou supérieurs quantifiés) grâce aux capacités de l'équipement dédié.
- **Conservation de l'isolation** : les données demeurent cantonnées au réseau local privé d'investigation.

### Exigences réseau et de sécurité
- **Sécurisation obligatoire du canal** : le port d'inférence ne doit pas être exposé en clair sur le réseau local. L'utilisation d'un tunnel SSH chiffré (`ssh -L ...`) restreint au loopback est la méthode recommandée pour acheminer les requêtes.
- **Authentification forte** : contrôle strict des accès par clés SSH et filtrage firewall restrictif.

### Mise en garde et statut
> **Important :** L'Architecture B constitue une **cible de conception en cours d'évaluation**. Elle ne doit pas être considérée comme pleinement opérationnelle tant que les procédures de raccordement automatisé et les tests d'étanchéité n'ont pas été formellement validés.

---

## 5. Architecture C — API externe d'intelligence artificielle facultative

Un adaptateur d'API externe existe à titre expérimental dans les modules. L'interface Textual actuelle refuse son activation faute de mécanisme de consentement par requête ; le parcours distant décrit ci-dessous n'est pas une fonction disponible dans cette interface.

```
+--------------------------+                     +---------------------------+
|    Poste Kali Linux      |                     |  Fournisseur d'API tiers  |
|                          |                     |                           |
|  +--------------------+  |    HTTPS / TLS      |  +---------------------+  |
|  |    UCHAMBUZI       |  |  (port standard 443)|  |   Service d'API     |  |
|  |                    |  | ------------------> |  |   (ex. OpenAI)      |  |
|  | - Prévisualisation |  |                     |  +---------------------+  |
|  | - Consentement     |  | <------------------ |             |             |
|  | - Clé masquée      |  |                     |             v             |
|  +--------------------+  |                     |  +---------------------+  |
|                          |                     |  | Modèle hébergé      |  |
|                          |                     |  +---------------------+  |
+--------------------------+                     +---------------------------+
```

### Garde-fous et règles de sécurité strictes

Les contrôles suivants limitent les transmissions implicites ; ils ne détectent pas toutes les données sensibles :

1. **Aucune activation implicite** : aucun fournisseur distant n'est activé par défaut. La configuration doit être explicitement demandée par l'utilisateur via la commande `/settings`.
2. **Gestion protégée de la clé d'API** :
   - La clé d'API doit être définie dans l'environnement système (`OPENAI_API_KEY`).
   - Le logiciel ne demande jamais la saisie de la clé dans le terminal et ne la persiste jamais sur disque.
   - La valeur exacte de la clé connue est masquée dans les affichages prévus du parcours distant ; le filtre ne reconnaît pas tous les secrets ou encodages.
3. **Prévisualisation intégrale et consentement par requête** :
   - Avant chaque émission vers l'API distante, le corps JSON complet et l'adresse du point de terminaison sont affichés à l'écran.
   - La transmission n'a lieu que si l'utilisateur saisit formellement `oui`.
4. **Étanchéité des données d'enquête** :
   - Aucun fichier d'indice, aucune capture réseau, aucune sortie brute d'outil d'investigation ni aucun historique de session n'est joint automatiquement à une requête distante.
   - L'enquêteur est seul responsable de reformuler manuellement sa question en éliminant tout identifiant sensible (noms d'hôtes internes, adresses IP d'infrastructure privée, données à caractère personnel).
5. **Absence de basculement automatique (*no auto-fallback*)** :
   - En cas d'erreur de réseau, de dépassement de quota ou de refus du fournisseur distant, UCHAMBUZI ne tente aucun repli automatique vers un autre service ni vers le moteur local. L'erreur est signalée et l'utilisateur conserve la maîtrise.
6. **Contrôle des réponses partielles et coûts** :
   - Toute réponse dont le motif d'achèvement (`finish_reason`) n'est pas nominal (`stop`) est signalée comme incomplète et n'est pas intégrée à la session.
   - L'utilisateur est averti que chaque requête transmise peut engendrer des coûts selon la tarification propre au fournisseur.

### Statut d'implémentation
- **Adaptateur OpenAI (`OpenAIRuntime`)** : implémenté et testé avec des simulateurs HTTP locaux respectant le protocole Chat Completions officiel. Aucun appel distant réel payant n'a été exécuté dans le cadre des tests standard.
- **Autres fournisseurs (Anthropic, Gemini, Mistral, etc.)** : non implémentés à ce jour ; envisagés dans les évolutions futures.

---

## 6. Gestion du budget de contexte et isolation des sessions

Ces contrôles de contexte et d'historique concernent le dialogue local. Le parcours distant envoie une question confirmée sans historique ni contexte technique automatique ; l'architecture B reste à qualifier :

- **Budget de contexte borné (`--context-budget`)** : fixé par défaut à 16 000 octets (réglable entre 1 024 et 128 000 octets). Si la taille des messages dépasse cette limite, la requête est refusée **sans troncature silencieuse**.
- **Sélection explicite du contexte (`/context`)** : les résultats d'analyses locales ne sont ajoutés aux échanges IA que si l'utilisateur en fait le choix explicite.
- **Réinitialisation complète (`/reset`)** : efface immédiatement l'historique conversationnel en mémoire vive.
