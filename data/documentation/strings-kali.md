# GNU strings — note de lecture Kali 2.45

Note originale UCHAMBUZI, consultation locale le 2026-11-08 via SSH de Kali
Rolling 2025.3. Aucun accès Internet ni analyse d’indice.
Manuel : `/usr/share/man/man1/strings.1.gz`; paquet observé : `binutils 2.45-4`.
Attribution du fichier : `binutils-common:amd64: /usr/share/man/man1/strings.1.gz`.
Auteur/origine identifiés : Free Software Foundation et contributeurs GNU Binutils; métadonnées copyright locales lues.
Date du manuel : 2025-08-16; diagnostic observé : `GNU strings (GNU Binutils for Debian) 2.45`.

SHA-256 compressé : `22693da2dc372b7516af0c3f9e60621316e887c028af8f02998806ad7c928ffd`.
SHA-256 décompressé : `98aee6be33d0a2f574abb899ee0c4cb379e4da10a5687ad9028202a121328aed`.
Référence d’origine conservée : https://sourceware.org/binutils/docs/binutils/strings.html — URL non consultée.
Le statut amont qualifie le manuel attribué, pas cette synthèse UCHAMBUZI.
L’authenticité cryptographique du paquet n’a pas été revérifiée.

## Fonction et portée

Repérer les séquences de caractères imprimables, sans interpréter la structure du fichier comme ExifTool.

Le manuel binutils-2.45 décrit des valeurs par défaut dépendantes de la
compilation : certains builds limitent la recherche aux sections de données.
-a force le parcours complet et évite BFD, contrairement à -d qui peut exposer
ses vulnérabilités de parseur. -n fixe le seuil (4 par défaut), -t x l’offset en
hexadécimal. Ne pas utiliser -o comme synonyme universel d’offset décimal : GNU
l’associe à l’octal et le manuel signale des différences avec d’autres versions.
-e s recherche les caractères 7 bits; -e l et -e b couvrent des séquences 16 bits.
Ce ne sont pas une détection automatique ou une extraction exhaustive d’Unicode.
@file lit des options, récursivement : un chemin absolu commençant par / évite
cet opérande spécial et une option débutant par -. Aucun de ces fichiers n’est
lu ni exécuté par ce composant documentaire.
Le propriétaire du manuel est binutils-common:amd64 2.45-4; le programme relève
de binutils 2.45-4. Le diagnostic observé est GNU strings (GNU Binutils for Debian)
2.45; aucune compatibilité LLVM ou autre build n’est extrapolée.

## Options examinées

- `-a` : Parcourir tout le fichier, sans analyse de sections par BFD.
- `-n N` : Longueur minimale; défaut 4 dans le manuel, borne à définir par le préparateur.
- `-t x` : Offsets hexadécimaux; -t d pour décimaux.
- `-e s` : Octets sur 7 bits; -e l pour 16 bits little-endian, -e b pour big-endian.

## Prérequis

- Fichier ordinaire lisible, copie sélectionnée et limites de taille/temps/sortie.
- Choisir longueur minimale et encodage; ne pas exécuter le fichier analysé.

## Limites

- Une chaîne peut être fortuite, inactive ou injectée; elle ne prouve aucune exécution ni connexion.
- Les données chiffrées, compressées, obfusquées ou d’un autre encodage peuvent rester invisibles.

## Risques

- Le manuel signale l’exposition au parseur BFD avec -d; privilégier -a pour lecture brute.
- Sortie hostile ou volumineuse : échapper les contrôles, limiter l’affichage; atime et montages distants à examiner.

## Restrictions de la fiche

- Fichier absolu ordinaire seulement; pas de répertoire, FIFO, périphérique ou stdin.
- Pas de -d, -T/--target ni de @fichier de paramètres; pas d’option libre, shell ou pipeline.

## Interprétation prudente

Relier chaque fragment à son offset et à l’encodage choisi; confirmer toute hypothèse avec un outil approprié.

Résultat attendu : Fragments imprimables accompagnés éventuellement d’offsets, ou absence; aucun comportement du fichier n’est établi.

La date de revue 2026-12-08 est un seuil expérimental, sans contrôle du site
distant. Une correspondance documentaire exacte ne certifie aucune commande,
aucune méthode testée et aucune autorisation d’exécution. Les contenus externes
restent non fiables. Toute autre version reste non vérifiée.

## Opération proposée au préparateur : extract_strings

Modèle documentaire, aucune commande exécutée ni autorisation accordée :

```text
strings -a -n MIN_LENGTH -e s CHEMIN_ABSOLU
```

- Un seul chemin absolu de fichier ordinaire dans une racine sélectionnée, sans liens ni traversées.
- Le manuel décrit un défaut de 4, sans maximum 64; la borne 4..64 est une restriction du préparateur.
- Refuser booléens, chaînes, flottants, valeurs hors bornes ou paramètres supplémentaires.
- Lecture brute complète via -a; encodage fixe -e s; pas de @fichier, -d, -T, stdin ou option libre.

Le choix 4..64 peut limiter le bruit affiché mais ne borne ni le temps ni la
taille de sortie. Le contrôle doit porter sur un entier strict, pas sur une
conversion permissive. Ces règles applicatives doivent être testées dans le
moteur; ce composant ne lit ni n’exécute le fichier cible.
