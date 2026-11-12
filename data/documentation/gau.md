# gau — référence locale

Description : Collecte des URL connues par les archives et fournisseurs tiers.

Options passives / bornage : Passif envers la cible : --providers wayback,commoncrawl ; --subs inclut les sous-domaines ; --timeout 15 borne chaque requête. Aucune option --silent ni -silent : elles sont invalides.

Options actives : Aucun mode de scan actif de la cible ; interroge néanmoins des services tiers sur le réseau.

Syntaxe et exemple typique : `gau --providers wayback,commoncrawl --subs example.org`

Toute opération réseau nécessite approbation [o/N]. Présence et version installées à vérifier ; cette fiche ne prouve pas leur disponibilité.
Source : https://github.com/lc/gau
Vérification documentaire : 2026-11-10 (synthèse, pas aide de la version installée).
