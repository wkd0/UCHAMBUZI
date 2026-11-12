# UCHAMBUZI Focus — socle architectural v1

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note de conception historique antérieure au passage de l'interface principale à Textual. Les détails ci-dessous décrivent les décisions et interfaces de l'époque, pas l'architecture intégrée actuelle. Voir le [guide des commandes](commandes.md) et les [fonctionnalités](fonctionnalites.md).

## Statut et décision

Le candidat intégré utilise une TUI `curses` en Python standard. Les contrats v1 sont conservés. La proposition Textual ci-dessous décrit le travail initial de conception ; elle ne décrit pas le moteur effectivement assemblé.

Mission 01, branche locale : décision de conception Focus **Textual / Python**, à intégrer et valider avant remplacement du parcours actuel. La mission du propriétaire autorise explicitement ce choix pour Focus ; elle ne constitue pas une publication ni une migration déjà effectuée. Le prototype distribué reste Python standard, CLI par défaut et `--tui` curses facultatif. Aucun framework n'est installé dans ce socle, aucune seconde interface principale n'est créée. La décision historique sur le prototype ne devient pas rétroactivement une recette Focus. `DECISIONS.md` reste privé et n'est pas publié ; l'intégrateur devra y consigner la portée de cette décision avant intégration, sans écraser les travaux concurrents.

### Comparaison technique

Appréciations de conception, pas mesures comparatives ; les performances, lecteurs d'écran et terminaux réels exigent les recettes ci-dessous. Tous nécessitent des essais Unicode (graphemes, largeur, caractères combinants), redimensionnement et saisie multiligne.

| Option | Rendu, saisie et boucle | Intégration, streaming, accessibilité et coût |
|---|---|---|
| **Textual** | Widgets, disposition, focus/clavier et événements ; resize par l'application ; rendu Rich. | Python et workers asynchrones ou threads permettent d'encapsuler le moteur existant ; dépendance à emballer hors ligne. Contraste et clavier configurables ; lecteur d'écran non présumé. Meilleur compromis pour Focus. |
| prompt_toolkit + Rich | Édition, bindings et plein écran, rendu Rich séparé ; davantage de composition manuelle. | Python/asyncio directs ; stream à organiser ; plus de colle UI. Accessibilité et Unicode à mesurer comme pour Textual. |
| Ratatui | Rust, rendu terminal structuré et gestion explicite des événements ; contrôle fin et potentiellement rapide. | Pont de processus ou réécriture du moteur Python, protocole et packaging supplémentaires ; async et édition à assembler ; accessibilité à tester. |
| Bubble Tea | Go, modèle/événements, rendu par cellules, composants de saisie et resize. | Excellent candidat natif mais pont Go/Python, distribution multi-architecture et annulation interprocessus supplémentaires ; accessibilité à tester. |
| Ink | React/Node et rendu flex, événements clavier et saisie par composants. | Runtime Node et IPC Python requis ; streaming et redimensionnement à câbler ; comportement Unicode et accessibilité à tester. |
| OpenTUI | Framework TypeScript avec moteur natif ; composition et saisie selon composants. | Runtime et binaire natif supplémentaires, IPC et packaging Kali à qualifier ; maturité, compatibilité et accessibilité à mesurer. |
| Hybride natif + Python | Une seule TUI native, moteur Python séparé. | Permet Rust/Go sans réécriture métier mais introduit sérialisation, cycle de vie, erreurs et sécurité IPC ; coût non justifié à ce stade. |

Sources primaires : [Textual saisie](https://textual.textualize.io/guide/input/), [workers](https://textual.textualize.io/guide/workers/), [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html), [Ratatui événements](https://ratatui.rs/concepts/event-handling/), [Bubble Tea](https://github.com/charmbracelet/bubbletea), [Ink](https://github.com/vadimdemedes/ink), [OpenTUI](https://github.com/anomalyco/opentui). La documentation décrit les mécanismes, elle ne prouve pas nos budgets ni l'accessibilité de notre application.

## État actuel vérifié et cible

`install.sh` appelle `installation.py` ; lanceur utilisateur et paquet Debian lancent `src/uchambuzi.py`. `main()` choisit actions, CLI interactive et `--tui` ; la TUI curses pilote une CLI enfant par PTY. `conversation.Session` conserve les tours et utilise `OllamaRuntime` ou `ProviderManager` ; `OllamaRuntime.chat` demande `stream: false`, vérifie la fin et interdit les appels d'outils. `parcours.py`, `indices_outils.py`, `commandes.py` et `documentation_locale.py` fournissent les fonctions métier ; `installation.py` gère préférences, chemins et installation. Tests : `python3 -m unittest discover -s tests` ou `python3 -m pytest` si disponible. Python >= 3.10 ; aucune dépendance pip requise actuellement.

Cible unique : `uchambuzi` → composition/CLI non interactive → application Textual sur TTY → contrôleur conversation asynchrone → ports `focus_contracts` → adaptateurs du moteur, profils, scénarios, outils et stockage. La vue reçoit des événements, jamais un accès direct au runtime ou aux données. Actions non interactives restent accessibles ; prévoir un mode texte accessible et le comportement non-TTY. À la bascule, remplacer le parcours interactif existant, ne pas lancer l'ancienne CLI en sous-processus dans Textual. Conserver les commandes et alias existants. L'intégration effective du lanceur et du packaging est une étape ultérieure, pas une fonctionnalité déjà livrée.

Les sessions, paramètres, profils et scénarios passent par des ports ; toute persistance réelle doit réutiliser les chemins et garanties existants, migrer explicitement les données et ne rien écraser. Aucune base, schéma de disque, partage de mémoire ou politique de rétention n'est imposé ici. Le modèle actif figure dans les paramètres de la session. Le service d'outils prépare seulement : pas d'exécution automatique. Consentement distinct et explicite avant toute transmission distante ; pas de décision IA assimilée à une confirmation humaine.

## Contrats et cycle de vie

`src/focus_contracts.py` est l'unique source de vérité Python v1. Identifiants non vides et uniques sont à créer par l'orchestrateur ; ils sont opaques et ne doivent pas contenir de données sensibles. `Message` est destiné à l'affichage conversationnel (user/assistant), jamais à injecter des rôles système. Les paramètres et snapshots sont des valeurs en mémoire ; leurs annotations ne valident pas des données non fiables, chaque adaptateur doit valider ses entrées et copier les mappings mutables aux frontières. Les permissions ne sont pas des capacités d'exécution : `ConfirmationRequest` et `ConfirmationDecision` identifient l'action précise ; l'orchestrateur doit vérifier la correspondance, appliquer les politiques, refuser par défaut et empêcher la réutilisation d'une décision. `approved_for` vérifie seulement identité et accord, pas expiration, unicité ni politique. Aucun secret dans les contrats ou journaux.

Pour un tour accepté, l'ordre normal est `TurnStarted`, zéro ou plusieurs `TextDelta` ordonnés, puis exactement un `TurnFinished` (`complete` ou `failed`). Les deltas sont du texte brut non fiable ; filtrer les contrôles avant affichage. Un seul producteur par tour, corrélation par `turn_id`, pas de mélange de fragments. À l'échec, les fragments sont partiels, clairement indiqués et non enregistrés comme réponse complète. L'annulation est propagée par `asyncio.CancelledError` ; le consommateur marque le tour annulé, sans attendre un événement final du générateur. Une implémentation native doit fermer ses ressources, empêcher toute mutation tardive et définir si l'annulation serveur est effective.

`focus_legacy_adapter.LegacyConversation` illustre le branchement réel à `conversation.Session` : `asyncio.to_thread`, verrou par adaptateur, un delta après réponse complète. Il conserve les protections de `Session`, pas de streaming réseau. À l'annulation il attend la fin du thread avant de relâcher son verrou ; **le tour peut avoir été enregistré dans la session historique même si le consommateur a annulé**. Ne pas le présenter comme annulation effective ni partager une même session entre plusieurs adaptateurs. Une vraie annulation exige un nouveau contrat de session transactionnel et un runtime approprié. Les exceptions internes sont masquées ; aucun retry automatique. `tests/test_focus_contracts.py` démontre intégration et échec sans réseau.

## Frontières exclusives proposées pour les missions 02 à 12

Ces lots sont des affectations de fichiers, à confirmer contre les consignes propres à chaque mission ; ils ne supposent pas leur contenu. Un propriétaire par chemin, aucun agent ne modifie les contrats communs ou les fichiers d'un autre. Un changement de contrat passe par une demande à l'intégrateur et tests de compatibilité. Les nouveaux fichiers doivent porter l'en-tête projet. Les tests propres à chaque lot suivent le préfixe indiqué.

| Mission | Responsabilité et chemins exclusifs proposés |
|---|---|
| 02 | Coquille et navigation TUI : `src/focus_ui.py`, `tests/test_focus_ui*.py` |
| 03 | Saisie et édition : `src/focus_editor.py`, `tests/test_focus_editor*.py` |
| 04 | Vue conversation et rendu des fragments : `src/focus_view.py`, `tests/test_focus_view*.py` |
| 05 | Adaptateurs IA et streaming réel : `src/focus_engine.py`, `tests/test_focus_engine*.py` |
| 06 | Profils : `src/focus_profiles.py`, `tests/test_focus_profiles*.py` |
| 07 | Scénarios : `src/focus_scenarios.py`, `tests/test_focus_scenarios*.py` |
| 08 | Outils et préparation : `src/focus_tools.py`, `tests/test_focus_tools*.py` |
| 09 | Permissions et confirmations : `src/focus_permissions.py`, `tests/test_focus_permissions*.py` |
| 10 | Sessions et stockage : `src/focus_storage.py`, `tests/test_focus_storage*.py` |
| 11 | Configuration : `src/focus_settings.py`, `tests/test_focus_settings*.py` |
| 12 | Assemblage, lancement, packaging et recette : `src/focus_app.py`, `src/uchambuzi.py`, `src/installation.py`, `debian/`, `tests/test_focus_integration*.py` |

L'intégrateur seul maintient `focus_contracts.py`, `focus_legacy_adapter.py`, leurs tests et ce document ; les modules historiques restent inchangés sauf intégration coordonnée. Les chemins réservés sont indicatifs et n'autorisent pas d'implémenter une mission différente de celle assignée. Chaque branche part du commit de contrats livré, sans modifier `dev` ; échanger les commits avec l'intégrateur et intégrer séquentiellement après revue, jamais par copie divergente des contrats.

## Compatibilité et budgets de recette

Cibles à vérifier : Kali et Ubuntu, terminal UTF-8 local et SSH, tmux, tailles 80×24 et 40×12, agrandissements/réductions répétés, `TERM=dumb`, absence de TTY et `NO_COLOR`. Vérifier accents, CJK, combinants, emoji, collage multiligne, navigation intégralement clavier, focus visible, contraste sans couleur et restauration du terminal après erreur/Ctrl-C. Tester lecteur d'écran avec utilisateur concerné ; aucune compatibilité annoncée avant observation. Les terminaux trop petits doivent présenter un message utilisable, sans perdre de saisie. Aucune séquence de contrôle provenant d'un modèle ou outil ne doit être exécutée par le terminal.

Budgets **cibles**, non mesurés : sur machine de référence à définir, p95 traitement d'une touche vers rendu ≤ 50 ms ; p95 resize ≤ 100 ms ; regroupement de fragments au plus toutes les 33 ms, sans perte ni réordonnancement ; pas plus de 30 rendus/s en streaming ; mémoire de l'historique bornée et documentée. Mesurer avec horloge monotone, au moins 1000 frappes/fragments et 100 resize, rapporter p50/p95/p99, taille de session, machine et terminal. Le réseau et l'inférence sont mesurés séparément. Ne pas bloquer la boucle UI pendant I/O ; file bornée avec contre-pression, sans jeter de texte ; définir fermeture et annulation pour chaque fournisseur.

Erreurs : codes stables, message utilisateur sûr, origine conservée localement sans contenu sensible ; aucune réponse incomplète enregistrée comme complète. Journalisation structurée, niveau INFO par défaut, identifiants opaques, durée et code seulement ; ni prompts, réponses, arguments d'outils, secrets ni preuves par défaut. Ne jamais écrire sur stdout pendant la TUI ; stockage des logs et activation du diagnostic explicitement configurés, permissions restrictives, rotation et rétention à spécifier avant mise en service.

## Intégration

1. Faire partir chaque branche de ce commit, appliquer exclusivement sa frontière ; tester ses adaptateurs avec des faux composants conformes au contrat.
2. L'intégrateur sélectionne une version Textual compatible Python/Kali, vérifie licence et dépendances transitives, prépare installation hors ligne et paquet Debian reproductibles ; ne pas introduire de téléchargement implicite.
3. Implémenter un contrôleur qui sérialise les tours et confirmations, adapte les modules existants, gère timeout et fermeture, puis remplace le parcours interactif sous `uchambuzi` ; conserver diagnostics et options non interactives.
4. Tester contrats, sécurité, non-régression, installation/mise à jour/désinstallation et sessions réelles ; recette terminal et mesures ci-dessus sur Kali et SSH. Tester le runtime local réel séparément des simulations et documenter les limites.
5. Revue coordonnée des changements, mise à jour des décisions privées selon le processus, intégration locale uniquement après autorisation distincte. Aucune publication dans cette mission.
