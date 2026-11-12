# Logo du bandeau terminal

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Spécification d'une version antérieure du terminal ; la composition de l'interface Textual actuelle n'est pas validée par cette note.

Le cadre est centré horizontalement, avec une largeur maximale de 100 colonnes.
Il utilise toute la largeur disponible sur un terminal plus étroit.

Le bandeau reprend la composition de
`assets/branding/logo/uchambuzi-lockup-horizontal.svg` : petit symbole à
gauche et nom espacé orange et gras à droite. À partir de 100 colonnes,
version, description, spécialité, moteur IA et enquête sont alignés sous
le nom dans la colonne de droite. Le symbole occupe six lignes au lieu de
quatorze. Le nom est du texte natif pour rester lisible à cette taille.

Entre 64 et 99 colonnes, le nom reste à droite du symbole et les informations
passent sous le lockup. Sous 64 colonnes, le nom précède les informations
sans symbole pour préserver la lisibilité. Le nom n'est affiché qu'une fois
dans le contenu du bandeau ; les libellés des informations sont alignés.

Le symbole est dérivé du groupe `symbol` du SVG horizontal (transformation
incluse). Son masque embarqué dans `src/focus_banner_logo.py` utilise
22 × 12 pixels et les demi-blocs Unicode de Rich. Les cellules vides
conservent le fond du terminal. Aucune dépendance graphique n'est nécessaire
au lancement ; le module fait partie de l'inventaire d'installation.

La couronne et les points reprennent la couleur principale du thème ;
le contour utilise la couleur secondaire de texte pour rester lisible
sur fond sombre. Le nom utilise la couleur principale orange.

## Sources examinées

- `logo/` : symbole orange/bleu nuit, variantes monochromes, compositions
  horizontale et verticale. La composition horizontale est la référence retenue.
- `icons/` : même symbole, cadrage ajusté dans le SVG et tailles PNG 16 à 512.
- `web/` : `favicon.svg` reprend le symbole avec cadrage ajusté ; favicon PNG
  et ICO, icônes d'application blanches sur fond bleu nuit.
- `web/site.webmanifest` : métadonnées d'installation web (nom, couleurs,
  icônes, page de démarrage). Il ne produit aucun dessin terminal.

Le masque est produit avec librsvg et Pillow : retrait du groupe `wordmark`
pour son rendu en texte natif, cadrage `viewBox="6 34 216 164"`, rendu
220 × 120 sans conservation automatique du ratio, réduction Lanczos à
22 × 12, seuil alpha 85 ; pixels orange si rouge > 45, contour sinon.
Le cadrage est adapté aux cellules terminal plus hautes que larges.
Les plus petits détails du SVG sont simplifiés à cette résolution.

Pour voir les couleurs si l'environnement SSH définit `NO_COLOR` :

```sh
env -u NO_COLOR COLORTERM=truecolor uchambuzi
```
