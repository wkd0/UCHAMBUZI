# Moteur IA — candidate privée Textual 1.1.0

Ce guide décrit le moteur de la candidate non publiée. La recette V1 citée
ci-dessous reste une preuve historique de la 1.0.0, pas une nouvelle recette 1.1.0.

Le dialogue courant passe par `FocusREPL`, `conversation.Session` et le runtime
Ollama ou les fournisseurs distants facultatifs configurés par `/settings`.
Les accès distants peuvent être enregistrés sous plusieurs noms ; les clés saisies
sont conservées séparément, en fichier `0600` non chiffré. Les variables
d’environnement restent utilisables. Voir les [réglages des accès](installation.md#fournisseurs-ia-distants-facultatifs).
Les délais sont gérés par fournisseur et ne figurent plus dans les réglages
courants. La reprise explicite des conversations est décrite dans le
[guide des commandes](commandes.md#reprendre-une-conversation) ; elle ne restaure
pas les autorisations. Le lancement ne télécharge pas de
modèle. La recette V1 a reçu une réponse réelle de `qwen2.5:3b` dans le terminal
Kali avec le paquet installé. Voir la [note V1](releases/1.0.0.md) pour sa portée.

## Mesure du contexte dans la session Textual

La session `conversation.Session` expose un instantané `context_usage`, actualisé
avant l'appel de rendu de chaque fragment et à la fin du tour. `used_bytes` inclut
le message système, l'historique, les données techniques effectivement transmises,
la question et la réponse en cours. `budget_bytes` est la limite existante de
`--context-budget` en JSON UTF-8 ; le pourcentage `ctx` mesure cette limite de
session, sans la présenter comme la fenêtre de tokens du modèle.

`used_tokens` est la somme `prompt_eval_count + eval_count` du dernier appel
Ollama quand ces compteurs sont disponibles et valides. Pendant la génération,
ou avec un moteur qui ne publie pas ces statistiques, il s'agit d'une estimation
indicative de quatre octets de texte par token (`tokens_estimated=True`). Les
compteurs des appels successifs ne sont pas cumulés. Aucun budget de tokens
n'est supposé lorsque le serveur ne le fournit pas. Une interruption ou un échec
restaure la mesure du dernier tour conservé ; `/reset` efface cette mesure.

## API du composant historique FocusAI

> Référence de composant conservée pour les développeurs. Les résultats anciens
> ci-dessous ne certifient pas le parcours Textual V1 et ne décrivent pas les
> options de configuration disponibles pour son utilisateur.

`FocusAI` implémente `ConversationEngine` sans dépendance pip. Par défaut il cible
Ollama sur `127.0.0.1:11434`, modèle de référence `qwen2.5:3b`. Il ne lance ni
n'installe de moteur et ne télécharge aucun modèle. Un démarrage sans serveur
reste possible; un tour retourne alors une erreur structurée. Les mécanismes
historiques restent disponibles indépendamment.

## Utilisation et intégration

Ajouter `src` au chemin Python. `await ai.discover()` ne sonde que les
fournisseurs locaux activés. `await ai.models(id)` retourne les modèles et leurs
métadonnées annoncées; `await ai.select(id, modele)` vérifie leur présence.
`ai.configure(GenerationSettings(...))` valide les réglages pris en charge.
Le moteur expose `provider_id`, `model_id`, `providers` et `settings` pour les
futures commandes. Les sondes de modèles sont asynchrones côté appelant.

`async for event in ai.stream(turn_id, message)` produit `TurnStarted`, zéro ou
plusieurs `TextDelta`, puis `TurnFinished`. Les événements conservent l'identifiant
du tour. Les fragments sont du texte brut, y compris Markdown partiel; leur
assemblage appartient au renderer. Le réseau tourne dans un thread dédié et un
délai total borne la génération. `ai.cancel(turn_id)` interrompt le tour actif;
une interruption, une réponse tronquée ou une limite de génération atteinte ne
sont jamais annoncées comme complètes. Le serveur peut toutefois continuer son
calcul après la fermeture de la connexion. Ne traiter comme réponse complète que
l'état `COMPLETE`. Une seule génération par instance est admise.

`ai.mode_engine` est le moteur de mission 06. Ses instructions composées sont
transmises comme message système à chaque tour. `ai.scenario` est un texte de
contexte facultatif pour la future intégration des scénarios; `ai.history` est
un tuple de `Message` utilisateur/assistant fourni par le gestionnaire de session.
Le moteur n'enregistre aucune conversation et ne modifie aucune permission.
L'intégration doit décider quels tours réussis conserver et gérer le budget de
contexte; aucun tour partiel ne doit être ajouté automatiquement à l'historique.

## Fournisseurs et confidentialité

`HTTPProvider` prend en charge Ollama (`protocol='ollama'`, HTTP exclusivement
sur `127.0.0.1`) et l'API HTTPS `chat/completions` à flux SSE compatible OpenAI
(`protocol='openai'`, endpoint de base par exemple `https://example.org/v1`).
Les autres protocoles peuvent être ajoutés par un adaptateur exposant `id`,
`local`, `enabled`, `capabilities`, `list_models` et `generate`. Aucun proxy ni
redirection HTTP n'est suivi. Les modèles externes sont découverts avec
`await ai.models(id, allow_external=True)` seulement après choix explicite;
la sélection nécessite également `allow_external=True`. Chaque tour externe
nécessite de nouveau `stream(..., allow_external=True)`. Ce choix autorise la
transmission de l'instruction de mode, de l'historique, du scénario et du message
au fournisseur sélectionné. L'interface appelante doit obtenir cette décision
de l'utilisateur pour le contenu concerné. Un fournisseur peut être désactivé
avec `enabled=False` lors de sa configuration.

La clé est référencée par le nom d'une variable d'environnement `secret_env` et
lue au moment de la requête; elle n'est ni stockée dans la configuration ni
incluse dans les erreurs. La protection de l'environnement relève du lanceur :
ne pas placer la clé dans un fichier de configuration public ou un historique
shell. Aucun corps d'erreur fournisseur n'est exposé. Les codes incluent
`authentication`, `quota`, `provider_unavailable`, `model_not_found`,
`incomplete_response`, `timeout` et `external_consent_required`.

La température (0–2), la limite de génération, le délai et le streaming sont
pris en charge; la taille de contexte est envoyée uniquement à Ollama. Les outils,
options arbitraires et génération non streaming sont refusés. Ces capacités
représentent les champs du protocole, pas la garantie qu'un modèle particulier
les accepte. Les limites propres aux modèles ne sont pas toujours publiées et
les erreurs du serveur restent possibles. Les appels d'outils reçus, sorties
tronquées et fins de génération autres que `stop` sont refusés.

## Vérification

Tests déterministes : `python3 -m unittest discover -s tests -p 'test_focus_*.py'`;
suite globale : `python3 -m unittest discover -s tests`. Les tests simulés ne
prouvent pas la compatibilité avec tous les services externes. Un essai local
séparé a utilisé Ollama et `qwen2.5:3b` déjà présents, sans installation ni
téléchargement : 70 fragments reçus pour une réponse, premier à 0,05 s et dernier
à 0,82 s, puis état `COMPLETE`. Aucun service externe réel n'a été sollicité.
La TUI, les scénarios et la persistance restent à raccorder par leurs missions.
