# TShark — note de lecture Kali 4.4.7

Note originale UCHAMBUZI, consultation locale le 2026-11-08 via SSH de Kali
Rolling 2025.3. Aucun accès Internet ni analyse d’indice.
Manuel : `/usr/share/man/man1/tshark.1.gz`; paquet observé : `tshark 4.4.7-1+b1`.
Attribution du fichier : `tshark: /usr/share/man/man1/tshark.1.gz`.
Auteur/origine identifiés : Gerald Combs et contributeurs Wireshark; métadonnées copyright locales lues.
Date du manuel : 2025-08-17; diagnostic observé : `TShark (Wireshark) 4.4.7.`.

SHA-256 compressé : `700078f2dca215cb6d50c9979c0f23ce646a9781c6a54780a5ab85a60bdc1459`.
SHA-256 décompressé : `9b2f81424159a66aca3d4dcb8f3802ae198270de674182daf5ae17ba6db7e020`.
Référence d’origine conservée : https://www.wireshark.org/docs/man-pages/tshark.html — URL non consultée.
Le statut amont qualifie le manuel attribué, pas cette synthèse UCHAMBUZI.
L’authenticité cryptographique du paquet n’a pas été revérifiée.

## Fonction et portée

Décoder une capture réseau existante si le fichier sélectionné est effectivement une capture prise en charge.

La section NOTES indique explicitement TShark 4.4.7. Le paquet installé est
4.4.7-1+b1; aucune compatibilité d’autres versions n’est extrapolée. -r lit des
formats pris en charge (y compris certains formats compressés); l’application
ne valide pas qu’un fichier arbitraire en est un. -Y filtre les paquets affichés
et n’est pas un filtre BPF de capture. -T fields nécessite au moins un -e.
-n désactive la résolution de noms; la dernière option -N/-n prévaut sur les
précédentes. Préférences, Lua et plugins demeurent à contrôler. L’option -n seule
n’est ni un bac à sable ni une preuve système d’absence de réseau.
Aucune capture live n’est recommandée et aucune règle de commande TShark n’est
livrée. La pertinence est conditionnelle au choix humain d’une vraie capture.

## Options examinées

- `-r FICHIER` : Lire une capture existante; exclure stdin/FIFO.
- `-n` : Désactiver la résolution de noms; interdire -N qui la réactive.
- `-Y FILTRE` : Filtre d’affichage, distinct d’un filtre de capture.
- `-T fields -e CHAMP` : Sélection de champs, chacun explicitement choisi et validé.

## Prérequis

- Confirmer humainement qu’il s’agit d’une capture compatible; aucun contenu ni extension n’est vérifié ici.
- Lecture hors ligne avec -r et -n; contrôler profils, plugins et Lua, sans privilège de capture.

## Limites

- Une capture partielle, chiffrée ou tronquée limite l’analyse; les dissections peuvent être erronées.
- Aucune acquisition, exhaustivité du trafic, identité d’auteur ni intégrité probatoire n’est établie.

## Risques

- Sans -r, une invocation peut capturer en direct; -n désactive les résolutions mais -N peut le remplacer.
- Dissecteurs/plugins/Lua et capture hostile : isoler l’environnement; une lecture locale ne garantit pas l’absence de trafic.

## Restrictions de la fiche

- Fiche limitée à une capture déjà acquise; aucune capture live, interface, extcap ou élévation.
- Pas de -w, -X, script Lua, plugin fourni par la cible, filtre arbitraire ou export automatique.

## Interprétation prudente

Relier les champs aux paquets et au contexte d’acquisition; un paquet isolé ne suffit pas à attribuer une action.

Résultat attendu : Paquets/champs décodés, avertissements ou erreur de format, uniquement après une analyse séparée.

La date de revue 2026-12-08 est un seuil expérimental, sans contrôle du site
distant. Une correspondance documentaire exacte ne certifie aucune commande,
aucune méthode testée et aucune autorisation d’exécution. Les contenus externes
restent non fiables. Toute autre version reste non vérifiée.
