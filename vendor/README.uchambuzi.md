# Copies locales UCHAMBUZI

Sources des six copies installables conservées le 10 novembre 2026. Les répertoires `.git` imbriqués ont été retirés ; sources et licences amont conservées.

| Outil | Révision des sources | Artefact |
| --- | --- | --- |
| gau | 4eabace | Go 1.23.12, `go build -o bin/gau ./cmd/gau`, version annoncée 2.2.4 |
| phoneinfoga | v2.11.0, commit 5f6156f567613a07ea8e3f04b004864582060a57 | Binaire officiel 2.11.0 ; sources correspondantes dans `phoneinfoga/phoneinfoga-v2.11.0-source.tar.gz`. Le répertoire de travail historique 55807b0 reste distinct. |
| maigret | 21577cf | Wheel 0.6.6 construit depuis ces sources |
| holehe | 14da70f | Wheel 1.61 construit depuis ces sources, mise à jour implicite désactivée |
| social-analyzer | c585f42 | Wheel 0.45 construit depuis ces sources, empaquetage corrigé |
| blackbird | 471ef970 | Bundle Python 3.13 Linux x86_64 ; licence conservée dans `docs/LICENSE` |

La copie de waybackurls (révision `8d27cf3`) a été retirée de `vendor/` et des
paquets ; son installation reste bloquée dans le catalogue faute de licence
amont déclarée. Le miroir WhatsMyName a également été retiré ; le moteur utilise
les copies vérifiées de la base et de la licence dans `data/tools/`.

PhoneInfoga : https://github.com/sundowndev/phoneinfoga/releases/download/v2.11.0/phoneinfoga_Linux_x86_64.tar.gz

Les ZIP Python contiennent le wheel du projet et tous les wheels de ses dépendances, préparés sur Kali Linux x86_64 / Python 3.13. Ils ne garantissent pas une compatibilité avec un autre Python ou une autre architecture. Les licences des dépendances sont conservées dans les métadonnées des wheels. Les SHA-256 des artefacts distribués figurent dans `data/tools/catalog.json` ; `vendor/SHA256SUMS` inventorie aussi les sources et chaque wheel contenu dans les bundles est couvert par l'empreinte du ZIP.

Reconstruction sur Kali : créer un venv de construction avec setuptools, wheel et poetry-core ; exécuter `pip wheel --no-build-isolation --wheel-dir <wheelhouse> ./vendor/<outil>`, puis archiver les wheels à plat dans le ZIP. La préparation peut télécharger les dépendances ; l'installation utilisateur utilise exclusivement `pip --no-index --find-links` dans un nouveau venv isolé. Toute reconstruction impose de renouveler les empreintes du catalogue et de refaire la recette hors réseau.

Correctifs locaux : `holehe/core.py` n'appelle plus `check_update()` ; `social-analyzer/setup.py` installe `social_analyzer.app:main_logic` avec les fichiers `data/*`. Les fonctions d'investigation restent des opérations réseau soumises à l'approbation de l'enquêteur ; seule l'installation est entièrement hors ligne.

`/tools verify <nom>` contrôle l'artefact source. La résolution d'un exécutable installé vérifie également le manifeste de son installation. Les outils sont installés dans `~/.local/share/uchambuzi-data/tools/<nom>/<version>/`.

## Qualification V1.0.0 — 11 novembre 2026

Les bundles `cp313` sélectionnent explicitement Python 3.13 ; les paquets système
`python3.13` et `python3.13-venv` doivent être présents, même sur Kali avec Python
3.14 par défaut. Le paquet Debian les déclare comme dépendances. L'installation
utilisateur reste sans réseau grâce aux wheels déjà inclus.

Blackbird travaille dans une copie temporaire de son application sous
`tools/.runtime/`, supprimée à sa sortie normale, pour que ses logs et rapports
internes n'altèrent pas l'installation vérifiée. UCHAMBUZI conserve la sortie
consignée dans le dossier actif. Les rapports natifs tiers de cette copie de
travail ne constituent pas des exports persistants UCHAMBUZI.

[DEPENDENCIES.json](DEPENDENCIES.json) inventorie chaque wheel, ses métadonnées de
licence et ses fichiers de notices. Cet inventaire documentaire ne constitue pas
une garantie de compatibilité, d'absence de vulnérabilités ou de conformité
juridique de toutes les dépendances. Les notices originales restent dans les
wheels. Les contrôles exécutables et la portée de recette figurent dans la
[note V1](../docs/releases/1.0.0.md).
