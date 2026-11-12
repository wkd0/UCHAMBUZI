# Validation du candidat à la première bêta

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Recette historique du prototype, antérieure à la publication 0.2.0-beta.1.
> Les exemples utilisent désormais les commandes officielles anglaises.

Recette du 7 novembre 2026 sur le code `d36bafe04fd25a98b7cf59a64608ec7e13cec53a`.
Le programme conserve la version `0.2.0-prototype` : aucune publication ni
validation définitive des contrats n'est impliquée.

## Livraisons assemblées

Base intégrée : `00e0ec96d45c07c62b9d7a52cdce860c3a1269d1`.

- Fiabilité terminal et conversation : `7a70066477f380d8d303f1032e9df484b3339255`, adapté aux parcours déjà
  intégrés ; la provenance est conservée dans le message du commit d'intégration.
- Détection d'indices et inventaire : `961cdecfaddf71d11eb4dd365d84e5c35da734b6`, repris avec `cherry-pick -x`.
- Documentation et catalogue Kali : `3a602379b1f562bb478266a782755403c9a7b38f`, repris avec `cherry-pick -x`.
- Préparation de commandes et intégration : règles de version dig exactes, distribution de la nouvelle note,
  délai configurable et tests transversaux dans le commit testé.

Les chevauchements avec la CLI et PROTOTYPE.md ont été résolus par
adaptation explicite. Aucun conflit Git ne reste ouvert.

## Vérifications effectuées

| Suite | Tests réussis sur Ubuntu | Tests réussis sur Kali |
| --- | ---: | ---: |
| Commandes et contrats | 25 | 25 |
| Conversation | 17 | 17 |
| Documentation et raccordement Kali | 50 | 50 |
| Indices et inventaire | 21 | 21 |
| Installation | 9 | 9 |
| Parcours terminal | 15 | 15 |
| Prototype | 4 | 4 |
| Nouvelles régressions transversales | 7 | 7 |
| Total | **148** | **148** |

Aucun échec ni test ignoré sur les passes finales : 6,562 s sur Ubuntu,
8,170 s sur Kali 2025.3 / Python 3.13.7. Compilation Python, syntaxe Shell et
contrôle des espaces Git réussis. Le premier passage intermédiaire comportait
3 échecs, 1 erreur et 1 test ignoré : attentes anciennes sur le contexte automatique,
le format JSON, la note documentaire et une fixture d'analyse incomplète ; ces
attentes ont été corrigées et les trois tests de raccordement documentaire Kali
s'exécutent désormais sur les modules présents. Les journaux intermédiaires sont
conservés dans les preuves locales. Un premier transfert SSH incomplet a aussi
empêché la découverte des tests sur Kali ; le transfert par fichier vérifié par
SHA-256 a permis la passe complète ci-dessus.

Le lancement par `uchambuzi`, hors du dépôt source dans un HOME de recette, a été
vérifié. Installation, réinstallation et retrait dans un second HOME temporaire
réussissent, avec préservation d'un fichier utilisateur. Le manifeste distribue
sept modules et cinq ressources, dont `data/documentation/dig-kali.md` et
`data/commands/syntax.md`. La migration d'un manifeste v2 à onze fichiers est
couverte ; une nouvelle ressource déjà présente mais non gérée provoque un refus.

L'inventaire réel retourne ExifTool **13.25**, `file-5.46` et
`DiG 9.20.11-4+b1-Debian`. Le parcours URL/e-mail exige la sélection du domaine
extrait. La préparation DNS utilise la référence Kali et sa provenance exacte ;
versions inconnues et périmètre non confirmé restent refusés. **Aucune requête DNS
ni commande préparée n'a été exécutée.** Les cinq types d'indices, les sources,
les limites, les refus et la sortie du terminal ont été exercés.

## Conversation réelle et temps observés

Ollama **0.40.15**, **qwen2.5:3b**, Q4_K_M, 4 vCPU, 7 938 Mio de RAM.
Fenêtre configurée à 4 096 tokens. Quatre réponses réelles à travers le lanceur
installé, avec instrumentation des requêtes HTTP et des processus du runtime :

| Cas | Durée totale | Tokens d'entrée | Tokens produits | Génération |
| --- | ---: | ---: | ---: | ---: |
| Question SHA-256 sans contexte technique | 41,54 s | 391 | 91 | 4,59 tokens/s |
| Question après `/analyze` puis `/context` | 208,86 s | 3 400 | 59 | 1,65 tokens/s |
| Relance avec historique, contexte non dupliqué | 19,75 s | 3 481 | 12 | 1,72 tokens/s |
| Question après `/context off` puis `/reset` | 7,16 s | 382 | 23 | 5,73 tokens/s |

Somme de RSS serveur et runner : maximum observé **2,254 Gio** ; CPU moyen par
requête **380 à 394 %**, sur une échelle où un cœur vaut 100 %. Ces mesures
incluent l'instrumentation ; la somme des RSS n'est pas une mémoire unique exacte.
Chargement rapporté par la première réponse : 2,109 s, avec caches système déjà
chauds ; ce n'est pas une mesure à froid.

Le délai de 300 s par défaut a permis la réponse de 208,86 s. `--timeout` accepte
une valeur finie strictement positive, au maximum 600 s. Un serveur HTTP simulé
envoyant lentement ses en-têtes vérifie que la borne porte sur la requête entière,
pas seulement sur chaque lecture. Un dépassement conserve l'historique antérieur,
n'ajoute pas le tour échoué et ne provoque aucune relance automatique. Le terminal
affiche l'attente, la durée d'une réponse réussie et une erreur explicite.

Le contexte complet sélectionné est sérialisé sans suppression de source ou de
limite et n'est pas recopié lorsqu'il figure déjà dans l'historique. Sur la relance
réelle, la requête représente **13 498 octets**, contre **24 920** si le même
contexte était ajouté une seconde fois : réduction de **45,8 %**. Cette comparaison
porte sur les données sérialisées ; la variante dupliquée n'a pas été soumise au
modèle. **Aucun gain général de vitesse n'est démontré.** Les essais antérieurs
et actuels n'ont pas les mêmes prompts, historiques et conditions de cache ;
les débits actuels sont inférieurs à ceux des anciennes questions courtes.

Les traces confirment le rôle utilisateur du contexte, sa conservation lors de
la relance, puis son absence après `/reset`. `/context off` a été actionné avant
ce reset ; le détail de son comportement lors d'un message suivant est couvert
par les tests automatisés. Aucune troncature n'est signalée par le runner pendant
ces quatre échanges. Une conversation plus longue peut dépasser sa fenêtre :
l'application conserve l'historique, mais le runtime peut le tronquer.

## Qualité et limites de la recette

Les quatre requêtes ont abouti, avec étiquette « réponse du modèle (non vérifiée) ».
Le modèle a répondu correctement sur l'impossibilité de retrouver les différences
à partir de SHA-256, a proposé dig, a déclaré n'avoir exécuté aucune commande et
n'a pas reconstitué le domaine effacé par `/reset`.

La qualité reste insuffisante pour valider une fiabilité générale : la réponse
sur dig confond certaines limites de la validation syntaxique avec les capacités
de l'outil, et les deux premières réponses dépassent les deux phrases demandées.
La grille conversationnelle complète, ses répétitions et les injections hostiles
contre le modèle réel n'ont pas été rejouées dans cette recette ciblée. Les tests
simulés de neutralisation ne prouvent pas la résistance du modèle à une injection.

Serveur et client ont tourné ensemble dans un espace réseau ne contenant que
loopback ; une tentative de connexion à une adresse réservée échoue avec réseau
inaccessible. L'écoute est `127.0.0.1:11434`, le serveur annonce le cloud désactivé.
L'audit Python du client observe cinq connexions à cette adresse et aucun lancement
de processus. Ce n'est pas une trace exhaustive des appels système du serveur ;
l'isolation réseau fournit la preuve d'absence d'accès Internet pendant l'essai.
Aucun modèle ni paquet supplémentaire n'a été téléchargé.

## Conditions pour la suite

Le candidat est prêt pour une validation humaine de la bêta et de l'installation
utilisateur. Une publication ou une qualification comme assistant fiable en
investigation reste prématurée : latence CPU importante, imprécisions des réponses,
fenêtre de contexte finie et couverture qualitative réelle limitée.

L'installation dans le HOME habituel demeure non exécutée et attend une
autorisation distincte. Les environnements temporaires et les preuves sont
conservés. Les contrats restent expérimentaux ; aucune fusion vers dev, publication
ou synchronisation distante n'a été réalisée.
