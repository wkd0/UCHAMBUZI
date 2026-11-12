# Rendu conversationnel Focus

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note technique d'un composant de rendu historique. Le chemin de rendu utilisé par l'interface Textual et son comportement interactif doivent être évalués séparément.

Le renderer `ConversationRenderer` produit une projection distincte de la
source : titres, listes, citations, liens visibles avec leur destination,
tableaux et clôtures de code sont rendus en texte terminal structuré. Les
emphases sont distinguées par des guillemets en l'absence d'attributs curses.
Les blocs de code ne sont pas interprétés comme Markdown ; l'indentation est
conservée dans la source et rendue à l'écran (les tabulations sont développées
sur des taquets de quatre colonnes). La projection neutralise les contrôles
terminaux et de direction. Le texte d'origine reste inchangé.

Le parseur est un sous-ensemble Markdown : les délimiteurs incomplets restent
visibles, sans modifier la source. Il ne prétend pas implémenter CommonMark ou
GFM intégralement : notamment l'imbrication complexe, les tableaux avec barres
verticales échappées, HTML, et la coloration syntaxique ne sont pas pris en
charge. Les longues lignes sont repliées et décorées : leur copie visuelle n'est
pas équivalente à la copie du texte original.

## Interface à transmettre à la mission 02

Sans modification du contrôleur dans cette livraison :

- `layout_message(message, width, streaming=...)` renvoie des `RenderedLine`
  immuables avec `text`, `style` et `source_line`. Le style porte sur la ligne ;
  `inline_spans` expose séparément les emphases et liens. Pour des attributs
  curses précis sur des sous-chaînes après repli, une interface de positions de
  spans et son adaptation au contrôleur restent à définir.
- `anchored_view(layout, height, anchor)` renvoie une fenêtre et une ancre
  `(source_line, occurrence)` ; `anchor=None` suit la fin. Le contrôleur doit
  conserver cette ancre par message pendant le défilement manuel et rétablir
  le suivi de fin sur action de l'utilisateur. Ce raccordement n'est pas réalisé.
- `source_text(message)` fournit le contenu original pour une commande de copie
  explicite. Le contrôleur doit décider du mécanisme de copie et de ses limites.
- Le renderer borne son cache à 64 entrées et n'y conserve pas les sources de
  plus de 65 536 caractères. La construction d'une mise en page reste linéaire
  en taille de réponse ; la liste complète de l'historique et la politique de
  mémoire appartiennent au contrôleur.

La segmentation des grappes traite notamment marques combinantes, ZWJ, tons et
paires régionales. Elle n'est pas une implémentation complète de l'algorithme
Unicode UAX #29 : la largeur et la présentation réelles restent dépendantes du
terminal. Le contrôleur actuel possède son propre calcul de largeur ; son
alignement sur ces fonctions et la saisie pendant génération restent à intégrer.

## Vérifications et limites d'intégration

`python3 -m unittest discover -s tests -p 'test_focus_view.py' -v` vérifie la
restitution exacte des fragments et du snapshot, le rendu Markdown, le code,
l'ancrage simulé, les contrôles dangereux et plusieurs séquences Unicode.
`python3 -m unittest discover -s tests -q` lance la suite complète. Les tests de
rendu ne prouvent pas le comportement d'un terminal ou presse-papiers réel.

Codex CLI 0.167.0 et Claude Code 2.1.319 ont été lancés dans des
pseudo-terminaux à 100 × 30 ; les deux ont produit une sortie, mais aucun écran
d'attente identifiable ni échange comparable n'a été établi automatiquement.
Aucune comparaison interactive de réponses, ni équivalence visuelle, n'est donc
revendiquée.

L'adaptateur historique émet une réponse complète en un seul fragment. Le
streaming réseau, le décodage UTF-8 du transport, l'annulation transactionnelle
et les reprises relèvent de la mission 08. Les événements d'outils structurés
nécessitent également un contrat coordonné. Les tests synthétiques n'établissent
pas ces fonctions.

## Segmentation commune après recette d'intégration

Le contrôleur et l'éditeur utilisent désormais les fonctions de segmentation et
de largeur partagées du renderer. Les propriétés indiciennes de la règle GB9c
sont issues de la [base Unicode 17.0.0](https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt),
figées dans le code, sans téléchargement ni dépendance pip à l'exécution. Le
cas `aक्षb` conserve `क्ष` en un graphème pour la coupe, le déplacement, la
sélection et la suppression. Une conformité UAX #29 exhaustive n'est pas revendiquée.
