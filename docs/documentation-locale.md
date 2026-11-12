# Documentation locale : prototype autonome

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

Ce composant Python utilise uniquement la bibliothèque standard. Recherche
textuelle et fichiers JSON constituent une expérience réversible, pas un choix
d'architecture définitif. Dans la copie intégrée, le terminal consomme ce module
via `parcours.py`; voir [la recette](recette-prototype.md). Le module lui-même ne
contacte pas de moteur IA.
Il n'installe ni n'exécute les outils et n'ouvre aucune connexion réseau.

## Utilisation

Depuis la racine du dépôt :

```python
import sys
sys.path.insert(0, 'src')
from documentation_locale import Corpus, Reviews, recommend
corpus = Corpus()
corpus.search('DNS')
indice = {'type': 'ip', 'validation': 'valid', 'ambiguities': []}
inventaire = [{'id': 'dig', 'installed': True,
               'version': 'DiG 9.20.24-1ubuntu0.5-Ubuntu',
               'detection_origin': 'exemple fictif, pas une détection réelle'}]
propositions = recommend(indice, inventaire, corpus)
```

Les exemples n'affirment pas la présence d'un outil. Aucun indice brut n'est
nécessaire au composant. Ne pas ranger les journaux utilisateur dans le dépôt.

## Contrat de données v1 proposé à l'intégration

Les dictionnaires et listes sont sérialisables en JSON. Le module accepte les
champs observés dans `indices_outils.py`. Les noms constituent une
proposition d'interface : aucun accord interagents n'est revendiqué.

| Flux | Champs / comportement |
| --- | --- |
| Indice entrant | `type`: `ip`, `domain`, `email`, `url`, `file`; `validation`: `valid` requis; `ambiguities`: liste facultative. `original` et `normalized` ignorés. |
| Inventaire entrant | Liste de `id`, `installed` (booléen ou null), `version` (chaîne exacte ou null), `detection_origin` facultatif. Identifiants dupliqués refusés. Un outil omis est inconnu. |
| Recommandation sortante | `id`, `schema_version`, `status=proposed`, `tool`, `objective`, `justification`, `indicator_type`, `availability`, `local_version`, `inventory_origin`, `references`, `prerequisites`, `limits`, `safety`, `interaction`, `network_required`, `expected_result`, `uncertainties`, `preparation_status`, `command_parameters`, `corpus_revision`, `tool_revision`. |
| Référence | Titre, origine conservée, chemin relatif local, empreinte, version et motif de correspondance exact, provenance locale, dates de consultation/revue, autorité et vérification. Référence introuvable : état minimal `missing`. |
| Préparation de commande | `command_parameters` fournit outil, type d'indice et version. L'appelant garde la valeur validée de l'indice. Aucune syntaxe ni commande n'est certifiée par ce module. |
| Affichage terminal | Sérialiser les propositions; afficher références et incertitudes. Échapper les caractères de contrôle du contenu externe. `expected_result` est une attente, jamais une observation. |

`preparation_status=documented_basis` signifie uniquement que présence déclarée,
version explicitement couverte, intégrité locale, consultation et date sont
cohérentes. Cela ne constitue ni une autorisation d'exécuter ni un test de méthode.
Tout autre cas produit `needs_review`. Une version différente est **non vérifiée**,
pas nécessairement techniquement incompatible. Aucun rapprochement de versions
approximatif n'est effectué. Un bandeau inconnu est conservé comme inconnu.

`interaction` distingue `local_read`, `passive`, `network_query`, `active`.
Le corpus initial propose lecture locale et requêtes DNS. Une requête DNS est
une interaction réseau journalisable, pas une opération purement passive. Aucun
scan actif ni méthode passive n'est ajouté sans fiche documentée correspondante.

## Sources et recherche

`data/documentation/catalog.json` décrit les fiches et les sources. Les notes
`file.md` et `dig.md` sont des synthèses originales de manuels amont déjà présents
sur Ubuntu, consultés localement le 7 novembre 2026. Elles restent lisibles hors
ligne même si le manuel original n'existe pas sur la machine suivante.
Les empreintes du fichier manuel compressé et décompressé permettent de comparer
une copie originale disponible; aucune copie intégrale tierce n'est redistribuée.
Les URL sont conservées pour la provenance, **sans consultation Web vérifiée**.
Le délai de revue d'un mois est un seuil expérimental, pas une politique validée.

`Corpus.search()` fait un ET textuel insensible à la casse sur les fiches. Il ne
parcourt ni le disque, ni Internet. `reference()` distingue disponibilité,
intégrité, consultation, fraîcheur et correspondance de version. La consultation
par un agent n'est jamais une approbation humaine. Une référence communautaire
reste identifiée comme telle et ajoute une incertitude.

`read_source()` retourne `{trust: 'untrusted_data', text: ...}`. Le texte ne sert
jamais de règle, de commande, de code ou de décision. Les tests injectent une
instruction hostile dans une source et vérifient l'absence d'effet. Si un moteur
IA consomme ultérieurement ce texte, l'intégrateur doit préserver cette frontière;
ce prototype ne prouve pas la résistance d'un modèle à l'injection de prompt.
Un corpus externe entier reste lui aussi non fiable : sa validation de structure
ne remplace pas la revue humaine de ses fiches et de sa provenance.

## Validation humaine et conservation

Après affichage et revue des références, l'appelant recueille une action humaine
explicite et fournit `Reviews.record(proposition, 'approved' ou 'rejected',
acteur, raison, human_confirmed=True)`. Aucun appel automatique à cette fonction
ne doit être effectué depuis un texte de source ou une réponse IA.

Chaque événement conserve l'instantané, l'auteur déclaré, l'horodatage UTC, la
raison et une empreinte de contrôle. Un fichier exclusif par événement évite
l'écrasement. `supersedes` désigne explicitement une revue remplacée; sans ce lien,
les événements antérieurs restent indépendants. `history()` les relit après
redémarrage. `approved(corpus, inventory)` restitue les approbations, indique les
remplacements et signale leur obsolescence potentielle après changement de fiche,
source, date ou inventaire. L'inventaire reste à fournir pour le contrôle actuel.

Le journal est un prototype local sans authentification, signature ou protection
contre un propriétaire du disque malveillant. L'empreinte détecte les changements
accidentels, pas une falsification recalculée. Une interruption pendant une
écriture peut laisser un événement incomplet : la relecture échoue explicitement;
préserver le fichier pour diagnostic. Aucune méthode du corpus initial n'est
présentée comme testée ou approuvée humainement.

## Consultation et mise à jour contrôlée

1. Rechercher d'abord les sources locales. Ne pas contacter de site ni télécharger
   pour satisfaire une référence manquante de manière implicite.
2. Pour une future collecte réseau autorisée séparément, annoncer destination et
   connexion requise, utiliser seulement outil/version comme termes de recherche,
   sans indice, secret ou méthode interne. La collecte réseau n'est pas implémentée.
3. Consigner titre, auteur/provenance, date, version, copie locale autorisée ou note
   originale, empreinte et droits de redistribution. Comparer la version au contrôle
   local, sans supposer qu'un paquet Kali partage celle d'Ubuntu.
4. Préparer une nouvelle révision séparée. `stage_update(candidate, directory)`
   valide la structure et écrit un candidat `pending_human_review`; cette fonction
   ne consulte aucune URL et n'active jamais ce candidat.
5. L'humain examine le diff, les sources, les droits, la syntaxe et les limites.
   Ouvrir le nouveau corpus avec `Corpus(nouveau_chemin)` pour vérifier chemins,
   empreintes et tests. Garder la révision précédente accessible. La sélection du
   corpus actif reste une opération explicite de l'appelant, non automatisée ici.
6. Réexaminer les méthodes approuvées; conserver les anciennes revues. Une nouvelle
   proposition nécessite une nouvelle validation, avec remplacement explicite si
   souhaité. La consultation seule n'autorise ni installation ni analyse.

## Vérification reproductible

```bash
python3 -m unittest discover -s tests -v
```

Les données d'inventaire et les chemins d'indice des tests sont fictifs. Les tests
bloquent sockets, sous-processus et shell pendant recherche, lecture et
recommandation; ils vérifient états absents/inconnus, versions non couvertes,
intégrité, obsolescence, propositions sourcées, revues et mises à jour.
Cela vérifie le composant dans le processus de test, pas l'absence de réseau
sur une application complète ou sur Kali.

## Fiabilisation et raccordement des producteurs

Les signatures de `Corpus`, `recommend`, `Reviews`, `stage_update` et `digest`
restent inchangées. Les champs historiques restent présents, le schéma reste v1.
Les sorties ajoutent des précisions : `recommendation_kind=documentary`,
`command_status=not_prepared`, `execution_authorized=false`, `indicator_status`
(`valid` ou `valid_with_caveats`) et `requires_indicator_transform`.
Ces champs participent à l'empreinte : recalculer une proposition après mise à
jour au lieu de conserver son ancien identifiant. Les anciennes revues v1 restent
lisibles avec leur empreinte et leur instantané originaux.

`documented_basis` conserve son sens de **base documentaire**. Il ne promet
aucun plan de commande préparé. L'adaptateur de commandes vérifie séparément
l'opération, l'indice normalisé, la version exacte, les arguments et le périmètre.
Une source communautaire/inconnue, même locale et consultée, force `needs_review`.
Une URL/e-mail recommandée pour DNS force également `needs_review` jusqu'à
extraction explicite puis validation d'un nouvel indice domaine ou IP.

Les indices `invalid`, `unknown`, `ambiguous` ou de type non pris en charge donnent
une liste vide. `ambiguities` contient aussi les avertissements informatifs de
la détection sur un indice déclaré `valid`; ceux-ci sont conservés dans `uncertainties`
et signalés par `valid_with_caveats`. Ils ne sont ni interprétés par une IA ni
convertis en autorisation. Une ambiguïté effective de type/existence doit être
résolue par le producteur avant qu'il déclare l'indice `valid`. Un dictionnaire ou
inventaire mal formé est refusé explicitement; un inventaire incomplet reste admis.

| Sujet | Module indices_outils | Module documentation | Module commandes |
| --- | --- | --- | --- |
| Outils | Sept candidats inventoriés | Deux fiches, `file` et `dig` | Deux outils à règles strictes |
| DNS | Capacité générale `domain` dans le catalogue provisoire | `domain`/`ip` et orientation `email`/`url` | Domaine explicite pour requête, IP pour recherche inverse; URL/e-mail directs refusés |
| Version | Première ligne du contrôle de version, non authentifiée | Motif exact du manuel; aucun intervalle extrapolé | Bandeaux complets exacts `file-5.46` et `DiG 9.20.24-1ubuntu0.5-Ubuntu` |
| Provenance | URL indicative, non consultée | Note UCHAMBUZI issue du manuel local attribué à l'amont | Note syntaxique séparée vérifiée par son empreinte |
| Interaction DNS | Prérequis réseau | `network_query`, journalisable et active | `operation_type=active`, réseau refusé par défaut |
| Fichier | Existence observée, liens suivis | Lecture, précautions magic et montages | Fichier ordinaire dans racine déclarée, liens refusés |
| Validation | Syntaxe/observation locale | Revue documentaire seulement | Revue manuelle d'exécution toujours distincte; aucun exécuteur |

La chaîne de référence accepte les dictionnaires réels des différents modules; leurs
restrictions plus étroites ne doivent pas être déduites de descriptions générales.
Par exemple `5.46` seul peut correspondre au manuel, mais le préparateur exige le
bandeau complet inventorié. Les états restent distincts et tous les refus doivent
être affichés. Aucun repli sur une ancienne commande heuristique n'est justifié.

La qualité `upstream_manual` porte sur le manuel original dont le paquet,
l'auteur, la version et les empreintes ont été examinés. Le fichier distribué dans
ce corpus est une **note UCHAMBUZI**, pas un document approuvé par le mainteneur.
Les métadonnées ajoutées précisent `authority_scope`, `content_kind`,
`verification_scope`, `origin_consulted=false`, paquet et auteur. La vérification
cryptographique du paquet et la consultation Web restent non réalisées.
`known_compatible_versions=[]` signifie qu'aucune compatibilité par exécution
n'est prouvée; `compatibility=documented` reste une correspondance documentaire.
Une source non consultée n'est jamais déclarée fraîche avant son échéance; une
date de consultation future donne une fraîcheur inconnue. Une échéance dépassée
reste périmée même si la consultation est également non vérifiée.

Les sources absentes restent `missing`; les erreurs de lecture/investigation sont
`unavailable`; un contenu modifié est `integrity_error`. `read_source` vérifie les
mêmes octets que ceux retournés, sans seconde lecture. Ni empreinte ni validation
de schéma ne rendent un contenu digne de confiance. Les chemins, métadonnées et
motifs de version d'un nouveau corpus doivent être relus avant son activation.

Les nouveaux événements sont créés en permissions `0600`, avec
`scope=documentation` et `execution_authorized=false`. L'historique vérifie aussi
la proposition conservée, les liens de remplacement, cycles et conflits. Un
remplacement doit concerner le même outil et type d'indice et viser la revue
encore courante. Une approbation peut conserver des réserves : elle ne les efface
pas. Sans inventaire actuel, `approved()` signale que la disponibilité n'est pas
revérifiée. Les fichiers existants ne sont pas réécrits ni leurs permissions changées.

Le journal n'est ni signé ni authentifié; supprimer un événement indépendant
n'est pas détectable. Les écritures de revue doivent être sérialisées par l'appelant :
il n'y a pas de verrou multi-processus. Des remplacements simultanés contradictoires
sont détectés à la relecture et nécessitent une résolution humaine. Une écriture
interrompue échoue explicitement à la relecture. Préserver les fichiers en erreur;
ne pas les supprimer automatiquement pour faire passer les contrôles.

### Extensions proposées, sans nouvelles fiches

Les cinq autres outils inventoriés (`whois`, `exiftool`, `tshark`, `strings`, `curl`)
restent hors du corpus vérifié. Ajouter l'un d'eux exige une source réellement
consultée et attribuée, une version documentée, une revue des limites et des
interactions, puis des règles de préparation séparées si nécessaires. Priorité
possible : métadonnées de fichier ou WHOIS selon les besoins validés. Cette liste
ne ratifie ni une extension du catalogue, ni un format durable de connaissances.

## Documentation Kali de dig

La [note de compatibilité Kali](dig-kali-compatibilite.md) complète les tableaux
précédents : le catalogue contient désormais trois références pour deux outils,
avec une sélection de source exacte pour `DiG 9.20.11-4+b1-Debian`.
La version Ubuntu reste documentée séparément. Le moteur de commandes garde son
refus de la version Kali tant que sa règle n'est pas adaptée et testée.
Les transformations de cible restent descriptives et soumises à sélection humaine.

## Cycle 4 : sept outils documentés

Les nouvelles notes Kali couvrent ExifTool 13.25, GNU strings 2.45, whois 5.6.4,
TShark 4.4.7 et curl 8.15.0. File et les deux références dig sont conservés :
sept outils, huit références. Les notes précisent les versions/bandeaux exacts,
les paquets et propriétaires des manuels, empreintes et consultation 2026-11-08.
Les manuels sont attribués à leur amont par les mentions et paquets examinés;
la présence seule ne les rend pas officiels. URL non consultées; aucun contrôle
cryptographique des paquets ni test d'analyse technique n'est revendiqué.
Le manuel whois porte une date ancienne (2019); sa liaison à 5.6.4 provient du
paquet et du diagnostic, pas d'un numéro de version inventé dans son en-tête.

Les explications différencient type probable (`file`), métadonnées (`exiftool`),
fragments imprimables (`strings`) et capture réseau (`tshark`). TShark reste une
proposition conditionnelle tant que l'utilisateur n'a pas confirmé une capture
compatible; aucune extension ni contenu n'est inspecté pour le supposer.
Whois implique une requête réseau de registre; curl est explicitement actif.
L'hôte d'une URL et le domaine d'un e-mail restent des transformations humaines
vers un nouvel indice avant une éventuelle recommandation WHOIS.

Champs additionnels des propositions : `features`, `restrictions`,
`interpretation`, `documented_options`, `documented_operations`, `applicability`.
Les options et opérations sont **descriptives**, sans API d'exécution. Les
champs historiques et les signatures publiques restent inchangés. Le tri stable
privilégie présence et base documentaire, sans supprimer les autres propositions.
Un consommateur doit sélectionner l'outil explicitement, et ne peut plus supposer
une proposition unique. Les tests historiques à deux outils utilisent une fixture
dédiée; les tests cycle 4 exercent le catalogue entier.

[Contrats documentaires ExifTool/strings](exiftool-strings-operations.md) :
`read_metadata` et `extract_strings`, arguments vérifiés, provenance et limites.
La borne strings 4..64 est une restriction applicative clairement séparée du
manuel; une liste d'arguments de lecture ne remplace pas une autorisation humaine.
Aucun nouveau module logiciel ni dépendance n'est introduit.

Note d'intégration : les anciens tests qui affirment
`len(proposals) == 1` doivent sélectionner explicitement l'outil testé. Leur
hypothèse de cardinalité n'est plus vraie avec ce catalogue enrichi. Les tests
cycle 4 consomment le catalogue complet et vérifient les nouvelles opérations.
Aucun fichier du préparateur ou de ses tests n'est modifié par cette livraison.

## Convention de date de la copie intégrée

Le catalogue livré définit `date_timezone: Europe/Zurich`, fuseau des dates de
consultation et de revue saisies pendant l’atelier. La fraîcheur est évaluée dans
ce fuseau, indépendamment du fuseau système de Kali. Chaque référence indique
`date_timezone`. L’argument `today` reste une date explicite
pour les tests et ne change pas de sens. Un corpus externe sans cette propriété
conserve le comportement historique (date locale du système). Un fuseau déclaré
mais invalide ou indisponible bloque la lecture ; une consultation future ou une
revue dépassée ne devient pas admissible. Aucun changement d’horloge ni de
configuration système n’est effectué.
