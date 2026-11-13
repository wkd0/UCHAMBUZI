# Utiliser UCHAMBUZI 2.0.0

Sur Kali : `uchambuzi --version`, `uchambuzi doctor`, puis `uchambuzi`.
L'accueil commence en Assist. `/ai` choisit un modèle local et `/settings`
configure Ollama ou un fournisseur distant facultatif. Pour enquêter, sélectionner
`/team 1` puis `/investigation create exercice-v1` pour un nouveau dossier, ou
`/investigation open exercice-v1` pour un dossier existant. Le sélecteur propose
ensuite une conversation sauvegardée, une reprise ou de continuer sans sauvegarde.

```text
/tools setup
/tools list
/analyze 192.0.2.1
/prepare 1
/investigation log
/report
```

Une installation ou une exécution demande confirmation : `o` puis Entrée
approuve ; Entrée seule refuse. `/prepare` peut ensuite proposer une exécution.
Ne confirmer que dans le périmètre autorisé. `/pseudo`, `/email`, `/domaine`,
`/archive` et `/photo` offrent des parcours directs. `/scenario` ouvre le
sélecteur ; `/scenario telephone +12025550123` propose les étapes PhoneInfoga.

Entrée envoie, Shift+Entrée ou Ctrl+J insère une ligne, ↑/↓ retrouve le brouillon
et l'historique. `/` complète une commande. La molette permet de relire les
messages, même pendant le streaming. `/theme` ouvre les palettes.
`/tips` affiche ou masque les conseils contextuels. `/tools` présente les fiches
des outils ; `/details search texte` recherche parmi les résultats numérotés.
F6 ou `/copy` copie la dernière réponse et `/copy commande` la commande préparée.
Ctrl+C vide une saisie ; sur saisie vide pendant une génération, il interrompt
le modèle. Au repos, une seconde pression sous trois secondes quitte.
Ctrl+D ou `/exit` ferme l'application. Ctrl+L efface la vue en gardant la session.

Références : [commandes](commandes.md), [interaction Textual](focus-textual-ux.md),
[Assist et Teams](assist-teams.md), [installation et données](installation.md).
