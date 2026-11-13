# Changelog

## 2.0.0 — 13 novembre 2026 (candidate privée)

Cette candidate n'est pas encore publiée sur le dépôt de distribution.

### Compatibilité

- **Rupture de garantie** : retrait du chaînage et du scellement SHA-256 des dossiers,
  journaux, captures shell et conversations. Le journal reste en clair, horodaté UTC.
  Les contrôles de structure, de fermeture et de révision concurrente restent actifs ;
  ils ne détectent pas une modification arbitraire du contenu.
- Les anciens dossiers restent lisibles. Une écriture avec cette version ne produit
  plus d'empreinte de dossier valide pour la 1.0.0 : le retour à cette version exige
  une sauvegarde antérieure complète. Ne pas partager un dossier entre les versions.
- Le format de dossier reste `schema_version: 1`. `CaseManager.status()` expose
  `structure` et `revision` ; il retire `sha256`, `journal_head_sha256`,
  `sealed_journal_sha256`, `integrity`, `integrity_scope` et `integrity_limitations`.
  Le format des conversations passe à la version 2 et accepte la lecture de la version 1.
- Les anciennes métadonnées de traçabilité peuvent rester dans les dossiers historiques ;
  leur retrait explicite est distinct de l'ouverture. Aucune migration automatique
  des dossiers utilisateur n'est exécutée lors de la préparation de cette candidate.
- Les hashes fournis comme indices et la vérification des paquets et outils tiers
  restent préservés.

### Évolutions et corrections

- Holehe : conserver les résultats consultables mais exclure ses sorties des pivots automatiques.

- Résultats, rapports et états documentaires présentés en français lisible,
  sans codes internes ni empreintes de traçabilité imposées.

- Outils : retirer Waybackurls du catalogue, de l’aide et des recommandations faute de licence identifiée ; conserver les archives avec gau puis curl (deux étapes).
- Outils : ajouter les copies figées Subfinder, HTTPX, DNSX, Photon, TruffleHog et Gitleaks, installables hors ligne.
- Social Analyzer : charger les données avant `--list`, avec un bundle révisé ; détecter les prérequis Amass v5 et documenter sa lecture SQLite locale.
- Découverte : résoudre les outils Kali dans le chemin système et les copies embarquées par leur manifeste vérifié, y compris pour l’aide documentaire.
- Scénarios : préparer la cible encodée de l’API Wayback sans interrompre le parcours `archives` après les premières étapes.
- Dialogue OSINT : état local des outils pertinents affiché séparément de l’IA ; les recherches ne sont proposées au modèle comme préparables qu’avec une copie vérifiée ou un chemin système présent.
- Interface : bordures du panneau `/investigation status` conservées lors de l’affichage et des redimensionnements du terminal.
- Holehe : corriger le plantage au chargement du module Facebook en retirant un import inutilisé ; bundle hors ligne reconstruit et révision distincte `1.61-14da70f-r1`.
- Catalogue OSINT : niveau d’intégration distinct de l’installation, avec les raccourcis et scénarios réellement disponibles pour chaque outil.
- Aide documentaire des 22 outils Kali accessible depuis les fiches et le dialogue IA ; source et troncature explicites, chargement de l’aide sans bloquer l’interface.

## 1.0.0 — 12 novembre 2026

Première version publique CLI pour Kali Linux amd64. Paquet :
`uchambuzi_1.0.0-1_amd64.deb`.

- Profils de fournisseurs IA nommés, avec accès distincts, clés facultativement sauvegardées en fichier privé non chiffré et recherche approuvée des modèles Responses.
- Kit graphique complété : variantes SVG, icônes PNG et ressources favicon ; anciennes notes de bêta retirées.

- Délais IA gérés automatiquement par fournisseur ; le délai ne figure plus dans les réglages courants.

- Reprise explicite de conversations associées à une enquête vérifiée, sans restauration des autorisations.
- Brouillons et positions de curseur conservés pendant la navigation dans l'historique.
- Résultats d'outils numérotés, consultables par `/details N` et recherchables par `/details search texte`.
- Conseils de saisie contextuels activables dans `/tips` ; `/copy commande` copie la dernière commande proposée.
- Les sorties en arrière-plan respectent la position de lecture et le brouillon en cours.
- Catalogue `/tools` interactif par objectif, avec fiches expliquant rôle, intérêt, indice, résultats et limites des 36 entrées.
- Préparation individuelle des six outils embarqués avec approbation, dossier de travail et contexte IA borné ; PhoneInfoga en analyse locale seulement.
- Préparation du shell avec le chemin d’exécution vérifié, aide locale et maintenance des copies depuis la fiche.

- Dès la frappe de `!`, le prompt passe en Shell mode avec préfixe, fond et aide dédiés ; Échap revient au dialogue. Collage et historique conservent ce comportement.
- `/stop` retiré du menu et de l’aide ; interruption directe avec Échap ou Ctrl+C.

- Gestion des dossiers unifiée sous `/investigation` : create, open, list, status, rename, close, archive et delete. Les anciens noms restent des alias de compatibilité.
- Commandes d’enquête absentes d’Assist et bloquées avant l’ouverture d’un sélecteur.
- Shell Bash libre avec `! commande` et `/terminal`, approbation explicite, terminal interactif et capture horodatée SHA-256 dans le dossier actif.
- Sortie du shell associée au prochain dialogue IA avec isolation des données externes.
- Sélection des réponses Markdown et sorties Rich, Ctrl+C pour copier une sélection, F6 ou `/copy` pour copier la dernière réponse ; presse-papiers OSC 52 et intégration X11/Wayland si disponible.
- Aide du catalogue enrichie avec les opérations de préparation et d’installation des copies vérifiées.
- RedSage local proposé par défaut ; les modèles déjà choisis restent configurables.
- Consignes communes renforcées sur les hypothèses et les limites des indices et des sources.
- Calibration du dialogue Assist et OSINT : priorité aux faits disponibles, préservation des preuves et réponses adaptées à la demande ; recette synthétique reproductible sur Kali.
- Une demande explicite de caractéristiques locales peut transmettre au modèle Ollama local un inventaire minimal de la machine exécutant UCHAMBUZI.
- Profils de consignes expérimentaux sélectionnés automatiquement par famille et modèle, avec modèle libre et repli familial ou neutre.
- Connexions facultatives OpenAI/Grok Responses et Claude Code, clé en variable d'environnement et aperçu soumis à approbation pour chaque envoi distant.

- Installation hors ligne des bundles corrigée sur Kali avec Python 3.14 par défaut : sélection de Python 3.13 et dépendances Debian explicites.
- Blackbird reçoit `--username` et travaille hors de sa copie vérifiée pour préserver son intégrité après exécution.
- Social Analyzer raccordé à `/pseudo` et au playbook de pseudonymes ; Holehe réservé au parcours email.
- Playbooks Textual et transformation `/target` exécutés dans un worker pour recueillir les confirmations interactives.
- PhoneInfoga 2.11.0 utilise les options réellement disponibles et désactive les scanners à clé ; génération locale de liens distinguée d’une recherche vérifiée.
- Documentation courante révisée, historique identifié, 134 wheels inventoriés, sources PhoneInfoga 2.11.0 conservées.
- Qualification détaillée dans la [note V1](docs/releases/1.0.0.md).
