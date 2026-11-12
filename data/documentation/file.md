# file(1) — note de lecture locale

Synthèse rédigée pour UCHAMBUZI, pas une copie intégrale du manuel.
Consultation locale : 2026-11-07, Ubuntu. Aucune consultation Web.
Manuel amont fourni par le paquet Ubuntu file 1:5.46-5build2.
Version documentée dans DESCRIPTION : 5.46; date du manuel : 2024-04-07.

Sections examinées : NAME, SYNOPSIS, DESCRIPTION, OPTIONS, BUGS, AVAILABILITY.
Le programme classe les fichiers en appliquant des tests de système de fichiers,
de signatures puis de langage. Le premier test réussi détermine le type affiché.
La base magic influe sur l'identification. Les tests de langage sont moins fiables.
Le résultat attendu est une description de type, pas une preuve d'authenticité.

Précautions UCHAMBUZI : lecture locale pouvant affecter les temps d'accès;
travailler sur une copie et documenter le montage et l'environnement. La présence
du programme et la correspondance de version ne prouvent pas un test forensic.
Aucune commande d'analyse n'a été exécutée pour rédiger cette note.
Origine du projet conservée comme référence : https://www.darwinsys.com/file/
Cette URL n'a pas été consultée. La provenance vérifiée est le manuel local.

## Portée de la vérification

La note UCHAMBUZI est une synthèse interne au corpus, pas une documentation
publiée ni approuvée par le mainteneur de l'outil. Le statut « upstream_manual »
qualifie le manuel original identifié par le paquet et ses mentions d'auteur.
La présence d'un fichier ou sa seule empreinte n'établit pas cette qualité.
Les empreintes compressée et décompressée ont été recomparées au fichier local
le 2026-11-07. L'authenticité cryptographique du paquet n'a pas été revérifiée.
La consultation concerne cette copie Ubuntu, pas le contenu actuel de l'URL.
Aucune plage de compatibilité n'est connue par test d'exécution. Seule la version
exactement documentée est reconnue; une autre version exige une nouvelle lecture.
La date de revue 2026-12-07 est un seuil expérimental : avant cette date, « current »
ne signifie pas que le contenu distant a été contrôlé ou qu'aucune mise à jour existe.

L'interaction est une lecture de fichier, sans écriture volontaire proposée.
Un montage réseau peut toutefois provoquer du trafic; « local_read » ne garantit
pas un disque physiquement local. La base magic, MAGIC et les bases personnelles
influencent les résultats. Les contrôles de chemins ne verrouillent pas les fichiers.

## Vérification complémentaire sur Kali

Le 2026-11-07, le manuel de Kali GNU/Linux Rolling 2025.3 a été lu via SSH local.
Le paquet propriétaire du fichier est `file 1:5.46-5`; `file --version` retourne
`file-5.46`. Les empreintes compressée et décompressée sont identiques à celles du
manuel Ubuntu déjà référencé. Cette observation confirme la documentation de la
version détectée, sans extrapoler d'autres versions. Le propriétaire a signalé
une préparation compatible dans sa recette; aucune analyse de fichier n'a été
exécutée par cette mission pour la reproduire. Les précautions de montage, magic,
liens, atime et chaîne de conservation restent applicables.
