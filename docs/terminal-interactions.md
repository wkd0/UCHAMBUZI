# Candidat local : interactions du terminal REPL

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note historique d'une recette Prompt Toolkit. Elle ne décrit pas la couverture actuelle de l'interface Textual ; voir [les commandes du candidat](commandes.md).

Ce candidat se teste séparément de `dev`. Il améliore l'interface Rich / Prompt Toolkit.

- Entrée envoie la saisie ; Alt+Entrée ou Ctrl+N ajoute une ligne.
- Un collage multiligne reste dans l'éditeur jusqu'à l'envoi explicite.
- Tab, Maj+Tab et les flèches parcourent les complétions. Entrée accepte une suggestion sélectionnée ; une seconde pression envoie. Échap ferme les suggestions.
- `/theme` et `/mode` ouvrent un sélecteur filtrable : écrire pour filtrer, flèches pour choisir, Entrée pour valider, Échap pour annuler. Les arguments directs et `list` restent disponibles.
- `/audit` complète les chemins de fichiers locaux.
- La barre d'état réduit son contenu à mesure que la fenêtre rétrécit.
- Le démarrage conserve le contenu du terminal, sans ajout de lignes vides pour positionner artificiellement la saisie.
- Les réponses Ollama s'affichent progressivement en Markdown. Ctrl+C interrompt le flux ; le texte partiel reste visible, le tour incomplet n'est pas ajouté au contexte conversationnel.
- Le terminal conserve sa sélection souris et sa molette ; l'application n'active pas de capture souris ni d'écran alternatif.

## Essai isolé

Depuis ce worktree, avec les paquets Rich et Prompt Toolkit installés :

```bash
PYTHONPATH=src python3 -c 'from focus_repl import run_focus_repl; run_focus_repl()'
PYTHONPATH=src python3 -c 'from focus_repl import run_focus_repl; run_focus_repl(model="qwen2.5:3b")'
```

Le premier lancement ne nécessite pas Ollama. Le second utilise un modèle local déjà présent.
Pour isoler aussi l'historique et le thème, définir `XDG_DATA_HOME` et `XDG_CONFIG_HOME` vers un répertoire temporaire avant le lancement.

## Vérifications

```bash
python3 -m unittest discover tests
python3 scripts/verify_terminal_interactions.py
```

La recette PTY supplémentaire nécessite `pexpect` et utilise des données temporaires. Elle vérifie les menus filtrables, le collage, le redimensionnement à 40 colonnes, l'annulation et la fermeture. La sélection graphique avec la souris et le presse-papiers du bureau doivent aussi être essayés dans le terminal VMware : un pseudo-terminal SSH ne les valide pas.

## Résultats de la recette du 9 novembre 2026

- Ubuntu : suite complète de 569 tests, 6 ignorés ; tests ciblés de l'éditeur et du streaming : 38 réussis.
- Kali : 38 tests ciblés réussis et recette PTY réussie. Une exécution complète intermédiaire (565 tests, 5 ignorés) signale les mêmes 11 échecs que `dev` sans ce candidat (558 tests, 5 ignorés). Les identifiants des 11 échecs ont été comparés : aucun échec supplémentaire. Ces tests concernent les anciens parcours d'interface et de repli.
- Ollama réel sur Kali (`qwen2.5:3b`) : réception de fragments avant la fin, reconstruction de la réponse complète et affichage dans le REPL vérifiés.
- Les essais SSH/PTY ne valident pas la sélection souris ni le presse-papiers du terminal graphique VMware.

Fichiers concernés : `src/focus_repl.py`, `src/conversation.py` (callback facultatif de streaming local), `tests/test_focus_repl.py`, `tests/test_repl_stream.py`, `scripts/verify_terminal_interactions.py` et ce document.
