# Amass v5.1.3 sur Kali

La version qualifiée ici est le paquet Kali `5.1.3-0kali1`. La fiche
`/tools amass` indique sa présence, les prérequis et ses limites. Amass conserve
sa syntaxe native via le shell ; aucun parcours accompagné ne lance son moteur.

## Pourquoi `enum -h` semble bloqué

Le lanceur Kali `/usr/bin/amass` vérifie les données libpostal dans
`/usr/share/libpostal/transliteration`. Si elles manquent, il appelle un
téléchargeur privilégié avant de traiter les arguments. La découverte UCHAMBUZI
signale cette dépendance sans lancer le téléchargeur.

Une fois les modèles disponibles, les commandes `amass -version`, `amass -h`,
`amass engine -h` et `amass subs -h` fonctionnent sans réseau.

En revanche, dans **v5.1.3**, `amass enum -h` cherche d’abord le moteur sur
`http://127.0.0.1:4000`, tente de le démarrer en arrière-plan et attend sa réponse
pendant 60 secondes avant de traiter les options d’énumération. Les sorties de
l’enfant sont supprimées. Ce délai vient du lanceur, pas du chargement libpostal.
Même `-engine` ou `-config` transmis à `enum` ne changent pas ce contrôle initial.

Le moteur charge ses plugins avant de démarrer l’API. BGP.Tools résout
obligatoirement `bgp.tools` par DNS à son initialisation. Sans réseau, le test
au premier plan échoue avec le code 1 :

```text
Failed to start the engine: failed to obtain the BGPTools IP address: failed the maximum number of DNS attempts
```

Un PostgreSQL configuré ne lève pas ce blocage initial. UCHAMBUZI ne démarre donc
pas le moteur pour vérifier sa disponibilité ou pour afficher une aide. La fiche
locale reste accessible sans cette opération réseau.

## Parcours local utilisable : relire une base

`subs` peut lire une base SQLite locale, sans moteur ni PostgreSQL. Ce mode
présente des données déjà acquises ; il ne découvre pas de nouveaux sous-domaines.
L’ouverture peut créer ou migrer la base : travailler sur une copie dédiée.

Exemple d’essai **sur Kali**, dans un nouveau dossier, sans configuration ni
variables Amass héritées :

```bash
work=$(mktemp -d "$HOME/amass-local.XXXXXX")
mkdir -p "$work/home" "$work/db"
printf 'scope: {}\noptions: {}\n' > "$work/local.yaml"
env -i HOME="$work/home" PATH=/usr/bin:/bin \
  /usr/bin/amass subs -config "$work/local.yaml" -dir "$work/db" \
  -d example.test -names -nocolor
```

Sur une base vide, le code est 0 et la sortie est `No names were discovered`.
Pour relire des résultats existants, placer une **copie cohérente** de la base
`asset.db` dans le dossier dédié et choisir le domaine déjà présent. Ne pas copier
à chaud un fichier SQLite en cours d’écriture sans sa sauvegarde appropriée.
La recette sur Kali, réseau désactivé, a relu exactement deux noms fictifs liés
par une relation `node`, et exclu un troisième nom hors périmètre. Ces données
ont été injectées localement dans une base de test, sans collecte.

Le YAML explicite et l’environnement vide évitent une connexion à une base
configurée ailleurs. Le dossier créé pour cet exemple peut ensuite être supprimé
après vérification de son contenu et de l’absence de processus l’utilisant.

## Avant une énumération réseau

La syntaxe v5 est `amass enum -d DOMAINE`. `-passive` est déprécié, le mode passif
étant déjà la valeur par défaut ; cela ne signifie pas « hors réseau ». Les
options, transformations et sources doivent être qualifiées pour rester dans le
périmètre autorisé et sans compte ni clé.

Le paquet fournit `/usr/share/doc/amass/README.Debian` et
`/usr/share/doc/amass/resources/config.yaml`, avec des exemples PostgreSQL et
Neo4j commentés. Adapter une **copie** de ces ressources à une base dédiée ; ne
pas reprendre les identifiants d’exemple. PostgreSQL n’est pas requis pour la
lecture SQLite ci-dessus. Aucune base ni aucun service ne sont créés par la fiche.

Après approbation explicite des accès réseau, le diagnostic du moteur se fait
au premier plan avec `amass engine -log-dir DOSSIER_JOURNAUX_DEDIE`, dans un
environnement dédié. `engine -h` décrit ses options ; il n’a pas d’option
`-config`. Le moteur utilise aussi `127.0.0.1:6060` pour son diagnostic Go.
Contrôler ces ports et les journaux avant toute session. Ce démarrage contacte
déjà des services tiers, même sans cible. Ne pas l’utiliser comme simple sonde.

L’énumération réseau n’a pas été qualifiée dans cette recette. Un binaire
installé, une aide générale ou une base vide ne prouvent pas qu’elle fonctionne.

## Sources primaires vérifiées le 12 novembre 2026

- Paquet Kali installé : `README.Debian`, ressources et aides locales v5.1.3.
- [Lanceur v5.1.3 : ordre de démarrage et attente](https://github.com/owasp-amass/amass/blob/v5.1.3/cmd/amass/main.go),
  [processus enfant et contrôle API](https://github.com/owasp-amass/amass/blob/v5.1.3/cmd/amass/process.go).
- [Initialisation BGP.Tools](https://github.com/owasp-amass/amass/blob/v5.1.3/engine/plugins/whois/bgptools/plugin.go),
  [chargement obligatoire des plugins](https://github.com/owasp-amass/amass/blob/v5.1.3/engine/plugins/load.go).
- [Options enum v5](https://github.com/owasp-amass/amass/blob/v5.1.3/internal/enum/cli.go),
  [lecture subs](https://github.com/owasp-amass/amass/blob/v5.1.3/internal/subs/cli.go),
  [choix SQLite/PostgreSQL/Neo4j](https://github.com/owasp-amass/amass/blob/v5.1.3/internal/tools/graph.go).
- [Guide PostgreSQL indiqué par Kali](https://owasp-amass.github.io/docs/asset_db/postgres/).
