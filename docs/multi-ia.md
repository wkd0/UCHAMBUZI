# Prototype multi-IA et intégration

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

Pour une vue d'ensemble des topologies d'intelligence artificielle présentes ou envisagées pour UCHAMBUZI, consultez [Architectures d'intelligence artificielle](architecture-ia.md).

> Limite du prototype historique : l'interface Textual refuse le fournisseur OpenAI tant qu'elle ne peut pas afficher la requête et recueillir un consentement explicite pour chaque transmission. Le mode de configuration distant ci-dessous est une note d'implémentation expérimentale, pas une procédure utilisateur actuellement disponible.

Dans la version 1.0.0, Textual prend en charge les accès Responses et Claude Code avec
approbation, ainsi que les profils nommés. Utiliser le
[guide courant](installation.md#fournisseurs-ia-distants-facultatifs) pour leur configuration.

Ce document technique décrit l'adaptateur OpenAI expérimental et son protocole [Chat Completions](https://developers.openai.com/api/reference/resources/chat). Aucun appel réel n'a été testé. Anthropic, Gemini et les autres fournisseurs ne sont pas implémentés.

## Utilisation

Lancer avec `uchambuzi --model NAME`, puis `/settings`. Choisir `configure`, le fournisseur `openai` et un modèle accessible à son compte, puis choisir `activate`. La clé est fournie avant le lancement dans la variable d'environnement `OPENAI_API_KEY`, par un moyen protégé adapté au système ; elle n'est ni saisie dans le terminal UCHAMBUZI ni stockée par celui-ci. La présence d'une clé ne valide pas la connexion. Aucun test de connexion automatique n'est effectué ; la première demande confirmée peut être facturée. `/ai` affiche le moteur actif ; `/settings` puis `local` revient immédiatement à Ollama. `/models` ne liste que les modèles locaux.

Pour chaque question distante, conserver le texte, le remplacer par une version expurgée ou annuler. Le corps JSON complet et la destination s'affichent avant confirmation explicite `oui`. L'en-tête d'authentification est volontairement masqué. La confirmation vaut pour cette seule requête. Le mode hybride consiste à choisir le moteur à la main et à reformuler les seuls éléments autorisés. Il n'y a aucun basculement automatique après erreur ou refus.

## Confidentialité et limites

Aucun historique, contexte d'analyse, fichier, preuve ou journal n'est joint automatiquement à une demande distante. Les éléments copiés volontairement dans la question restent sous la responsabilité de l'utilisateur : l'expurgation manuelle n'est pas un détecteur fiable de secrets ni d'indices sensibles. Examiner également les identifiants indirects, chemins, noms d'hôtes, métadonnées et détails d'enquête. Une clé présente littéralement dans le texte est bloquée, mais les autres secrets ne sont pas détectés automatiquement. Les données peuvent être traitées ou conservées selon les conditions, paramètres de compte et politiques du fournisseur ; vérifier ces conditions avant l'envoi. TLS ne protège pas un poste compromis. La variable d'environnement peut être accessible à des processus autorisés localement : utiliser les protections du système, ne jamais la commiter ou la placer dans un journal.

Le profil demande de clarifier le contexte professionnel, de ne pas inventer de résultats et de respecter les refus. Il ne garantit ni l'exactitude ni l'absence de refus. Les sorties sont du texte non vérifié : aucune commande n'est exécutée. Un refus explicite de l'API est conservé. Le moteur de commandes conserve sa propre autorité et ses refus.

## Raccordement dans le candidat intégré

La livraison `349dc1f` et son parent `7f414d8` sont adaptés au terminal intégré.
Le moteur local garde son historique ; le fournisseur distant reçoit seulement
le profil système et la question explicitement confirmée. L’appel de transport
`OpenAIRuntime.chat(messages, consent=True)` exige une confirmation explicite
pour cette requête ; le défaut refuse avant ouverture de connexion. Ce paramètre
est un contrat du code appelant, pas une preuve d’identité humaine ni une défense
contre du code Python hostile exécuté dans le même processus.

Le texte de la clé présente dans OPENAI_API_KEY est masqué à l’affichage, y compris
dans une réponse distante. Aucun contenu de fichier n’est chargé par l’adaptateur.
Une réponse dont `finish_reason` n’est pas `stop` est annoncée incomplète ; un
refus explicite du fournisseur est conservé. Les appels d’outils restent exclus.
Ces champs sont décrits par la [référence officielle Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
consultée le 8 novembre 2026 avec la compétence OpenAI Docs, sans appel d’inférence.

Le délai HTTP est configurable et testé contre un serveur simulé lent. Les
erreurs, interruptions et réponses partielles ne déclenchent ni relance ni repli.
Une interruption cliente ne garantit pas l’arrêt du calcul ni l’absence de
facturation côté fournisseur. DNS, TLS, accès au modèle, quotas et facturation
réels ne sont pas qualifiés par ces tests simulés.

Aucun appel distant réel n’a été exécuté. Une telle recette exige une autorisation
spécifique, un compte, un modèle et une clé adaptés ; aucune donnée d’enquête
réelle ne doit servir à cette recette. La configuration reste en mémoire, le
mode hybride est un choix manuel entre local et distant, sans routeur automatique.
