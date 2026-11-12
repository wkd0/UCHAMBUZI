# Candidat local : flux visuel du terminal

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note historique d'une branche de travail antérieure à l'assemblage Textual. Les recettes ci-dessous attestent uniquement les contrôles et le commit cités, pas l'interface ou le dialogue IA du candidat V1 actuel.

Branche isolée `feature/terminal-codex-flow`, construite depuis le `dev` local `b594282`, puis mise à jour avec les évolutions locales jusqu’à `6b46a50` pendant le développement. Aucune intégration automatique n'est prévue.

## Disposition et interactions

La conversation et les opérations terminées restent dans le défilement natif. Pendant un tour, l'affichage est organisé ainsi :

```text
• UCHAMBUZI
  Consultation du modèle local
  Réponse Markdown progressive…

⠋ Réponse en cours · 3 s · Ctrl+C interrompre
─────────────────────────────────────────────────
› brouillon du prochain message
```

L'activité apparaît au-dessus de la saisie. L'éditeur reste accessible pendant le travail ; Entrée n'envoie pas le brouillon tant que le tour courant n'est pas terminé. À la fin, le brouillon et la position du curseur sont restaurés. L'indicateur temporaire disparaît du flux et une durée remplace l'état d'attente.

Les paragraphes Markdown complets rejoignent progressivement le défilement. Le bloc encore incomplet reste dans un aperçu borné au-dessus de l'éditeur. Les blocs de code clôturés sont conservés ensemble ; les titres sont alignés à gauche, les titres/liens cyan, le code en ligne orange, les blocs de code colorés selon leur langage. `NO_COLOR` reste respecté.

Les opérations locales `/tools`, `/analyze`, `/audit` et `/search` affichent leur activité réelle, puis un résumé de trois lignes. `/details NUMERO` développe une sortie complète ; `/details` ou Ctrl+T développe la dernière. Développer une sortie ne relance jamais une opération.

La préparation conserve son accord humain explicite. Une commande approuvée s'exécute avec le même éditeur actif ; Ctrl+C interrompt son groupe de processus et le résultat complet (stdout/stderr, code, durée et arguments) reste journalisé dans le dossier actif. L'attente Ollama peut également être interrompue, sans enregistrer un tour incomplet. Pour une opération Python locale déjà en cours, Ctrl+C attend sa terminaison plutôt que de prétendre qu'elle a été arrêtée.

Les étapes sont tirées des opérations réellement effectuées. Une conversation libre n'affiche pas de fausses lectures de fichiers ni de pensées internes inventées.

## Défilement

Le terminal conserve sa sélection souris, sa molette et son historique natif. Aucun écran alternatif ni capture souris n'est activé. Le bouton flottant « Back to bottom » visible dans la capture du client graphique appartient à ce client : cette version terminal n'ajoute pas de bouton flottant au scrollback du terminal hôte. Le retour à la saisie utilise les commandes natives du terminal.

La police et sa taille restent celles du terminal choisi par l'utilisateur.

## Essai séparé sur Kali

La copie de recette n'écrase pas la commande `uchambuzi` installée :

```bash
cd ~/uchambuzi-tests/terminal-codex-flow
PYTHONPATH=src python3 -c 'from focus_repl import run_focus_repl; run_focus_repl(model="qwen2.5:3b")'
```

Saisir une question, préparer un brouillon pendant la réponse, essayer Ctrl+C. Vérifier ensuite `/tools`, Ctrl+T, les menus `/theme` et `/mode`, un collage multiligne et le redimensionnement. Le logo, le menu `/team` et les nouvelles commandes de `dev` sont conservés.

## Recettes reproductibles

```bash
python3 -m unittest discover tests
python3 scripts/verify_terminal_interactions.py
python3 scripts/verify_terminal_flow.py
```

Les deux recettes PTY utilisent `pexpect` et des données temporaires. La seconde utilise un serveur Ollama de recette sur loopback, contrôle le brouillon, l'envoi protégé, les couleurs, les sorties développables et l'interruption ; elle produit des traces ANSI pour inspection. Elle ne constitue pas une exécution d'un vrai modèle. Un essai distinct avec le vrai `qwen2.5:3b` sur Kali a aussi vérifié la génération progressive, le brouillon et la fermeture.

Les captures d'aperçu sont reconstruites à partir du vrai flux ANSI de la recette PTY ; elles ne remplacent pas une vérification de la souris et du presse-papiers dans le terminal graphique VMware.

Le nouveau module de rendu fait partie du manifeste d'installation. L'ancien manifeste du REPL reste reconnu pour les mises à jour.

## Validation finale

- Suite complète Ubuntu : 593 tests, succès, 6 ignorés.
- Suite complète Kali : 593 tests, succès, 5 ignorés.
- Les deux recettes PTY passent : menus, collage, redimensionnement, saisie pendant le travail, couleurs, détails et interruption.
- Le vrai modèle `qwen2.5:3b` a été utilisé sur Kali avec le candidat actualisé : génération, conservation du brouillon et fermeture vérifiées.
- Installation temporaire sur Kali, avec HOME/XDG isolés : manifeste incluant le module de rendu, lancement de la commande installée `uchambuzi`, `/tools`, `/details`, réponse Ollama réelle et fermeture vérifiés. L'installation habituelle n'a pas été remplacée.
- L'interruption d'un processus de recette vérifie son arrêt effectif et l'enregistrement de son résultat. Un dossier réel temporaire vérifie aussi la conservation de la sortie complète et la chaîne SHA-256 après réouverture.

Les huit fichiers propres au candidat sont `src/focus_repl.py`, `src/focus_repl_transcript.py`, `src/conversation.py`, `src/installation.py`, `src/parcours.py`, `tests/test_repl_transcript.py`, `scripts/verify_terminal_flow.py` et ce document. Le petit ajout dans `CaseManager` fournit la journalisation des exécutions terminées ou interrompues, nécessaire au parcours d'interruption ; il conserve le format existant des dossiers et journaux.
