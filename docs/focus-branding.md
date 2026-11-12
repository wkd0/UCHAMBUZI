# Identité et accueil Focus

> Référence de composant ou recette historique, conservée pour sa provenance. Pour la V1.0.0, utiliser l’[index courant](README.md), les [commandes](commandes.md) et la [note de recette V1](releases/1.0.0.md). Ce document ne certifie pas le candidat actuel.

> Note de composant historique : le raccordement décrit ci-dessous vise une interface Focus antérieure. Le bandeau actuellement assemblé est défini dans `src/repl_welcome.py` et les modules importés par celui-ci.

`src/focus_branding.py` fournit un rendu sans chargement d'image ni dépendance externe. Le dessin est une interprétation par cellules des SVG officiels : crête à trois barres orange, œil en amande, iris, pupille et réticule, trois points orange à chaque extrémité. La police et les courbes SVG ne peuvent pas être reproduites exactement en caractères terminaux. Le nom est présenté séparément en capitales. L'orange officiel est `#E85D26` ; sur fond clair, les traits utilisent le marine officiel `#0D1B2A`, et sur fond sombre un gris clair contrasté remplace le marine illisible. Le thème doit être fourni par l'application : la couleur de fond ne peut pas être déduite de manière fiable.

## Raccordement

L'intégrateur peut injecter `BrandLogo()` dans le champ `logo` de `FocusExtensions` du moteur 02 annoncé : `render_logo(width, height)` retourne des lignes sans ANSI, conformément à sa signature. Cette compatibilité est structurelle et ne valide pas le moteur encore en arbitrage. La composition complète reste indépendante :

```python
from focus_branding import WelcomeInfo, render_welcome, terminal_options

unicode_ok, truecolor_ok = terminal_options()  # sortie et environnement réels
info = WelcomeInfo.from_snapshot(snapshot, version=version_reelle,
                                 mode=mode_connu, directory=repertoire_reel)
lines = render_welcome(width, info, height=height, unicode=unicode_ok,
                       color=truecolor_ok, theme='dark',
                       conversation_started=bool(snapshot.messages))
```

Les valeurs et leur actualisation relèvent de l'orchestrateur : `snapshot.settings.model` décrit le modèle choisi, pas son état de connexion. La version, le mode et le répertoire doivent provenir des services d'exécution ; `None` produit une mention neutre. Le texte `/aide` correspond à un alias existant du prototype et devra être vérifié lors de l'assemblage Focus. La sortie est une liste de lignes ; le moteur peut l'afficher, la remplacer ou l'animer sans état caché. `conversation_started=True` supprime l'accueil. Aucun lancement ni gestion d'animation n'est modifié ici.

`terminal_options` désactive la couleur pour `NO_COLOR` (même vide), `TERM=dumb`, sortie non TTY ou absence d'annonce TrueColor ; il détecte l'encodage Unicode. `render_logo` et `render_welcome` acceptent explicitement ces capacités : l'appelant doit leur transmettre les résultats. Les variantes automatique, complète, compacte et minimale s'adaptent à l'espace ; si aucune ne tient, le logo est omis. Les chaînes variables sont nettoyées des contrôles, puis tronquées à la largeur. Les caractères combinants et les caractères larges sont comptés sans dépendance ; les séquences complexes d'emoji et les conventions de largeur des terminaux peuvent différer. Une recette visuelle sur terminaux, thèmes, SSH et lecteurs d'écran reste nécessaire.
