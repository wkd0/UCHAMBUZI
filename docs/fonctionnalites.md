# Fonctionnalités UCHAMBUZI 1.1.0

La candidate privée 1.1.0 utilise **Textual et Rich** : saisie multiligne, historique de session,
complétion slash au-dessus du prompt, huit thèmes avec aperçu, Markdown et code
en streaming, interruption et redimensionnement. Voir le [guide Textual](focus-textual-ux.md).

L'accueil est **Assist**, pour le dialogue général. `/team 1` active l'OSINT Team.
Red, Blue et Purple affichent leur indisponibilité et ne transmettent pas le
texte libre au modèle. Sept spécialités OSINT organisent les recommandations.

Le catalogue est une liste blanche. Douze outils tiers sont embarqués et
installables hors ligne après contrôle SHA-256 : gau, Maigret, Holehe,
PhoneInfoga, Social Analyzer, Blackbird, Subfinder, HTTPX, DNSX, Photon,
TruffleHog et Gitleaks. Les bundles Python utilisent
Python 3.13 et ses dépendances incluses. Les outils Kali sont détectés séparément.
Les entrées « À venir » ne sont pas des installations disponibles.

Les six actions accompagnées restent distinctes des parcours et du shell.
Le parcours archives utilise gau puis curl, avec approbation à chaque étape.

Les raccourcis `/pseudo`, `/domaine`, `/email`, `/archive`, `/photo` et six
playbooks `/scenario <alias> <cible>` sont raccordés dans Textual.
PhoneInfoga est accessible par le playbook `telephone` ; Social Analyzer par
`/pseudo` et le playbook `email-pseudo`, qui attend un pseudonyme.
WhatsMyName est un moteur natif utilisant un jeu de données local ; ses requêtes
aux sites sont actives et soumises à confirmation. Une base locale ne rend pas
les recherches réseau disponibles hors ligne.

Chaque opération proposée affiche son niveau et attend une approbation.
Les commandes proviennent des gabarits intégrés. Les données externes sont
traitées comme non fiables ; la détection d'injection est heuristique et ne
constitue pas une protection absolue. Les résultats doivent être recoupés.

`/investigation create` crée un dossier ; `/investigation open` ouvre un dossier existant. Les analyses, préparations,
exécutions et constats consignés sont horodatés UTC dans un journal en clair.
`/report` produit un rapport Markdown après contrôle de structure du dossier.
Ces contrôles ne garantissent pas l'absence de modification du contenu.
Les anciens dossiers sont lisibles ; un dossier créé ou réécrit en 1.1.0
n'est pas utilisable en 1.0.0. Voir la [compatibilité](releases/1.1.0.md).

Le dialogue IA local utilise Ollama et un modèle installé ; RedSage est proposé
par défaut et reste en calibration. OpenAI/Grok Responses et Claude Code sont
facultatifs, avec aperçu et approbation avant chaque envoi distant. Voir les
[prérequis et limites](installation.md).

Le catalogue `/tools` propose des fiches et la préparation individuelle des six
copies disposant d’une action accompagnée. Le shell libre `!` et `/terminal` demande une approbation et
consigne ses captures dans le dossier. Les conversations peuvent être sauvegardées
et reprises explicitement avec contrôle de structure et de révision, sans restauration
des autorisations. Les résultats sont numérotés et recherchables avec `/details`.

`/ai off` laisse accessibles les fonctions déterministes. Aucun compte ni clé
API n'est requis pour les parcours intégrés. Les services Internet tiers peuvent
changer, refuser des requêtes ou fournir des résultats incomplets.

Voir les [commandes](commandes.md), les [outils et limites](outils-osint.md),
les [composants tiers](../THIRD_PARTY.md) et la [note de candidate 1.1.0](releases/1.1.0.md).
