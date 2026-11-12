# Références pour les opérations locales ExifTool et strings

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

Consultation locale sur Kali Rolling 2025.3 le 8 novembre 2026. Aucun accès
Internet; seuls les diagnostics de version ont été lancés. Aucun fichier
cible d'enquête, capture, document ou binaire n'a été analysé par cette mission.
Les notes et le catalogue sont fournis pour revue du préparateur : aucun modèle
de syntaxe ci-dessous ne constitue une autorisation ou un résultat d'exécution.

| Outil / opération | Bandeau exact observé | Source locale et paquet |
| --- | --- | --- |
| `exiftool` / `read_metadata` | `13.25` | `/usr/share/man/man1/exiftool.1p.gz`, `libimage-exiftool-perl 13.25+dfsg-1` |
| `strings` / `extract_strings` | `GNU strings (GNU Binutils for Debian) 2.45` | `/usr/share/man/man1/strings.1.gz`, propriétaire `binutils-common:amd64 2.45-4`, programme `binutils 2.45-4` |

Aucune autre version ni autre implémentation (par exemple LLVM strings) n'est
rendue compatible par cette lecture. Les versions structurées 13.25 et 2.45 sont
également reconnues par le catalogue; le préparateur garde le contrôle de son
propre bandeau exact. Les URL amont sont conservées mais n'ont pas été consultées.

## read_metadata

Source attribuée à Phil Harvey par le manuel et les métadonnées du paquet.
Sections examinées : SYNOPSIS/Reading/Writing, DESCRIPTION, Option Details
(-config, -j, -G, -s, -a, -n, --), READING EXAMPLES et AUTHOR.
[Note de lecture](../data/documentation/exiftool-kali.md), identifiant
`exiftool-kali-manual`; origine conservée : https://exiftool.org/.

SHA-256 du manuel compressé :
`bd0ebd668ff69c1eb79a006d85612fd2e2c54baaa3e897d977f43b07fa68a150`.
SHA-256 décompressé :
`90b1a4d37062e819ddbe39957dea31909cfb60e5db5dfaaea1e0d35d1b6e101a`.

Modèle proposé, aligné avec la préparation observée dans l'intégration :

```text
exiftool -config "" -j -G1 -s -- CHEMIN_ABSOLU
```

- `-config` est le **premier** argument. Le suivant est une vraie chaîne vide,
  pas une omission : le manuel précise qu'elle empêche le chargement de la
  configuration personnelle. Une implémentation par liste conserve cet opérande
  vide; aucune concaténation shell n'est nécessaire.
- `-j` seul émet du JSON; **ne pas** accepter `-j=JSONFILE` ou `-json=...`, qui
  importent des données et peuvent écrire. Les valeurs extraites restent non fiables.
- `-G1` qualifie les tags par groupe de famille 1; `-s` sélectionne leurs noms.
  Des tags ayant encore des noms JSON identiques peuvent être supprimés; ne pas
  promettre un inventaire exhaustif. Le manuel décrit `-G4` pour les noms uniques,
  mais son adoption demanderait une adaptation distincte, pas un changement implicite.
- `--` termine les options selon sa section dédiée. Un seul chemin absolu de
  fichier ordinaire sélectionné est accepté par la proposition de règle.
- Paramètres de l'opération : `{}`. Refuser clés supplémentaires, affectations de
  tags, expressions, imports, copie de tags, sortie fichier, récursion, stdin,
  répertoires, fichiers d'arguments, `-execute` et `-stay_open`.

Le mode de lecture est établi par la liste d'arguments restreinte, pas par un
bac à sable ou une garantie générale que cet outil ne sait pas écrire. Refuser
les chemins hors racine, les contrôles, composants `..` et liens symboliques
(parents compris). Contrôler la confiance du binaire, Perl et l'environnement.
Conserver les précautions de montage et d'atime. Les métadonnées peuvent être
absentes, modifiées ou calculées; elles ne démontrent ni auteur ni authenticité.

## extract_strings

Le manuel s'identifie comme GNU Binutils 2.45, date du 16 août 2025; il est
attribué à GNU/FSF. [Note de lecture](../data/documentation/strings-kali.md),
identifiant `strings-kali-manual`; origine conservée :
https://sourceware.org/binutils/docs/binutils/strings.html.
Sections lues : SYNOPSIS, DESCRIPTION, OPTIONS et COPYRIGHT.

SHA-256 du manuel compressé :
`22693da2dc372b7516af0c3f9e60621316e887c028af8f02998806ad7c928ffd`.
SHA-256 décompressé :
`98aee6be33d0a2f574abb899ee0c4cb379e4da10a5687ad9028202a121328aed`.

```text
strings -a -n MIN_LENGTH -e s CHEMIN_ABSOLU
```

- `-a` impose la lecture du fichier entier et évite le parseur BFD de sélection
  de sections. Le manuel avertit des risques de `-d`; ne pas se fier au défaut,
  qui dépend de la compilation.
- `-n` fixe la longueur minimale; le manuel donne **4 par défaut**, sans annoncer
  une limite maximale de 64. `min_length` entier strict **4 à 64 inclus** est une
  restriction UCHAMBUZI proposée et observée dans le préparateur en développement.
- Refuser booléens, flottants, chaînes numériques, null, valeurs <4 ou >64 et
  clés supplémentaires. Ne pas convertir permissivement une entrée invalide.
- `-e s` fixe les caractères 7 bits, sans sélection d'encodage libre. Un autre
  encodage nécessiterait une opération/paramétrisation revue et testée.
- Un seul chemin absolu ordinaire dans une racine sélectionnée. Un tel chemin
  commence par `/`, pas `-` ou `@` : `@file` est un fichier de paramètres récursif
  dans ce manuel. Pas de stdin, FIFO, périphérique, répertoire, `-T`, `-d`, pipeline,
  redirection ou exécution du contenu. Contrôler les liens et traversées comme ci-dessus.

Le seuil ne borne pas le temps, la mémoire ou la taille de sortie. Une sortie
vide ne prouve pas l'absence d'information; une chaîne ne prouve aucune exécution,
connexion ou intention. Aucune décompression ou analyse sémantique n'est faite.
Le moteur prépare une liste d'arguments; tout exécuteur futur demanderait des
limites séparées et une nouvelle validation. Atime, montages et courses restent
à examiner; aucune chaîne de conservation n'est certifiée.

## Raccordement et tests

Les fiches possèdent `documented_operations` (id, bandeaux, syntaxe descriptive,
paramètres et restrictions), et les propositions exposent le même champ. Elles
gardent `status=proposed`, `command_status=not_prepared`,
`execution_authorized=false`. Les empreintes des notes locales sont dans le
catalogue et distinctes de celles des manuels compressés/décompressés ci-dessus.
La fraîcheur est vérifiée à la date d'appel; consultation et approbation humaine
restent deux dimensions séparées. Aucune revue documentaire n'autorise l'exécution.

Le catalogue peut maintenant retourner plusieurs propositions pour un fichier.
Sélectionner explicitement `p['tool']` après choix humain, jamais `proposals[0]`
comme choix automatique et jamais une assertion de cardinalité égale à un.
L'ordre favorise les outils présents puis les bases documentaires cohérentes;
les absences et incertitudes restent affichables, sans masquer les alternatives.

Les tests de contrats optionnels utilisent les producteurs locaux indiqués par
`UCHAMBUZI_AGENT2_ROOT` et `UCHAMBUZI_AGENT4_ROOT`. Aucun accès SSH/Internet n'est
nécessaire. Ils doivent vérifier les listes d'arguments, l'opérande vide de config,
la longueur minimale (dont les types invalides), chemins, racines, liens,
versions non reconnues, empreintes et exécution toujours désactivée.

## Empreintes des notes UCHAMBUZI embarquées

- `exiftool-kali.md` : `6527afd45598dbc0595aed46742cd7a421d203294a550067e4d3f8764fca8a23`.
- `strings-kali.md` : `be55e1e3b81168e43c7d345303719074254085bdbe274bcccefb6de33e455167`.

Ces empreintes vérifient la copie consultable hors ligne; elles ne sont ni une
signature du mainteneur ni une approbation humaine.
