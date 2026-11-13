# Amass v5.1.3 — référence locale Kali

Présence du binaire et version ne prouvent pas la disponibilité du moteur ou de sa base. Le lanceur Kali exige les données libpostal ; si elles manquent, il tente un téléchargement privilégié. UCHAMBUZI ne le déclenche pas.

Aides locales vérifiées : `amass -h`, `amass engine -h`, `amass subs -h`. Version : `amass -version`, après vérification des données libpostal.

Attention : `amass enum -h` démarre le moteur AVANT de lire -h, masque ses erreurs et attend jusqu’à 60 s sa réponse sur http://127.0.0.1:4000. Le moteur initialise obligatoirement BGP.Tools par DNS ; hors réseau il échoue même sans cible. Ne pas utiliser enum -h comme sonde automatique. Un PostgreSQL seul ne corrige pas cette dépendance réseau. Aucun démarrage moteur sans approbation réseau.

Parcours local vérifié sans moteur : `amass subs -config CONFIG_LOCALE -dir DOSSIER_BASE -d example.test -names -nocolor`. CONFIG_LOCALE est un YAML dédié contenant `scope: {}` et `options: {}` sur deux lignes. DOSSIER_BASE est un dossier dédié contenant asset.db (SQLite). Cela relit des noms déjà acquis ; cela ne collecte rien. Une base vide affiche « No names were discovered ». Ne pas omettre la configuration dédiée ni réutiliser une base utilisateur pour un essai : ouverture et migrations peuvent écrire.

L’énumération utilise `amass enum -d DOMAINE` après qualification du moteur, de la base et des sources sans compte/clé, avec approbation réseau explicite. `-passive` est déprécié en v5.1.3. Aucun parcours accompagné Amass dans UCHAMBUZI.

Procédure et sources primaires : docs/amass-v5.md. Source : https://github.com/owasp-amass/amass/tree/v5.1.3 ; README.Debian et ressources du paquet Kali 5.1.3-0kali1. Vérification Kali : 2026-11-12, réseau désactivé ; aucune collecte qualifiée.
