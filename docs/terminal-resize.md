# Correctif du redimensionnement des réponses

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Rapport historique de correction sur l'ancien terminal. Il ne constitue pas une recette de redimensionnement de l'interface Textual actuelle.

La capture du défaut montrait deux problèmes : les anciennes coupures de lignes restaient figées après une réduction de largeur, et les fonds/paddings des blocs de code étaient réorganisés en grands rectangles vides par le terminal.

Le rendu conserve maintenant les objets sémantiques des dernières sorties et recalcule la partie visible à la nouvelle largeur. Le rafraîchissement est différé pendant une rafale de changements de taille. Les messages déjà envoyés, le brouillon, les couleurs et les paragraphes terminés sont conservés. Les blocs de code utilisent le fond natif et n'ajoutent plus de lignes de padding.

Le redessin n'utilise ni écran alternatif ni effacement du scrollback. Il intervient lorsque le flux d'UCHAMBUZI a rempli l'écran ; avant cela, le réagencement reste celui du terminal, pour préserver les sorties du shell présentes au-dessus de l'application. L'historique hors écran reste celui du terminal. Le tampon de rendu des dernières sorties n'est pas un journal d'enquête et ne modifie ni les données, ni les commandes, ni le chaînage SHA-256.

## Recette reproductible sur Kali

```bash
python3 scripts/verify_terminal_resize.py
```

Cette recette nécessite tmux et utilise un serveur tmux isolé, des données fictives et un modèle de recette. Elle ne lance aucun outil d'investigation. Elle vérifie :

- une longue réponse avec commande colorée, après affichage complet ;
- les passages 140×36 → 60×24 → 120×32 ;
- le redimensionnement pendant la génération, avec un brouillon saisi ;
- le passage à 72×24 puis à 140×36 après la réponse ;
- une rafale de changements rapides de largeur ;
- la présence des coupures de lignes recalculées à 60 colonnes ;
- la conservation d'un marqueur du shell dans le scrollback.

La même assertion sur les coupures de lignes échoue sur le code antérieur `6599aa7` : `lecture-seule` reste coupé en `lec` / `ture-seule`, avec les anciens fonds et lignes vides. Elle passe sur le correctif.

Les captures texte et ANSI produites par tmux restent dans le répertoire temporaire affiché par la recette. Un essai dans le terminal graphique/SSH réellement utilisé reste utile pour juger sa police et son propre comportement de défilement.
