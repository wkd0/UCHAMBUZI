# maigret — référence locale

Description : Recherche de profils publics correspondant à un pseudonyme.

Options passives / bornage : Aucun mode passif hors-ligne de recherche. --no-recursion borne les recherches ; --timeout 10 règle le délai. Ces options ne rendent pas les requêtes passives.

Options actives : Le pseudonyme positionnel déclenche des requêtes HTTP vers les sites : actif, accord requis. --top-sites 50 borne le nombre de sites.

Syntaxe et exemple typique : `maigret example_user --top-sites 50 --timeout 10 --no-recursion`

Toute opération réseau nécessite approbation [o/N]. Présence et version installées à vérifier ; cette fiche ne prouve pas leur disponibilité.
Source : https://maigret.readthedocs.io/en/latest/command-line-options.html
Vérification documentaire : 2026-11-10 (synthèse, pas aide de la version installée).
