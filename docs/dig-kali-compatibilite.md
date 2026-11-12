# Préparation de la prise en charge documentaire de dig Kali

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

La référence locale [dig-kali.md](../data/documentation/dig-kali.md) décrit la
comparaison argument par argument, les prérequis et les limites. Cette livraison
ajoute uniquement la reconnaissance documentaire de `9.20.11-4+b1-Debian` et du
bandeau `DiG 9.20.11-4+b1-Debian`. Les autres révisions restent non vérifiées.
Le manuel Ubuntu `9.20.24-1ubuntu0.5-Ubuntu` garde sa propre référence et sa portée.

## Preuves locales examinées

Le 7 novembre 2026, lecture via SSH de la VM Kali Rolling 2025.3, sans Internet :

- `dpkg-query -W bind9-dnsutils file` : `1:9.20.11-4+b1` et `1:5.46-5`.
- `dpkg-query -S` : attribution des manuels aux deux paquets correspondants.
- `dig -v` : `DiG 9.20.11-4+b1-Debian`; `file --version` : `file-5.46`.
- `dig(1)` : auteur ISC, en-tête du 4 juillet 2025; métadonnées de copyright
  du paquet consultées. Aucune signature de paquet revérifiée.
- SHA-256 dig compressé : `faaf11b7648a35d0df5b2fb87d0e4c7889e6a1e25e70b2f6037a1020097815c4`;
  décompressé : `aa73b2dd16e0f0e0701645dd181729d320dffe6eee62281a1fafd85e4032236e`.
- SHA-256 file compressé : `7cef83cc744a8af5342336922d90ad0fdc3f103422b74f1a1475739090db8104`;
  décompressé : `5b537184dabc1813252c5ca2c81ad9386b056e53daeb23306eee99dfae1b1fa5`.
  Ces deux empreintes correspondent au manuel Ubuntu déjà lu.

Les copies de manuels reçues via SSH sont des ressources locales préexistantes,
pas des téléchargements Internet. Seules des notes originales sont incluses dans
le corpus Git; aucun manuel tiers intégral n'est redistribué. Les liens Web sont
des références non consultées, pas des preuves de leur contenu actuel.

## Catalogue et contrats

L'extension optionnelle `sources_by_version` des fiches associe des chaînes de
version exactes à des listes de sources. La sélection s'effectue sans rapprochement
approximatif. Dans une même liste, toutes les sources restent requises, comme pour
le champ historique `sources`. Sans correspondance exacte, `sources` reste utilisé;
la compatibilité reste inconnue/non vérifiée si son motif ne correspond pas.

Le champ `source_selection` précise `exact_version` ou `default`. Une source Kali
sélectionnée mais absente, altérée ou périmée force `needs_review` : aucun repli
silencieux sur le manuel Ubuntu n'a lieu. Les identifiants historiques
`dig-manual` et `file-manual` gardent leur sens. `dig-kali-manual` est distinct.
`Corpus.reference('dig-manual', version_kali)` reste non vérifié.

Les explications distinguent question DNS d'un domaine, recherche inverse PTR,
extraction humaine de domaine d'e-mail et extraction humaine d'hôte d'URL. Le
nouveau champ descriptif `target_transformation` ne contient pas de valeur cible :
il indique l'action, la sélection humaine requise, les types de sortie possibles
et `automatic=false`. Il ne modifie pas les indices ni le préparateur. Pour une
URL contenant une IP, le nouvel indice peut être `ip`; aucun PTR n'est choisi
silencieusement. Le choix du résolveur et du type DNS appartient à l'utilisateur.

Les signatures publiques, les champs historiques et l'algorithme `digest` sont
conservés. Le changement de corpus ou de proposition modifie leurs empreintes;
les revues anciennes restent inchangées et peuvent devenir potentiellement
obsolètes. `documented_basis` est une base documentaire seulement :
`command_status=not_prepared`, `execution_authorized=false` restent explicites.

## Adaptation réalisée dans la copie intégrée

Le préparateur accepte désormais le bandeau exact `DiG 9.20.11-4+b1-Debian`,
avec la provenance et le SHA-256 du manuel Kali. La règle Ubuntu est conservée.
Aucune plage de versions n’est ouverte. Les tests couvrent les types A/AAAA/MX/TXT,
les PTR IPv4/IPv6, les versions proches refusées, les périmètres et les sources
manquantes, altérées ou périmées. La préparation demeure sans exécuteur.
La note syntaxique et son empreinte sont actualisées conjointement. Une revue
humaine de documentation n’accorde jamais d’autorisation d’exécution.

## Tests reproductibles sans Internet

Depuis ce worktree, les tests documentaires n'ont besoin d'aucun accès Kali :

```bash
python3 -m unittest discover -s tests -v
```

Pour activer aussi les tests réels de contrats Kali avec le préparateur existant,
indiquer explicitement les racines locales des producteurs :

```bash
UCHAMBUZI_AGENT2_ROOT=/chemin/agent2 \
UCHAMBUZI_AGENT4_ROOT=/chemin/agent4 \
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
```

Sans ces variables, les modules de la copie intégrée sont utilisés. Aucune modification automatique du moteur ni accès
SSH n'est effectué par les tests. Les inventaires utilisés sont fictifs.
