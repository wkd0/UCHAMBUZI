# subfinder — référence locale

Description : Enumération de sous-domaines depuis des sources tierces.

Options passives / bornage : Passif envers la cible : -d DOMAINE -silent ; -s crtsh limite à une source sans clé. -silent règle seulement la sortie.

Options actives : -active (alias -nW) active la résolution DNS ; -oI nécessite -active. Ne pas ajouter ces options pour une demande passive.

Syntaxe et exemple typique : `subfinder -d example.org -s crtsh -silent`

Toute opération réseau nécessite approbation [o/N]. Présence et version installées à vérifier ; cette fiche ne prouve pas leur disponibilité.
Source : https://github.com/projectdiscovery/subfinder
Vérification documentaire : 2026-11-10 (synthèse, pas aide de la version installée).
