# Composants tiers — UCHAMBUZI 1.0.0

Le code UCHAMBUZI est sous GPL-3.0-or-later. Les composants tiers conservent
leurs licences propres. Le catalogue n'accorde aucun droit supplémentaire.
Les paquets Kali sont des dépendances système distinctes, installées et mises à
jour via Kali ; leurs notices se trouvent dans `/usr/share/doc/<paquet>/copyright`.
Les déclarations ci-dessous sont celles du catalogue et des copies conservées.

## Copies embarquées

| Outil | Version/révision | Licence déclarée | Notice conservée |
| --- | --- | --- | --- |
| [maigret](https://github.com/soxoj/maigret) | 0.6.6-21577cf | MIT | [Texte local](vendor/maigret/LICENSE) |
| [holehe](https://github.com/megadose/holehe) | 1.61-14da70f | GPL-3.0 | [Texte local](vendor/holehe/LICENSE.md) |
| [phoneinfoga](https://github.com/sundowndev/phoneinfoga) | 2.11.0 | GPL-3.0 | [Texte local](vendor/phoneinfoga/LICENSE) |
| [gau](https://github.com/lc/gau) | 4eabace | MIT | [Texte local](vendor/gau/LICENSE) |
| [social-analyzer](https://github.com/qeeqbox/social-analyzer) | 0.45-c585f42 | AGPL-3.0 | [Texte local](vendor/social-analyzer/LICENSE) |
| [blackbird](https://github.com/p1ngul1n0/blackbird) | 471ef970 | GPL-3.0 | [Texte local](vendor/blackbird/docs/LICENSE) |

Les auteurs et contributeurs sont ceux des notices et historiques amont conservés.
Les révisions et transformations locales sont décrites dans
[vendor/README.uchambuzi.md](vendor/README.uchambuzi.md). Les licences GPL et AGPL
des outils restent applicables à leurs copies ; elles ne sont pas remplacées par
la licence du lanceur. Les sources de PhoneInfoga **v2.11.0** sont conservées dans
l'archive source correspondante, issue du tag amont (commit
`5f6156f567613a07ea8e3f04b004864582060a57`), séparément de l'ancien arbre de sources.
Les sources des autres outils restent dans leurs répertoires `vendor/<outil>/`.

Les bundles Python contiennent les wheels des outils et de leurs dépendances,
avec leurs notices originales. L'[inventaire des dépendances](vendor/DEPENDENCIES.json)
identifie chaque wheel et les licences déclarées dans ses métadonnées.
Les binaires Go dépendent également des modules référencés par les `go.mod` et
`go.sum` amont conservés. L'empreinte SHA-256 assure la correspondance avec le
catalogue ; elle ne signe pas la provenance et n'établit pas à elle seule la
conformité juridique d'une redistribution. Cette page ne prétend pas être un
audit juridique complet ni un audit de vulnérabilités.

## WhatsMyName

Le moteur natif [src/osint_wmn.py](src/osint_wmn.py) est du code UCHAMBUZI sous
GPL-3.0-or-later. Le [jeu de données](data/tools/wmn-data.json) du projet
[WhatsMyName](https://github.com/WebBreacher/WhatsMyName), porté par WebBreacher
et ses contributeurs, conserve sa [licence CC BY-SA 4.0](data/tools/wmn-LICENSE.md).
Révision documentée : `abcb19d6809f0e963e353819c571133b45b6a106`.
Le catalogue représente cette combinaison par
`GPL-3.0-or-later AND CC-BY-SA-4.0` ; les deux composants restent distincts.

## Composants non distribués et références

Waybackurls n'est pas distribué : licence non déclarée (`NOASSERTION`) et
installation bloquée. Subfinder, httpx, dnsx, photon, trufflehog et gitleaks sont
des entrées déclaratives sans artefact approuvé livré. Une entrée du catalogue
ne signifie pas qu'un paquet tiers est embarqué.

La table Unicode dérivée de `src/focus_view.py` conserve sa notice Unicode 3.0
également reproduite dans [debian/copyright](debian/copyright). Les dépendances
Textual, Rich et Prompt Toolkit restent des paquets système séparés.
