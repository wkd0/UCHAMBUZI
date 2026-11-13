# WhatsMyName et Blackbird

## Moteur natif

`src/osint_wmn.py` expose `check_username(username, limit=50)` et
`await check_username_async(username, limit=50)`. Bibliothèque standard uniquement,
10 requêtes simultanées au maximum, délai socket de 8 secondes, corps limité à
2 Mio, HTTPS public uniquement, aucune redirection suivie. Dans le code courant,
le raccourci `/pseudo` appelle ce moteur après avoir affiché le niveau **actif** et
obtenu l'accord `[o/N]`. Les résultats sont ajoutés au dossier si un cas est
actif. La portée des vérifications du candidat figure dans la [note V1](releases/1.0.0.md).

Les règles GET HTTPS sont prises en charge ; les règles POST, HTTP et désactivées
sont exclues avant application de la limite. `exists=False` avec `error` signifie
**indéterminé**, pas absence confirmée. Même un positif nécessite confirmation.
L'API synchrone refuse une boucle asyncio déjà active ; utiliser alors l'API async.
Le délai DNS dépend du résolveur système et n'est pas borné par le délai socket.

Base officielle : https://github.com/WebBreacher/WhatsMyName
Révision : `abcb19d6809f0e963e353819c571133b45b6a106`.
Base non modifiée, licence CC BY-SA 4.0 conservée dans `data/tools/wmn-LICENSE.md`.
Le dépôt amont est archivé depuis le 9 novembre 2026.

## Blackbird

Source : https://github.com/p1ngul1n0/blackbird (redirige vers antoniaci/blackbird).
Révision : `471ef970b4cd45378de1270c1b2b06687aa158b7`.
Licence GPLv3 conservée dans `vendor/blackbird/docs/LICENSE` ; la licence de
`.github/LICENSE` concerne ce sous-répertoire. Aucun `.git` imbriqué.
Le fichier `.env` amont contient uniquement des paramètres de service ; il n'est
pas distribué, et le bundle fournit un `.env` vide.

Le ZIP contient les sources et les 21 wheels de dépendances figées dans
`requirements.txt`, téléchargés sur Kali, Python 3.13 / Linux x86_64.
L'installation crée un venv et emploie exclusivement `--no-index --find-links`.
Le lanceur impose `--no-update` et refuse les options IA avec clé, y compris
leurs formes abrégées. L'outil reste une opération réseau active ; aucun scan
Blackbird n'est lancé durant la recette. L'installation ne nécessite aucune clé.
Les sources amont conservées contiennent encore les fonctions IA facultatives ;
le lancement direct du script tiers contourne les restrictions du lanceur.

## Recette Kali actuelle

Depuis une copie à jour du candidat sur Kali :

```sh
UCHAMBUZI_TEST_BLACKBIRD=1 python3 -m unittest discover -s tests -p test_blackbird_offline.py
UCHAMBUZI_TEST_VENDOR=1 python3 -m unittest discover -s tests -p test_vendor_acceptance.py
```

Ces recettes isolent leurs données et nettoient leurs installations. La seconde
installe les copies distribuées avec l'interface Textual (douze sur la branche
de développement, six dans la version publique 1.0.0), vérifie leurs aides et leurs
dépendances, refuse les recherches réseau et exécute les étapes PhoneInfoga
locales. La [note V1](releases/1.0.0.md) distingue les résultats du candidat des
contrôles réseau anciens. Les recherches sur les sites Internet doivent toujours
être recoupées et sont soumises à approbation.

Le lanceur Blackbird utilise `--username`, impose `--no-update` et travaille sur
une copie temporaire sous `tools/.runtime/`. Ses logs ne modifient plus le
manifeste installé ; la copie est supprimée à la sortie normale. Les sorties
consignées par UCHAMBUZI restent dans le dossier d'enquête actif.
