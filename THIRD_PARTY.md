# Composants tiers — candidate privée UCHAMBUZI 2.0.0

Le code UCHAMBUZI est sous GPL-3.0-or-later. Les composants tiers conservent
leurs licences propres. Le catalogue n'accorde aucun droit supplémentaire.
Les paquets Kali sont des dépendances système distinctes, installées et mises à
jour via Kali ; leurs notices se trouvent dans `/usr/share/doc/<paquet>/copyright`.
Les déclarations ci-dessous sont celles du catalogue et des copies conservées.

## Copies embarquées

La table décrit les douze copies de la candidate privée 2.0.0, non publiée ; la version publique 1.0.0 en contient six.

| Outil | Version/révision | Licence déclarée | Notice conservée |
| --- | --- | --- | --- |
| [maigret](https://github.com/soxoj/maigret) | 0.6.6-21577cf | MIT | [Texte local](vendor/maigret/LICENSE) |
| [holehe](https://github.com/megadose/holehe) | 1.61-14da70f-r1 | GPL-3.0 | [Texte local](vendor/holehe/LICENSE.md) |
| [phoneinfoga](https://github.com/sundowndev/phoneinfoga) | 2.11.0 | GPL-3.0 | [Texte local](vendor/phoneinfoga/LICENSE) |
| [gau](https://github.com/lc/gau) | 4eabace | MIT | [Texte local](vendor/gau/LICENSE) |
| [social-analyzer](https://github.com/qeeqbox/social-analyzer) | 0.45-c585f42-r1 | AGPL-3.0 | [Texte local](vendor/social-analyzer/LICENSE) |
| [blackbird](https://github.com/p1ngul1n0/blackbird) | 471ef970 | GPL-3.0 | [Texte local](vendor/blackbird/docs/LICENSE) |
| [subfinder](https://github.com/projectdiscovery/subfinder) | 2.17.0 | MIT | [Texte local](vendor/subfinder/LICENSE.md) |
| [httpx](https://github.com/projectdiscovery/httpx) | 1.12.0 | MIT | [Texte local](vendor/httpx/LICENSE.md) |
| [dnsx](https://github.com/projectdiscovery/dnsx) | 1.3.1 | MIT | [Texte local](vendor/dnsx/LICENSE.md) |
| [photon](https://github.com/s0md3v/Photon) | 1.3.0-r1 | GPL-3.0 | [Texte local](vendor/photon/LICENSE) |
| [trufflehog](https://github.com/trufflesecurity/trufflehog) | 3.99.8 | AGPL-3.0 | [Texte local](vendor/trufflehog/LICENSE) |
| [gitleaks](https://github.com/gitleaks/gitleaks) | 8.30.1 | MIT | [Texte local](vendor/gitleaks/LICENSE) |

Les auteurs et contributeurs sont ceux des notices et historiques amont conservés.
Les révisions et transformations locales sont décrites dans
[vendor/README.uchambuzi.md](vendor/README.uchambuzi.md). Les licences GPL et AGPL
des outils restent applicables à leurs copies ; elles ne sont pas remplacées par
la licence du lanceur. Les sources de PhoneInfoga **v2.11.0** sont conservées dans
l'archive source correspondante, issue du tag amont (commit
`5f6156f567613a07ea8e3f04b004864582060a57`), séparément de l'ancien arbre de sources.
Les sources, archives et notices des autres outils restent dans leurs répertoires
`vendor/<outil>/`. Les sources du tag TruffleHog sont incluses ; la complétude
des sources et notices de ses dépendances Go doit encore être vérifiée avant
une publication. La présente recette ne publie aucun paquet.

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

Une entrée du catalogue ne signifie pas qu'un paquet tiers est embarqué.
Les copies distribuées doivent disposer d'une licence identifiée.

La table Unicode dérivée de `src/focus_view.py` conserve sa notice Unicode 3.0
également reproduite dans les métadonnées `debian/copyright` du paquet Debian
(et dans les sources privées de construction). Les dépendances
Textual, Rich et Prompt Toolkit restent des paquets système séparés.
