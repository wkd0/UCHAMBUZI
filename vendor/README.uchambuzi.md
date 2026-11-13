# Copies locales UCHAMBUZI

Sources des six copies installables conservées le 10 novembre 2026. Les répertoires `.git` imbriqués ont été retirés ; sources et licences amont conservées.

| Outil | Révision des sources | Artefact |
| --- | --- | --- |
| gau | 4eabace | Go 1.23.12, `go build -o bin/gau ./cmd/gau`, version annoncée 2.2.4 |
| phoneinfoga | v2.11.0, commit 5f6156f567613a07ea8e3f04b004864582060a57 | Binaire officiel 2.11.0 ; sources correspondantes dans `phoneinfoga/phoneinfoga-v2.11.0-source.tar.gz`. Le répertoire de travail historique 55807b0 reste distinct. |
| maigret | 21577cf | Wheel 0.6.6 construit depuis ces sources |
| holehe | 14da70f + correctif local r1 | Wheel 1.61 construit depuis ces sources, mise à jour implicite désactivée, import inutilisé de requests retiré |
| social-analyzer | c585f42 + correctif local r1 | Wheel 0.45 construit depuis ces sources, empaquetage et liste locale corrigés |
| blackbird | 471ef970 | Bundle Python 3.13 Linux x86_64 ; licence conservée dans `docs/LICENSE` |

Le miroir WhatsMyName a également été retiré ; le moteur utilise
les copies vérifiées de la base et de la licence dans `data/tools/`.

PhoneInfoga : https://github.com/sundowndev/phoneinfoga/releases/download/v2.11.0/phoneinfoga_Linux_x86_64.tar.gz

Les ZIP Python contiennent le wheel du projet et tous les wheels de ses dépendances, préparés sur Kali Linux x86_64 / Python 3.13. Ils ne garantissent pas une compatibilité avec un autre Python ou une autre architecture. Les licences des dépendances sont conservées dans les métadonnées des wheels. Les SHA-256 des artefacts distribués figurent dans `data/tools/catalog.json` ; `vendor/SHA256SUMS` inventorie aussi les sources et chaque wheel contenu dans les bundles est couvert par l'empreinte du ZIP.

Reconstruction sur Kali : créer un venv de construction avec setuptools, wheel et poetry-core ; exécuter `pip wheel --no-build-isolation --wheel-dir <wheelhouse> ./vendor/<outil>`, puis archiver les wheels à plat dans le ZIP. La préparation peut télécharger les dépendances ; l'installation utilisateur utilise exclusivement `pip --no-index --find-links` dans un nouveau venv isolé. Toute reconstruction impose de renouveler les empreintes du catalogue et de refaire la recette hors réseau.

Correctifs locaux : `holehe/core.py` n'appelle plus `check_update()` ; `social-analyzer/setup.py` installe `social_analyzer.app:main_logic` avec les fichiers `data/*`. Les fonctions d'investigation restent des opérations réseau soumises à l'approbation de l'enquêteur ; seule l'installation est entièrement hors ligne.

Holehe r1 retire l'import inutilisé de `requests` dans le module Facebook, qui
utilise déjà le client HTTPX partagé. Le bundle est reconstruit sans nouvelle
dépendance. La recette charge tous les modules installés sans réseau : `--help`
et `pip check` seuls ne détectaient pas cette erreur au démarrage d'une recherche.
Le pin `1.61-14da70f-r1` distingue cette copie de l'ancienne installation ; après
mise à jour d'UCHAMBUZI, préparer cette nouvelle copie avec `/tools install holehe`.

Social Analyzer r1 charge la base locale avant d'afficher `--list`, dans les
interfaces CLI et objet. Le pin `0.45-c585f42-r1` distingue le bundle corrigé ;
préparer cette copie avec `/tools install social-analyzer`. Les 26 wheels de
dépendances restent identiques octet pour octet. La liste valide la lecture de
la base embarquée, sans certifier la disponibilité des sites distants.

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

## Copies supplémentaires — recette du 12 novembre 2026

| Outil | Version figée | Source officielle et conditions |
| --- | --- | --- |
| subfinder | v2.17.0 | https://github.com/projectdiscovery/subfinder/releases/tag/v2.17.0 — MIT |
| httpx | v1.12.0 | https://github.com/projectdiscovery/httpx/releases/tag/v1.12.0 — MIT |
| dnsx | v1.3.1 | https://github.com/projectdiscovery/dnsx/releases/tag/v1.3.1 — MIT |
| gitleaks | v8.30.1 | https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1 — MIT |
| trufflehog | v3.99.8 | https://github.com/trufflesecurity/trufflehog/releases/tag/v3.99.8 — AGPL-3.0 ; sources correspondantes incluses |
| photon | v1.3.0, adaptation r1 | https://github.com/s0md3v/Photon/tree/v1.3.0 — GPL-3.0 ; sources originales et modifiées incluses |

Les archives officielles Linux ont été vérifiées avec les sommes publiées avec chaque release. Gitleaks et TruffleHog sont reconditionnés en ZIP à partir des fichiers des archives officielles tar.gz ; leur fichier de sommes officiel est conservé pour la traçabilité du téléchargement initial. Les ZIP ProjectDiscovery sont ceux de l'amont. Chaque empreinte distribuée est figée dans le catalogue. Les sources de TruffleHog correspondent au tag publié ; les sources des dépendances Go ne sont pas incluses dans cette archive et restent disponibles auprès de leurs auteurs.

Photon ne publie pas de wheel à ce tag : le bundle Python 3.13 comprend un wheel construit localement, ses dépendances et leurs notices. L'adaptation r1 ajoute le conditionnement et un point d'entrée, utilise le chemin du fichier de données relatif au module et désactive `--update`. Le code amont du tag v1.3.0 affiche encore `v1.2.2` dans sa bannière. Son installation et son exécution exigent Python 3.13.

La présence de ces copies ne prouve pas que les services réseau distants répondent, ni qu'un workflow guidé existe pour chaque outil.
