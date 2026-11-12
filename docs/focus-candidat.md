# UCHAMBUZI Focus — guide de la préversion 0.3.0-beta.1

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

La commande `uchambuzi` ouvre une seule TUI sur un terminal compatible. Python standard ; aucun paquet pip obligatoire. Le modèle local doit déjà être disponible ; `/models ollama` le vérifie et le sélectionne.

## Interactions

- Entrée soumet ; Ctrl+N ou Alt+Entrée insère une ligne. Pendant une génération, Entrée conserve le brouillon sans soumettre une deuxième requête.
- Ctrl+C interrompt la génération ou l'outil actif ; hors opération il efface le brouillon. Ctrl+S ouvre les paramètres pendant un flux.
- Ctrl+P choisit le mode ; `/scenario` présente les trois scénarios du mode et la conversation libre. `/scenario off` désactive le scénario.
- `/scenario parameters` ouvre le formulaire de valeurs du scénario actif ; `/scenario set NOM VALEUR` valide aussi une valeur explicitement. Les paramètres sont repris avec la session.
- Shift+flèches étend la sélection ; Ctrl+O copie vers le presse-papiers interne et tente explicitement le presse-papiers disponible (Wayland, X11 ou tampon tmux). Ctrl+Y colle la copie interne. `/copy CHEMIN` exporte le texte original de la dernière réponse dans un nouveau fichier privé sans écrasement.
- Tab change de région ; Ctrl+Espace complète le préfixe commun des suggestions. Flèches haut/bas naviguent dans les lignes puis dans l'historique.
- `/settings set history true` active explicitement l'enregistrement ; `/context sessions` reprend une session. Les modèles doivent être revérifiés après reprise. Aucun accord temporaire d'exécution n'est repris.

## Outils : trois actions distinctes

`/tools`, `/analyze TEXTE` et `/prepare OBJECTIF [CIBLE]` passent par le service conversationnel d'outils audités. `/prepare NUMERO` reprend une recommandation affichée. L'opération préparée possède un identifiant.

`/approve ID` présente les détails et attend une réponse humaine. Cet accord ne lance rien. `/execute ID` demande ensuite le lancement explicite avec cet accord unique. Changer de contexte invalide les accords précédents. Le modèle ne possède ni l'autorité ni ces commandes d'exécution. Les modes et scénarios ne donnent aucune permission supplémentaire.

## Terminal et limites

Le décodeur indépendant de `curses.define_key` reconnaît les séquences xterm fragmentées et conserve les préfixes CSI en attente. Escape isolé est distingué après 250 ms ; une coupure plus longue immédiatement après Escape reste intrinsèquement ambiguë. Le mode de collage bracketé évite cette ambiguïté avec les terminaux qui envoient ses délimiteurs. CRLF et CR sont normalisés en LF. Les combinaisons modifiées ne sont disponibles que si le terminal les distingue ; Shift+Entrée peut être identique à Entrée, d'où Ctrl+N. Ctrl+C reste toujours réservé à l'interruption.

La conversation utilise des positions de ligne et colonne source pour maintenir la lecture lors du redimensionnement et de la réception de fragments. Seule la portion d'historique nécessaire à la fenêtre est mise en page ; le reste demeure accessible au défilement. Le rendu présente titres, listes, citations, liens, tableaux et blocs de code, y compris incomplets. Il implémente un sous-ensemble Markdown, pas CommonMark/GFM intégral ; la coloration syntaxique complète et les structures imbriquées complexes restent hors de cette qualification.

Les grappes Unicode courantes (accents, ZWJ, modificateurs emoji, drapeaux, CJK) sont regroupées ; la largeur dépend aussi des polices et du terminal et ne constitue pas une certification complète UAX #29. Sans presse-papiers accessible, la copie interne et l'export demeurent disponibles. Aucun transfert OSC52 implicite n'est effectué.

La comparaison avec Codex CLI et Claude Code reste documentée dans la recette locale. Une égalité complète n'est pas déduite des tests unitaires. Aucun résultat IA ne dispense de vérifier les faits ou l'intégrité des éléments d'enquête.
