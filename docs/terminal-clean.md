# REPL : saisie et redimensionnement

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Recette et observations historiques sur le terminal Prompt Toolkit. Le lanceur courant privilégie Textual ; ces résultats ne constituent pas une validation de l'interface V1 actuelle.

Le bloc de saisie conserve sa position au bas de la zone interactive du terminal.
La barre d'état reste sur sa dernière ligne après chaque redimensionnement.
L'espace disponible est géré par le layout Prompt Toolkit, sans impression de
lignes vides dans le transcript ni calcul de remplissage après `/clear`.

Les fenêtres Prompt Toolkit désactivent le retour automatique à la ligne. Les
séparateurs utilisent la largeur courante moins une colonne, afin de préserver
la dernière colonne du terminal. Une longue ligne de saisie défile
horizontalement ; les sauts de ligne explicites restent possibles.

Le gestionnaire SIGWINCH natif de Prompt Toolkit conserve la responsabilité de
l'effacement et du redessin de l'éditeur. Avant chaque rendu, les dimensions
Rich sont synchronisées sur les mêmes largeur et hauteur. L'historique déjà
publié reste dans le scrollback natif du terminal.

Une seule barre d'état est affichée. En Assist, son fond est blanc et son texte
noir gras. Elle est masquée à la validation et l'éditeur est effacé avant la
publication du message utilisateur dans le flux.

## Recette Kali

Depuis les sources de la branche à vérifier, sur `kali-vm` :

```bash
python3 scripts/verify_terminal_clean.py
python3 -m unittest discover tests
```

La recette ouvre un serveur tmux isolé, contrôle les tailles
80×24 → 140×40 → 60×20 → 80×24 avec saisie vide puis brouillon, et vérifie les
séparateurs, la barre blanche unique ancrée en bas et son absence dans le scrollback après
validation. Elle nettoie automatiquement son serveur et ses données fictives.
La suite de tests vérifie aussi les attributs noir gras, le menu slash, les
sauts de ligne explicites et les dimensions Rich pendant les changements de taille.

Sur une VM chargée, les deux tests de packaging peuvent dépasser leur délai de
30 secondes avec la compression Debian par défaut. Une exécution complète avec
la compression gzip rapide se lance sans modifier les tests :

```bash
DPKG_DEB_THREADS_MAX=2 DPKG_DEB_COMPRESSOR_TYPE=gzip DPKG_DEB_COMPRESSOR_LEVEL=1 \
  python3 -m unittest discover tests
```

Ces variables ne valent que pour cette commande et conservent les contrôles de
construction, de contenu, d'extraction et d'exécution des paquets.
