# Syntaxes de préparation expérimentales

Notes de lecture des manuels amont distribués localement sur Ubuntu et Kali, consultés
le 7 novembre 2026. Ce document décrit seulement les arguments des deux exemples
ci-dessous. Les fiches générales et recommandations restent dans le corpus
 documentaire séparé. Aucun téléchargement ni interrogation Web.

## file 5.46

Source : `/usr/share/man/man1/file.1.gz`, manuel daté du 7 avril 2024,
version 5.46 indiquée dans DESCRIPTION.
SHA-256 du fichier compressé :
`7cef83cc744a8af5342336922d90ad0fdc3f103422b74f1a1475739090db8104`.
Origine amont conservée comme référence : https://www.darwinsys.com/file/

SYNOPSIS et OPTIONS documentent `-b` (omet le nom du fichier dans la sortie)
et `-h` (ne suit pas le lien symbolique final, même si POSIXLY_CORRECT est défini).
Le seul opérande préparé est un chemin absolu de fichier ordinaire : il ne peut
pas être interprété comme une option. Aucun `-z`, `-s`, `-f`, `-m`, `-C`,
chargement de liste, décompression ou écriture n'est proposé.
ENVIRONMENT décrit MAGIC et les bases personnelles : l'environnement et la base
magic doivent être examinés séparément avant toute exécution manuelle.
La lecture peut changer l'atime. L'identification reste heuristique. Un changement
de fichier, de parent ou de montage après la préparation invalide les observations.

## DiG 9.20.24-1ubuntu0.5-Ubuntu

Source : `/usr/share/man/man1/dig.1.gz`, manuel daté du 8 juin 2026,
version exacte dans l'en-tête.
SHA-256 du fichier compressé :
`ea0bc673a6a04335495eff79f36019677aeed04c56642177687b693c42f08b94`.
Origine amont conservée comme référence :
https://bind9.readthedocs.io/en/latest/manpages.html

OPTIONS documente `-r` (ignore .digrc), `@server` (serveur explicite), `-q`
(nom demandé), `-t` (type) et `-x` (recherche inverse PTR d'une IP).
QUERY OPTIONS documente `+nosearch` (désactive la recherche par suffixes),
`+timeout=2` (délai par requête, pas délai global garanti) et `+tries=1`.
Le sous-ensemble retenu autorise seulement A, AAAA, MX et TXT pour un domaine
ASCII absolu, et PTR via `-x` pour une IP sans identifiant de zone. Le résolveur
est une IP explicite. Ni AXFR, IXFR, ANY, +trace ni fichier de commandes/clé.
Une requête DNS est une interaction réseau active : le résolveur et les serveurs
peuvent la journaliser. La récursion du résolveur peut atteindre d'autres serveurs;
l'autorisation de la cible et du résolveur doit inclure ces effets. Des réponses
tronquées peuvent entraîner une reprise TCP. Le résultat n'est jamais présumé.

## DiG 9.20.11-4+b1-Debian — Kali Rolling 2025.3

Source locale : `/usr/share/man/man1/dig.1.gz`, fourni par bind9-dnsutils
`1:9.20.11-4+b1`, en-tête du 4 juillet 2025. Auteur amont : ISC.
SHA-256 compressé :
`faaf11b7648a35d0df5b2fb87d0e4c7889e6a1e25e70b2f6037a1020097815c4`.
SHA-256 décompressé :
`aa73b2dd16e0f0e0701645dd181729d320dffe6eee62281a1fafd85e4032236e`.
Origine conservée, non consultée sur le Web :
https://bind9.readthedocs.io/en/latest/manpages.html

La comparaison locale consignée dans `data/documentation/dig-kali.md` et
`docs/dig-kali-compatibilite.md` établit le même sens pour le seul sous-ensemble
`-r`, `@server`, `-q`, `-t`, `-x`, `+nosearch`, `+timeout=2`, `+tries=1`.
Le bandeau exact admis est `DiG 9.20.11-4+b1-Debian` ; les autres révisions
Debian/Kali ne sont pas extrapolées. Les restrictions de types DNS, de cibles,
de résolveurs IP, de périmètre, de récursion et de reprise TCP décrites plus haut
s'appliquent intégralement. Les plans émis conservent l'empreinte de ce manuel
Kali, distincte de celle d'Ubuntu. Aucune requête DNS n'est exécutée par la recette.

## Portée de la preuve

Ces notes établissent une base syntaxique pour les bandeaux exacts déclarés,
pas la confiance dans l'exécutable ni une approbation d'exécution. Les tests de
préparation sur Kali ne constituent pas un test de résolution DNS. Le champ
historique `tested_on_kali=false` ne revendique aucune exécution d'investigation.
Aucune plage de versions compatible n'est extrapolée.

## Lectures locales supplémentaires — Kali, 8 novembre 2026

Lecture directe des manuels installés sur la VM de recette, sans consultation Web
pour ces deux outils. Ce sont des notes de lecture de l'Agent 4, distinctes des
fiches de recommandation attendues de l'Agent 3. Aucune exécution des commandes
préparées n'est revendiquée. Aucune plage de versions n'est déduite.

### ExifTool

- Bandeau exact : `13.25` ; paquet `libimage-exiftool-perl 13.25+dfsg-1`.
- Manuel original : `/usr/share/man/man1/exiftool.1p.gz`, daté du 16 mars 2025.
- SHA-256 compressé : `bd0ebd668ff69c1eb79a006d85612fd2e2c54baaa3e897d977f43b07fa68a150`.
- SHA-256 décompressé : `90b1a4d37062e819ddbe39957dea31909cfb60e5db5dfaaea1e0d35d1b6e101a`.
- Référence amont identifiée par le paquet : https://exiftool.org/exiftool_pod.html
  (lien non consulté pendant cette lecture locale).
- Syntaxe retenue : `exiftool -config '' -j -G1 -s -- /chemin/absolu`.

La section `-config CFGFILE` exige la première position ; la chaîne vide empêche
le chargement de la configuration personnelle. `-j` sans fichier d'import
formate la sortie en JSON ; `-G1` ajoute les groupes famille 1 ; `-s` retient les
noms des tags ; `--` termine les options. Aucune affectation, import, récursion,
commande Perl, sortie sur fichier ou session persistante n'est autorisée.
Des noms JSON identiques peuvent être supprimés par ExifTool : cette présentation
ne prétend pas extraire exhaustivement toutes les métadonnées. Les données et
dates ne prouvent pas leur authenticité. Une lecture peut modifier l'atime.

### GNU strings

- Bandeau exact : `GNU strings (GNU Binutils for Debian) 2.45` ; paquet `binutils 2.45-4`.
- Manuel original : `/usr/share/man/man1/strings.1.gz`, binutils-2.45, 16 août 2025.
- SHA-256 compressé : `22693da2dc372b7516af0c3f9e60621316e887c028af8f02998806ad7c928ffd`.
- SHA-256 décompressé : `98aee6be33d0a2f574abb899ee0c4cb379e4da10a5687ad9028202a121328aed`.
- Référence amont : https://sourceware.org/binutils/docs/binutils/strings.html
  (lien non consulté pendant cette lecture locale).
- Syntaxe retenue : `strings -a -n MINIMUM -e s /chemin/absolu`.

`-a` parcourt le fichier entier et évite la sélection des sections par BFD ;
`-n` fixe la longueur minimale ; `-e s` fixe les caractères à un octet de 7 bits.
Le minimum doit être un entier entre 4 et 64 (restriction UCHAMBUZI, non limite
annoncée de GNU strings). Le chemin absolu ne peut commencer par `-` ou `@`.
Aucun fichier d'arguments, entrée standard, encodage libre, cible BFD, pipeline,
redirection ou décompression n'est proposé. La sortie peut être volumineuse ou
fortuite ; elle ne prouve aucun comportement du fichier.

Les deux règles exigent un fichier ordinaire dans une racine explicite, sans
composant `..` ni lien symbolique. Elles ne verrouillent ni le fichier ni les
montages et ne certifient pas l'intégrité des exécutables. Un montage distant
reste possible derrière un chemin local. L'exécution reste toujours désactivée.
