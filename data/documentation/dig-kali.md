# dig(1) — note locale Kali, 9.20.11-4+b1-Debian

Note originale UCHAMBUZI rédigée après lecture du manuel amont fourni par
`bind9-dnsutils 1:9.20.11-4+b1`, sur Kali GNU/Linux Rolling 2025.3.
Consultation : 2026-11-07, via SSH vers la VM locale; aucun accès Internet.
`dig -v` a retourné `DiG 9.20.11-4+b1-Debian` (diagnostic, aucune requête DNS).
`dpkg-query -S` attribue `/usr/share/man/man1/dig.1.gz` à `bind9-dnsutils`.
Le manuel annonce BIND 9, version `9.20.11-4+b1-Debian`, date `2025-07-04`.
Auteur : Internet Systems Consortium; copyright 2025 dans ce manuel.
Les métadonnées locales `/usr/share/doc/bind9-dnsutils/copyright` indiquent
BIND, Internet Systems Consortium et `https://ftp.isc.org/isc/bind9/` comme source.
Ces mentions attribuent le manuel à l'amont; elles ne prouvent pas la signature
cryptographique du paquet. La note UCHAMBUZI n'est pas approuvée par ISC.

SHA-256 du manuel compressé :
`faaf11b7648a35d0df5b2fb87d0e4c7889e6a1e25e70b2f6037a1020097815c4`.
SHA-256 décompressé :
`aa73b2dd16e0f0e0701645dd181729d320dffe6eee62281a1fafd85e4032236e`.
Origine Web conservée : https://bind9.readthedocs.io/en/latest/manpages.html
Cette URL n'a pas été consultée. Aucun téléchargement public ni installation.

## Sous-ensemble comparé avec Ubuntu

Comparaison directe des sections SYNOPSIS, DESCRIPTION, SIMPLE USAGE, OPTIONS,
QUERY OPTIONS et EXAMPLES avec le manuel Ubuntu `9.20.24-1ubuntu0.5-Ubuntu`, daté
`2026-06-08`. Les arguments ci-dessous sont documentés dans les deux copies.

| Élément | Sens commun lu dans les deux manuels | Restriction du préparateur examiné |
| --- | --- | --- |
| `@server` | Choix explicite du serveur, IPv4/IPv6 ou nom | IP littérale autorisée seulement; pas de résolution de nom du résolveur |
| `-r` | Ignore les options du fichier personnel `.digrc` | Toujours placé en premier |
| `-q name` | Distingue le nom à interroger des autres arguments | Domaine ASCII normalisé absolu, suffixé d'un point |
| `-t type` | Choisit le type; A par défaut sans recherche inverse | A, AAAA, MX et TXT seulement; choix explicite de l'utilisateur |
| `-x addr` | Recherche inverse IPv4/IPv6, classe IN et type PTR | IP explicite, sans zone, non multicast/non indéfinie |
| `+nosearch` | Désactive l'usage de la liste de suffixes | Présent dans les deux opérations |
| `+timeout=2` | Délai de requête en secondes; minimum 1, défaut 5 | Ne constitue pas un délai global de l'opération |
| `+tries=1` | Nombre d'essais UDP et TCP; défaut 3, minimum 1 | N'établit pas une garantie d'un seul paquet |

Modèles documentaires du préparateur examiné, **pas des commandes exécutées** :

```text
dns_query:   dig -r @RESOLVEUR_IP -q DOMAINE. -t TYPE +nosearch +timeout=2 +tries=1
dns_reverse: dig -r @RESOLVEUR_IP -x ADRESSE_IP +nosearch +timeout=2 +tries=1
```

Les sections `+tcp` et `+ignore` décrivent dans les deux versions une possibilité
de reprise TCP après troncature d'une réponse UDP. Un seul résolveur déclaré peut
récursivement joindre d'autres serveurs. La requête est active et journalisable.
Le résultat attendu reste une réponse DNS, une absence ou une erreur; aucun nom,
attribution, service ou résultat d'investigation n'est présumé.

Aucune différence de sens relevée pour ces arguments. Différences observées :
version/date/copyright des en-têtes, génération et balisage roff (italiques, liens
RFC). Cela n'établit ni l'équivalence des binaires, ni celle des versions entières,
ni l'absence de différences hors de ce sous-ensemble. Les fonctionnalités non
examinées, corrections de bugs et vulnérabilités ne sont pas évaluées ici.

## Prérequis et portée

Choisir humainement l'indice et l'objectif DNS; vérifier le type de requête, le
résolveur et les périmètres cible/résolveur/récursion. Réseau requis uniquement pour
une exécution manuelle distincte. Aucun scan, transfert AXFR/IXFR, ANY, +trace,
fichier d'entrée, secret ou option libre n'est couvert par cette note.
Pour e-mail : sélectionner explicitement le domaine puis valider un nouvel indice.
Pour URL : sélectionner explicitement l'hôte puis valider un domaine ou une IP.
Aucune extraction automatique ni réutilisation de paramètres d'URL n'est autorisée
par la documentation. Aucun test de boîte ou téléchargement HTTP n'est impliqué.

La comparaison établit une correspondance documentaire pour cette version exacte,
pas une compatibilité générale de toute la série 9.20.11 ou Debian/Kali. Les autres
révisions restent non vérifiées. Aucun argument d'analyse DNS n'a été exécuté.
La branche d’intégration ajoute désormais la préparation pour ce bandeau exact,
avec provenance Kali et tests positifs/négatifs. Cette adaptation ne constitue
aucune exécution DNS ni autorisation réseau.
La date de revue `2026-12-07` est un seuil expérimental; elle ne prouve pas la
fraîcheur d'un site ni l'absence de mises à jour. Toute revue reste documentaire,
sans autorisation d'exécution.
