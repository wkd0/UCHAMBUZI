# Candidat cycle 4 — résultats d'intégration

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Recette historique du prototype, antérieure à la publication 0.2.0-beta.1.
> Les exemples utilisent désormais les commandes officielles anglaises.

Recette des 7–8 novembre 2026 ; code testé :
`4eedcd96d0dabafeab85e7071282815b101c9c2d`.
Le candidat reste `0.2.0-prototype`, sans publication ni acceptation générale
comme assistant fiable pour une investigation.

## Livraisons et raccordements

La base `a8f56f7` contient déjà les livraisons initiales annoncées. Aucun changement
n'a été appliqué deux fois. Évolutions intégrées pendant ce cycle :

| Chantier / Composant | Commit source | Intégration locale |
| --- | --- | --- |
| Fiabilité et contexte | `7f414d8b20c430738f54ed8c2c62c53bc93e7efe` | adaptation dans `b017b9d`, déduplication existante conservée |
| Multi-IA et adaptateur distant | `349dc1f768b142f02dc266206e50364d8f889eec` | adaptation dans `b017b9d` |
| Reconnaissance et inventaire | `1df23c59fd9ab821dfba77309b964841e70ffb80` | cherry-pick `5686e14` |
| Sonde ExifTool | `bca5d696d30ce84a3e6739d55adef2c63ebd398b` | adaptation `d508331` |
| Sept outils documentés | `411fe8aef00700e2d59398b272fd927f2b24665c` | adaptation dans `b017b9d`, références dig Kali préservées |
| Dates et sélection multiple | règles et tests d'intégration | `4eedcd9` |

Les chevauchements avec le terminal, le catalogue et les assertions de préparation
ont été examinés avant application. Aucun conflit Git non résolu.

Les huit échecs historiques signalés provenaient de l'hypothèse de recommandation
unique. Les tests choisissent maintenant l'outil par son identifiant. Le terminal
présente les propositions numérotées et exige un choix ; aucun outil n'est choisi
par défaut. Les nouveaux tests vérifient plusieurs recommandations réelles pour
un fichier, leurs identifiants distincts, leurs références, l'ordre d'inventaire
inversé, les sélections invalides et les paramètres croisés ExifTool/strings.
Une préparation rafraîchit l'inventaire et la recommandation de l'outil choisi ;
elle conserve les propositions initiales et retourne l'identifiant de la nouvelle
recommandation utilisée. Les paramètres ne passent pas d'un outil à un autre.

## Commandes et documentation

| Outil | Version exacte supplémentaire | Opération |
| --- | --- | --- |
| ExifTool | `13.25` | `read_metadata`, paramètres vides, `-config '' -j -G1 -s -- CHEMIN_ABSOLU` |
| GNU strings | `GNU strings (GNU Binutils for Debian) 2.45` | `extract_strings`, `min_length` entier 4 à 64, `-a -n N -e s CHEMIN_ABSOLU` |

Versions et manuels vérifiés sur Kali. Les deux préparations sont passées par le
terminal installé, avec sélection explicite et racine déclarée. Les opérations
file et dig restent disponibles, notamment le bandeau exact
`DiG 9.20.11-4+b1-Debian`. Les versions inconnues restent refusées, même si un
numéro de version partiel figure ailleurs dans l'inventaire.

La documentation couvre file, dig, ExifTool, strings, whois, TShark et curl.
Les trois derniers restent informatifs, sans règle de préparation. Un refus est
présenté immédiatement lorsqu'ils sont sélectionnés pour une préparation.
Aucune recommandation ni revue documentaire ne vaut autorisation d'exécution.
Les options autorisées et limites sont dans
[exiftool-strings-operations.md](exiftool-strings-operations.md).

## Installation et paquet

Migration réelle d'une installation utilisateur à douze fichiers vers dix-sept,
réinstallation, lancement par `uchambuzi` hors du dépôt, diagnostic des ressources,
et retrait dans un autre HOME temporaire : réussis. Les notes personnelles sont
conservées. Sept modules et dix ressources sont distribués ; l'installation reste
sans dépendance Python externe ni accès Internet obligatoire. Le runtime et le
modèle déjà installés restent des prérequis distincts.

Deux constructions indépendantes de l'archive avec `git archive` et `gzip -n`
produisent les mêmes octets. Paquet du code recetté :
`uchambuzi-cycle4-4eedcd9.tar.gz` ; SHA-256 :
`1f1d7ceea36d16b8ff7ac4c2d138de1ccf3daaf27a13e96a5d940839104f538f`.
Les documents internes, clés, modèles et preuves de recette sont exclus.
Aucune installation dans le HOME habituel n'a été effectuée.

## Tests et anomalie corrigée

**202 tests réussis sur Ubuntu, 202 sur Kali 2025.3 / Python 3.13.7** ; aucun échec
ni test ignoré dans les passes finales. Durées : 6,396 s et 5,947 s. Compilation,
syntaxe Shell et contrôles Git réussis.

| Domaine | Tests |
| --- | ---: |
| Commandes, contrats, lectures locales | 33 |
| Conversation et fournisseurs | 25 |
| Multi-IA et limites de contexte | 13 |
| Documentation, dates et raccordements | 67 |
| Indices/inventaire | 29 |
| Installation | 9 |
| Parcours, prototype et régressions bêta | 26 |
| Total | 202 |

Le premier passage intermédiaire avait deux échecs et une erreur : fixtures
sans statut de fin d'inférence, et tests d'historique dépassant le nouveau budget.
Les fixtures ont été rendues explicites et les tests du budget ajoutés. Les
journaux intermédiaires sont conservés, sans suppression d'un test en échec.

Un premier essai réel sur Kali a refusé les nouvelles fiches, correctement selon
leur date apparente : le système était encore au 7 novembre en EST alors que
les consultations étaient datées du 8 novembre en Europe/Zurich. Le catalogue
déclare maintenant ce fuseau, affiché avec les références. Les sources futures,
périmées ou de fuseau invalide restent refusées. Aucun réglage de l'horloge système,
aucune tolérance arbitraire et aucune date variable dans l'identité de la fiche.
La recette corrigée a été exécutée dans un nouveau répertoire ; l'essai refusé
et les anciennes installations de recette sont conservés.

## Dialogue local et multi-IA

Ollama 0.40.15, qwen2.5:3b Q4_K_M, 4 vCPU, 7 938 Mio, fenêtre runtime de
4 096 tokens. Deux réponses réelles via le lanceur installé, client et serveur
isolés dans un espace réseau ne contenant que loopback, cloud désactivé.
Écoute : `127.0.0.1:11434`. Aucune troncature signalée pendant ces échanges.

| Cas | Durée | Tokens d'entrée | Tokens produits | Génération |
| --- | ---: | ---: | ---: | ---: |
| Question documentaire après `/context 1` | 87,77 s | 2 154 | 55 | 3,47 tokens/s |
| Relance avec historique | 10,02 s | 2 232 | 14 | 3,40 tokens/s |

CPU moyen : 392–396 % (100 % par cœur) ; maximum de RSS additionnés serveur et
runner : 2,132 Gio, sans prétendre mesurer la mémoire unique. Chargement rapporté
initial : 1,302 s, caches déjà chauds. Instrumentation incluse.

L'analyse entière de 28 065 octets a été refusée avant envoi avec le budget par
défaut de 16 000. `/context 1` a ramené les messages à 8 463 octets, soit 69,85 %
de moins, en conservant intégralement la recommandation choisie, ses références,
limites et réserves. Les autres outils restent consultables dans le terminal.
La requête HTTP complète représente 8 517 octets, enveloppe comprise.

Les 87,77 s sont inférieurs aux 208,86 s observées au cycle précédent, avec
2 154 tokens d'entrée contre 3 400. Ce n'est pas une comparaison contrôlée à
instructions, corpus, cache et charge identiques ; aucun gain général garanti.
La réponse reconnaît dig et la relance déclare n'avoir exécuté aucune commande.
Elle reste imprécise en attribuant à des résultats DNS une limite de validation
syntaxique : la qualité technique n'est pas résolue par le nouveau profil système.

Le délai configurable de 300 s, borné à 600, est conservé. L'attente est visible ;
interruptions, budgets dépassés et réponses partielles sont explicites. Un tour
incomplet n'est pas ajouté à l'historique. Aucun réessai automatique. Le budget en
octets n'est pas une garantie de respect de la fenêtre en tokens du modèle.

Le gestionnaire multi-IA est intégré : local initial, configuration en mémoire,
choix distant manuel, aperçu, remplacement/annulation et consentement par
requête. L'annulation distante puis le retour local ont été exercés sur Kali.
Les tests d'API utilisent uniquement des serveurs ou transports simulés : aucun
appel payant, aucune clé réelle, aucune qualification des modèles distants.
Les refus du moteur de commandes restent indépendants et ne sont jamais envoyés
silencieusement à un fournisseur. Voir [multi-ia.md](multi-ia.md).

## Portée et suite

La recette du terminal déterministe observe 21 sondes fixes de version, dont
`exiftool -config '' -ver`, et aucune connexion Python. La préparation directe
est testée avec processus et sockets interdits. Pendant les deux conversations,
l'audit du client observe uniquement trois connexions loopback (liste et deux
réponses), sans processus lancé. Ce n'est pas une trace exhaustive des syscalls
internes des binaires ; l'isolation réseau de l'essai IA est vérifiée séparément.
Aucune commande préparée, requête DNS ou analyse de fichier n'a été exécutée.

Le candidat est prêt pour une revue humaine et une installation utilisateur
autorisée séparément. Restent à valider : qualité technique du modèle, grille
conversationnelle complète, usage avec longs historiques, contrats définitifs
et, si souhaité, véritable recette d'API avec autorisation spécifique. Une clé
masquée à l'affichage n'est pas un détecteur de tous les secrets. Les dates du
corpus requièrent la base de fuseaux système ; si elle manque, la lecture refuse.
Aucune fusion vers dev, aucun push ni aucune publication n'ont été effectués.
