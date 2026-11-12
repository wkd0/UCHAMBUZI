# ExifTool — note de lecture Kali 13.25

Note originale UCHAMBUZI, consultation locale le 2026-11-08 via SSH de Kali
Rolling 2025.3. Aucun accès Internet ni analyse d’indice.
Manuel : `/usr/share/man/man1/exiftool.1p.gz`; paquet observé : `libimage-exiftool-perl 13.25+dfsg-1`.
Attribution du fichier : `libimage-exiftool-perl: /usr/share/man/man1/exiftool.1p.gz`.
Auteur/origine identifiés : Phil Harvey; métadonnées copyright locales lues.
Date du manuel : 2025-03-16; diagnostic observé : `13.25`.

SHA-256 compressé : `bd0ebd668ff69c1eb79a006d85612fd2e2c54baaa3e897d977f43b07fa68a150`.
SHA-256 décompressé : `90b1a4d37062e819ddbe39957dea31909cfb60e5db5dfaaea1e0d35d1b6e101a`.
Référence d’origine conservée : https://exiftool.org/ — URL non consultée.
Le statut amont qualifie le manuel attribué, pas cette synthèse UCHAMBUZI.
L’authenticité cryptographique du paquet n’a pas été revérifiée.

## Fonction et portée

Lire les métadonnées des formats pris en charge, en complément du type probable fourni par file.

Le manuel décrit séparément Reading et Writing. Une affectation -TAG=... ou
un import peut basculer en écriture; les options de lecture ne neutralisent pas
ce mode. -config doit être le premier argument; sa valeur vide désactive le
chargement automatique de .ExifTool_config. -j seul formate la sortie, mais
-j=JSONFILE importe des données. -a conserve les doublons pour l’affichage texte;
en JSON des noms identiques peuvent être supprimés : -G1 n’assure pas l’unicité
de tous les tags, -G4 est décrit pour les noms uniques. Une première règle simple
peut donc préférer -a -G1 -s en texte, sans prétendre collecter tous les tags.
Éviter -fast : le manuel explique qu’il omet certaines recherches de métadonnées.
La version 13.25 est liée au paquet installé et au diagnostic -ver; l’en-tête
indique Perl v5.40.1, pas une autre version d’ExifTool.

## Options examinées

- `-config ""` : Désactiver la configuration par défaut; deux arguments, premier paramètre obligatoire.
- `-a` : Afficher aussi les tags dupliqués.
- `-G1` : Afficher le groupe de famille 1 par tag.
- `-s` : Afficher les noms techniques des tags.
- `-j` : Sortie JSON sans argument de fichier; -j=FICHIER est un import et est exclu.
- `-n` : Désactiver les conversions de présentation, pas toutes les valeurs calculées.

## Prérequis

- Copie de travail lisible et format pris en charge; ne pas confondre lecture et écriture.
- Désactiver la configuration personnelle avant toute opération préparée; contrôler environnement et montage.

## Limites

- Métadonnées modifiables, absentes ou contradictoires; une date ou un auteur ne prouve pas l’origine.
- Certains tags sont calculés/composites; absence de tag ne prouve pas absence d’information.

## Risques

- L’outil peut aussi écrire ou supprimer des métadonnées; aucune affectation de tag n’est autorisée ici.
- Données hostiles et configuration personnalisée à isoler; une lecture peut modifier l’atime ou utiliser un montage distant.

## Restrictions de la fiche

- Lecture seule d’un fichier ordinaire sélectionné; pas de répertoire, stdin ou récursion.
- Refuser affectations, -tagsFromFile, -geotag, -csv=, -json=, -w/-W, -o, -execute, -stay_open, -@, -if et expressions de format.

## Interprétation prudente

Croiser les tags avec le format, les fuseaux et d’autres sources; distinguer valeur stockée, conversion et calcul.

Résultat attendu : Tags avec noms/groupes, avertissement ou erreur de format; aucune authenticité ni chronologie n’est démontrée.

La date de revue 2026-12-08 est un seuil expérimental, sans contrôle du site
distant. Une correspondance documentaire exacte ne certifie aucune commande,
aucune méthode testée et aucune autorisation d’exécution. Les contenus externes
restent non fiables. Toute autre version reste non vérifiée.

## Opération proposée au préparateur : read_metadata

Modèle documentaire, aucune commande exécutée ni autorisation accordée :

```text
exiftool -config "" -j -G1 -s -- CHEMIN_ABSOLU
```

- Premier argument -config, suivi d’une chaîne vide réelle, avant toute autre option.
- Un seul fichier ordinaire absolu dans une racine sélectionnée; refuser liens et traversées.
- Paramètres vides, aucune option libre, affectation ou import; JSON non fiable et pas forcément exhaustif.

La section `--` du manuel confirme la fin des options : les opérandes suivants
sont des noms de fichiers, même s’ils commencent par un tiret. Le préparateur
reste plus strict et exige un chemin absolu ordinaire. Le modèle JSON correspond
à une sortie de lecture, pas à `-j=FICHIER`; les tags de noms identiques peuvent
être supprimés et les métadonnées restent modifiables.
