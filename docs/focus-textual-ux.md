# Dialogue terminal Textual

Les réponses sont rendues directement en Markdown, sans encadrement. Le curseur
`▌` indique une réponse en cours et disparaît à la fin, même après une
interruption. Les clôtures de code manquantes sont complétées uniquement dans
la copie de rendu ; le texte de la réponse reste intact.

Le suivi descend après chaque rafraîchissement du flux. Remonter à la molette
ou avec PageUp le suspend ; revenir tout en bas le réactive. La molette de
l'écran principal agit sur la conversation, y compris au-dessus du prompt ou
du menu. Les modales gardent leur navigation propre. Un redimensionnement
conserve le bas lorsque le suivi est actif.

La bannière reste accessible en remontant dans l'historique de la vue Textual.
Au premier message, le dialogue occupe la hauteur disponible et la bannière
sort de la zone visible. Le menu `/` flotte au-dessus du prompt sans déplacer
les messages ni la saisie. La complétion ne remplace jamais les arguments déjà
saisis.

| Touche | Action |
| --- | --- |
| Entrée | Envoyer |
| Shift+Entrée ou Ctrl+J | Nouvelle ligne |
| ↑ / ↓ | Historique de session ; navigation dans les lignes d'un brouillon multiligne |
| Échap ou Ctrl+U | Vider la saisie |
| Ctrl+A / Ctrl+E | Début / fin de ligne |
| Ctrl+K | Supprimer la fin de ligne |
| PageUp / PageDown | Relire la conversation |
| Ctrl+L | Effacer l'affichage en conservant contexte IA, historique des prompts et saisie |
| Ctrl+C, saisie non vide | Vider la saisie |
| Ctrl+C, génération en cours et saisie vide | Interrompre la génération |
| Ctrl+C, saisie vide et moteur au repos | Afficher l'invite de sortie ; une seconde pression sous 3 secondes quitte |
| Ctrl+D | Quitter directement |
| F6 ou `/copy` | Envoyer la sélection, sinon la dernière réponse, au presse-papiers |
| F7 ou `/copy native` | Basculer entre sélection du terminal et souris de l’application |

Pour copier avec les raccourcis du terminal, appuyez sur **F7**, sélectionnez le
texte en faisant glisser la souris, puis utilisez **Ctrl+Maj+C** (coller :
Ctrl+Maj+V). Cette sélection fonctionne aussi en SSH sans transmission du
presse-papiers. Appuyez à nouveau sur F7 pour retrouver les clics dans les menus
et le défilement de la conversation à la molette ; PageUp/PageDown restent
disponibles dans les deux modes. La barre d’état rappelle le mode sous les
grandes largeurs. Avec de nombreux terminaux, maintenir Maj pendant la sélection
permet également de sélectionner nativement sans changer de mode.

En mode souris de l’application, la sélection est automatiquement envoyée au
terminal au relâchement ; Ctrl+C copie aussi une sélection existante. La copie
utilise OSC 52 et, en session graphique locale, le presse-papiers système.
Certains terminaux ignorent OSC 52 : en SSH, un outil de copie installé sur Kali
ne suffit pas à atteindre le presse-papiers de l’ordinateur hôte. F7 permet alors
la copie native sans installer de service ni modifier la configuration SSH.
Ctrl+Maj+C est généralement traité directement par le terminal ; il copie sa
sélection native et peut ne jamais être transmis à UCHAMBUZI.

Les collages conservent leurs sauts de ligne. La saisie grandit de une à six
lignes. Un clic de lecture dans l'historique laisse la prochaine frappe
rejoindre immédiatement le prompt. Les champs des modales restent indépendants.

La barre d'état masque les raccourcis secondaires sous 85 colonnes. `ctx %`
reflète la limite de session `--context-budget`, exprimée en octets JSON UTF-8.
Son infobulle donne cette unité et les tokens du contexte, estimés pendant le
flux puis exacts lorsque le moteur renvoie ses compteurs. Ce pourcentage ne
prétend pas représenter une fenêtre de tokens que le moteur n'a pas déclarée.

Les thèmes existants proposent une liste textuelle et un ruban continu dans la
prévisualisation. Les couleurs du terminal hôte suivent OSC 10/11 et sont
restaurées par OSC 110/111. Le titre devient `UCHAMBUZI — Assist`, le nom de
l'équipe ou `UCHAMBUZI — #dossier` ; le titre précédent est conservé et restauré
avec la pile de titres xterm. Le rendu des couleurs et du titre dépend du
support de ces séquences par le terminal hôte.
