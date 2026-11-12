# phoneinfoga — référence locale

Description : Analyse de numéros internationaux par scanners configurés.

Options passives / bornage : --help et scan --help : aide locale. Aucun mode global garantissant une recherche réseau passive ou sans clé.

Options actives : scan -n NUMERO lance les scanners disponibles ; -D/--disable désactive un scanner. Certains exigent une clé : les exclure. Ne pas inventer -s google.

Syntaxe et exemple typique : `phoneinfoga scan -n +12025550123`

Toute opération réseau nécessite approbation [o/N]. Présence et version installées à vérifier ; cette fiche ne prouve pas leur disponibilité.
Source : https://github.com/sundowndev/phoneinfoga
Vérification documentaire : 2026-11-10 (synthèse, pas aide de la version installée).
