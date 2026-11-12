# Assist et sélection des Teams

Chaque lancement commence en **Assist**, même lorsqu'une ancienne configuration
contient un autre `active_team`. Les réglages du modèle IA restent conservés.

`/team` ouvre cinq choix :

| Touche | Profil | Comportement |
| --- | --- | --- |
| 0 | Assist | Pédagogie générale et dialogue IA sans outils ni playbooks |
| 1 | OSINT Team | Investigation après sélection explicite |
| 2 | Red Team | Réponse locale « en développement » |
| 3 | Blue Team | Réponse locale « en développement » |
| 4 | Purple Team | Réponse locale « en développement » |

Les flèches et Entrée permettent aussi de choisir ; Échap annule. Les arguments
directs restent disponibles, par exemple `/team 0`, `/team assist`, `/team 1`
et `/team osint`. Le badge `✓ ACTIF` identifie le profil courant.

En Assist, un domaine, une adresse IP ou une URL reste une question pour l'IA.
Les commandes d'investigation invitent à sélectionner `/team 1`. Le retour à
Assist retire le contexte d'enquête du dialogue et vide les exécutions et pivots
en attente. Red, Blue et Purple répondent localement au texte libre, sans appel
à Ollama ; les commandes locales de navigation et d’aide restent accessibles.

Au premier passage en OSINT, le panneau **Cadre légal OSINT** apparaît avant
l'**Approbation [o/N]**. Cet accusé de lecture est facultatif et distinct de
l'autorisation d'exécuter chaque commande. Entrée refuse l'accusé de lecture ;
`o` puis Entrée l'enregistre localement pour cette version du texte. Le panneau
Rich natif est recalculé par Textual lors des redimensionnements.

Vérification sur Kali :

```sh
uchambuzi
# /team → 1 → lire le cadre légal → o ou Entrée
# /team → 0 → retour Assist
# /team → 2, 3 ou 4 → saisir un domaine : réponse locale
python3 -m unittest discover tests
```
