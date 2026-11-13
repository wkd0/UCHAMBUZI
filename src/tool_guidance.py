# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : tool_guidance.py
# Role          : Fiches explicatives et preparation bornee des outils OSINT
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Descriptions locales et preparation seulement : aucun outil n'est execute ici."""
import re
import shlex
import shutil

from indices_outils import classify
from tools_catalog import load_catalog, validate_catalog

OBJECTIVES = (
    dict(id='domain', title='Domaines & DNS', description='Retrouver les noms, sous-domaines et enregistrements liés à une organisation.'),
    dict(id='infra', title='Infrastructure & Réseau', description='Examiner les services, technologies et adresses exposés.'),
    dict(id='person', title='Personne & Identité', description='Explorer une adresse email, un numéro ou un pseudonyme.'),
    dict(id='social', title='Pseudonymes & Profils', description='Repérer des profils publics et recouper leur attribution.'),
    dict(id='media', title='Fichiers & Métadonnées', description='Examiner des fichiers locaux et leurs informations techniques.'),
    dict(id='leaks', title='Secrets dans les fichiers', description='Repérer des secrets potentiels dans des fichiers ou dépôts locaux.'),
    dict(id='web_archive', title='Web & Archives', description='Retrouver des URL historiques dans des sources tierces.'),
)

GUIDED_TOOLS = frozenset(('maigret', 'blackbird', 'social-analyzer', 'holehe', 'gau', 'phoneinfoga'))
# Shared with the REPL so the catalogue advertises the routes actually offered.
QUICK_TOOL_SPECS = {
    '/pseudo': ('username', (('whatsmyname', ()), ('maigret', ('--timeout', '10')),
                             ('blackbird', ('--username',)),
                             ('social-analyzer', ('--mode', 'fast', '--output', 'json', '--username')))),
    '/domaine': ('domain', (('whois', ()), ('dig', ()), ('subfinder', ('-d',)), ('gau', ()))),
    '/email': ('email', (('holehe', ()),)),
    '/archive': ('url', (('gau', ()),)),
    '/photo': ('image', (('exiftool', ('-config', '', '--')), ('mat2', ('--show', '--')))),
}
_INPUTS = {
    'username': ('Pseudonyme', 'enquete_demo'), 'email': ('Adresse email', 'analyste@example.org'),
    'domain': ('Domaine', 'example.org'), 'url': ('URL HTTP(S)', 'https://example.org'),
    'ip': ('Adresse IP', '192.0.2.1'), 'phone': ('Numéro international E.164', '+33601020304'),
    'image': ('Chemin d’une image locale', '/chemin/exercice.jpg'),
    'file': ('Chemin d’un fichier local', '/chemin/exercice.txt'), 'hash': ('Empreinte', 'SHA-256 du fichier'),
}

# Descriptions attachées aux identifiants de la liste blanche, jamais aux sorties IA.
# Chaque limite explique ce qui ne peut pas être conclu à partir du résultat.
_DESCRIPTIONS = {
    'maigret': ('Rechercher des profils publics utilisant un pseudonyme.',
        'Élargir une recherche de pseudonyme puis recouper les profils trouvés.',
        'URL de profils potentiels, états des vérifications et informations publiques disponibles.',
        'Un pseudonyme commun ne prouve pas une identité commune. Faux positifs, sites indisponibles et limites de requêtes possibles.'),
    'blackbird': ('Rechercher la présence publique d’un pseudonyme sur différentes plateformes.',
        'Recouper une recherche Maigret ou WhatsMyName avec un autre moteur.',
        'Profils potentiels et URL à examiner manuellement.',
        'Le parcours accompagné utilise seulement le pseudonyme, même si le programme possède d’autres modes. Les rapports natifs temporaires ne sont pas des exports persistants UCHAMBUZI.'),
    'social-analyzer': ('Repérer et analyser des profils publics correspondant à un pseudonyme.',
        'Compléter le recoupement de présence en ligne avec une sortie JSON structurée.',
        'Correspondances potentielles et données publiques renvoyées par les plateformes.',
        'Le mode fast est un périmètre de recherche limité. Une correspondance technique n’établit pas l’attribution à une personne.'),
    'holehe': ('Rechercher des indices d’utilisation d’une adresse email sur différents services.',
        'Explorer une adresse email connue au lieu de supposer que son préfixe est un pseudonyme.',
        'États de présence possibles, réponses indéterminées et limites de requêtes.',
        'Certains modules interrogent des mécanismes d’inscription, de connexion ou de récupération. L’absence d’alerte à la cible n’est pas garantie ; un résultat négatif ne prouve pas l’absence de compte.'),
    'gau': ('Collecter des URL connues de fournisseurs d’archives web.',
        'Retrouver des pages et chemins historiques avant d’envisager une requête directe au site.',
        'Liste d’URL historiques à trier, dater et vérifier.',
        'Une URL archivée peut avoir disparu ou changé de propriétaire. La collecte contacte des services tiers ; elle ne prouve ni accessibilité actuelle ni vulnérabilité.'),
    'phoneinfoga': ('Examiner localement le format et les informations dérivées d’un numéro international.',
        'Qualifier un numéro avant de décider quelles recherches complémentaires effectuer.',
        'Informations locales de format, indicatif et validité selon les données du programme.',
        'Ce parcours désactive les scanners réseau et ceux à clé. Il ne localise pas un téléphone et ne prouve ni propriétaire, ni activité, ni opérateur actuel.'),
    'whatsmyname': ('Vérifier un pseudonyme sur un ensemble de sites issu d’une base locale.',
        'Commencer une recherche bornée avant d’utiliser plusieurs moteurs de recoupement.',
        'URL de profils possibles et réponses indéterminées ; 50 sites maximum dans le parcours actuel.',
        'Le moteur est intégré à UCHAMBUZI, pas un exécutable à lancer dans le shell. Les vérifications contactent les sites et restent sujettes aux faux positifs.'),
    'whois': ('Consulter les informations d’enregistrement d’un domaine ou d’une IP.', 'Identifier le registre, le registrar et les contacts rendus publics.', 'Données d’enregistrement et dates disponibles.', 'Données souvent masquées ou limitées ; elles ne prouvent pas la propriété actuelle.'),
    'dig': ('Interroger les enregistrements DNS.', 'Vérifier la résolution et les services déclarés d’un domaine.', 'Réponses DNS avec type, valeur et TTL.', 'Réponse dépendante du résolveur et de l’instant ; elle ne prouve pas la propriété d’un hôte.'),
    'dnsrecon': ('Énumérer des informations DNS selon plusieurs méthodes.', 'Approfondir une cartographie DNS ciblée.', 'Enregistrements, noms et résultats des méthodes choisies.', 'Certaines méthodes sont actives ; chaque option doit être choisie et expliquée.'),
    'dnsenum': ('Énumérer les noms et enregistrements liés à un domaine.', 'Recouper une découverte DNS avec un autre outil.', 'Noms et enregistrements découverts.', 'L’énumération peut provoquer des requêtes actives ; la couverture n’est pas exhaustive.'),
    'amass': ('Cartographier des noms et relations d’infrastructure.', 'Explorer les liens entre un domaine et son exposition publique, ou relire une base locale avec subs.', 'Noms, adresses et relations selon les sources sélectionnées.', 'Amass v5.1.3 : libpostal requis sur Kali ; enum démarre un moteur dépendant du réseau avant même -h. Sa présence ne prouve pas que le moteur et la base sont prêts. subs peut lire SQLite localement. Voir docs/amass-v5.md ; seules les sources sans compte ni clé sont admises.'),
    'sublist3r': ('Rechercher des sous-domaines dans des sources publiques.', 'Compléter une première liste de noms.', 'Sous-domaines potentiels.', 'Sources parfois indisponibles ; un nom trouvé ne prouve pas son activité actuelle.'),
    'fierce': ('Effectuer une reconnaissance DNS.', 'Explorer la structure de nommage d’un domaine.', 'Noms et adresses issus de recherches DNS.', 'Les recherches sont actives et doivent être bornées à un périmètre autorisé.'),
    'theharvester': ('À partir d’un domaine fourni, collecter des traces publiques telles que des hôtes et adresses email.', 'Rassembler une première vue d’exposition depuis plusieurs sources.', 'Noms, adresses et autres données selon les sources disponibles.', 'Ne déduit pas des domaines associés à partir d’une adresse email. Les sources exigeant compte ou clé ne sont pas retenues. Aucune action accompagnée n’est encore qualifiée ici.'),
    'dmitry': ('Rassembler des informations de reconnaissance réseau.', 'Comparer plusieurs informations techniques sur un hôte.', 'Données de domaine, d’hôte et résultats des fonctions choisies.', 'L’outil combine des fonctions différentes, dont certaines actives ; éviter les lancements globaux non expliqués.'),
    'whatweb': ('Identifier les technologies apparentes d’un service web.', 'Comprendre les composants déclarés par un site.', 'Signatures techniques et en-têtes observés.', 'Contacte le serveur ; les signatures peuvent être trompeuses et ne prouvent pas une version vulnérable.'),
    'wafw00f': ('Rechercher des indices de protection WAF sur un site.', 'Contextualiser les réponses filtrées d’un service web.', 'Familles de protections potentielles.', 'Détection heuristique par requêtes actives, pas preuve d’une configuration de sécurité.'),
    'sherlock': ('Rechercher un pseudonyme sur différentes plateformes.', 'Recouper des profils possibles avec un moteur supplémentaire.', 'URL et états de présence possibles.', 'Intégré au scénario email-pseudo, sans préparation individuelle depuis cette fiche ; doublons et faux positifs possibles.'),
    'spiderfoot': ('Orchestrer des collectes OSINT par modules.', 'Relier différents types d’indices lors d’une investigation plus large.', 'Événements et relations issus des modules sélectionnés.', 'Tous les modules ne sont pas utilisables sans compte ou clé. Leur sélection doit être qualifiée avant une intégration accompagnée.'),
    'recon-ng': ('Organiser des recherches OSINT dans une console à modules.', 'Travailler sur des données et transformations dans un espace dédié.', 'Enregistrements et exports des modules utilisés.', 'La console et les modules ont leurs propres commandes ; aucun téléchargement de module ni lancement global implicite.'),
    'exiftool': ('Lire les métadonnées d’un fichier.', 'Relever dates, appareil ou coordonnées déclarées dans un média.', 'Champs de métadonnées et informations techniques.', 'Les métadonnées peuvent avoir été modifiées ; elles ne prouvent pas la provenance.'),
    'mat2': ('Examiner les métadonnées prises en charge par mat2.', 'Repérer des informations personnelles dans un média.', 'Champs détectés selon le format.', 'Le parcours /photo utilise seulement --show ; les fonctions de nettoyage modifient des fichiers et nécessitent une décision séparée.'),
    'foremost': ('Rechercher des fichiers à partir de signatures dans une image locale.', 'Tenter un carving sur une copie de travail.', 'Fichiers reconstruits et compte rendu.', 'Reconstruction partielle possible ; travailler sur une copie et prévoir un dossier de sortie distinct.'),
    'binwalk': ('Repérer des signatures et contenus embarqués dans un fichier.', 'Orienter l’examen d’un firmware ou conteneur.', 'Offsets et signatures potentielles.', 'Une signature est heuristique ; les fonctions d’extraction ne sont pas automatiquement autorisées.'),
    'strings': ('Extraire les suites de caractères imprimables d’un fichier.', 'Trouver des pistes textuelles sans exécuter le fichier.', 'Chaînes et éventuels offsets selon les options.', 'Une chaîne isolée n’explique pas le comportement du programme ; sorties non fiables.'),
    'metagoofil': ('Rechercher des documents publics liés à un domaine.', 'Étudier l’exposition documentaire d’une organisation.', 'Documents et indices de métadonnées selon le parcours utilisé.', 'Téléchargements et requêtes réseau possibles ; vérifier le périmètre et la provenance des fichiers.'),
    'curl': ('Interroger une ressource réseau avec sa syntaxe native.', 'Examiner une réponse HTTP ou récupérer une ressource déterminée.', 'Corps de réponse, en-têtes et code de retour selon les options.', 'Peut envoyer ou modifier des données selon ses options ; une URL ou sortie externe ne doit jamais devenir une commande.'),
    'nmap': ('Explorer les ports et services d’un hôte.', 'Vérifier une exposition technique dans un périmètre autorisé.', 'Ports et signatures de services selon le scan choisi.', 'Scan actif détectable ; l’outil conserve sa syntaxe native dans le shell, sans catalogue de toutes ses options slash.'),
    'subfinder': ('Rechercher des sous-domaines dans des sources tierces.', 'Compléter une cartographie de domaine.', 'Liste de noms potentiels.', 'Artefact vérifié non embarqué : indisponible dans cette version. Certaines sources exigent une clé et sont exclues.'),
    'httpx': ('Caractériser les réponses de services HTTP.', 'Trier des services web découverts.', 'États HTTP et caractéristiques selon les options.', 'Artefact vérifié non embarqué ; les sondes contactent les services.'),
    'dnsx': ('Effectuer des vérifications DNS sur une liste de noms.', 'Valider ou enrichir des noms découverts.', 'Enregistrements et états de résolution.', 'Artefact vérifié non embarqué ; les requêtes réseau doivent être bornées.'),
    'photon': ('Explorer les liens et ressources d’un site.', 'Cartographier les références publiques d’un site.', 'URL et ressources découvertes.', 'Artefact vérifié non embarqué ; exploration active avec risques de volume et de périmètre.'),
    'trufflehog': ('Rechercher des secrets potentiels dans des données.', 'Examiner l’exposition de secrets dans un dépôt ou fichier.', 'Correspondances à qualifier.', 'Artefact vérifié non embarqué ; certains modes valident les secrets en réseau, ce qui doit être distingué d’une analyse locale.'),
    'gitleaks': ('Détecter des motifs de secrets dans des fichiers ou dépôts.', 'Effectuer un premier contrôle local d’exposition de secrets.', 'Correspondances avec emplacement et règle.', 'Artefact vérifié non embarqué ; faux positifs possibles et aucun secret trouvé ne doit être réutilisé automatiquement.'),
}


def _entry(tool_id, rows):
    if not isinstance(tool_id, str):
        raise ValueError('Identifiant d’outil attendu.')
    return next((row for row in rows if row['id'] == tool_id), None)


def integration_for(tool_id):
    """Describe implemented entry points, independently of installation state."""
    tool = _entry(tool_id, load_catalog())
    if tool is None:
        raise ValueError('Outil absent du catalogue approuvé.')
    if tool['source'] == 'vendored' and not tool.get('artifact'):
        return dict(level='planned', label='À venir', routes=(),
                    detail='Aucune copie vérifiée distribuée ; aucun parcours exécutable proposé.')
    routes = [command + ' <indice>' for command, (_, operations) in QUICK_TOOL_SPECS.items()
              if any(name == tool_id for name, _ in operations)]
    from osint_playbooks import list_playbooks
    for playbook in list_playbooks():
        # An alternative is only a suggestion, not an implemented replacement.
        if any(step.tool_id == tool_id and
               shlex.split(step.command_template)[0] == tool['executable']
               for step in playbook.steps):
            routes.append('/scenario ' + playbook.slug + ' <indice>')
    if tool_id in GUIDED_TOOLS:
        routes.insert(0, '/tools run ' + tool_id + ' <indice>')
        level, label = 'guided', 'Action accompagnée'
        detail = 'Préparation individuelle disponible ; seules les options prévues sont intégrées.'
    elif tool['source'] == 'builtin':
        level, label = 'builtin', 'Moteur natif'
        detail = 'Moteur intégré à UCHAMBUZI ; aucun exécutable shell.'
    elif routes:
        level, label = 'workflow', 'Parcours intégré'
        detail = 'Utilisable dans les parcours indiqués ; pas de préparation individuelle depuis cette fiche.'
    else:
        level, label = 'shell', 'Shell et aide'
        detail = 'Fiche descriptive et aide locale ; aucun parcours intégré pour cet outil.'
    return dict(level=level, label=label, routes=tuple(routes), detail=detail)


def guide_for(tool_id):
    """Return a fresh local guide; an unknown tool never becomes a command."""
    tool = _entry(tool_id, load_catalog())
    if tool is None or tool_id not in _DESCRIPTIONS:
        raise ValueError('Outil absent du catalogue approuvé.')
    purpose, why, outputs, limits = _DESCRIPTIONS[tool_id]
    kind = 'domain' if tool_id == 'gau' else tool['input_types'][0]
    label, example = _INPUTS[kind]
    if tool_id == 'gau':
        label = 'Domaine ou URL HTTP(S)'
    input_example = example
    examples = {
        'maigret': 'maigret --timeout 10 enquete_demo',
        'blackbird': 'blackbird --username enquete_demo',
        'social-analyzer': 'social-analyzer --mode fast --output json --username enquete_demo',
        'holehe': 'holehe analyste@example.org',
        'gau': 'gau example.org',
        'phoneinfoga': 'phoneinfoga scan -n +33601020304 --env-file /dev/null -D numverify -D googlecse -D ovh -D googlesearch',
        'whatsmyname': '/pseudo enquete_demo',
        'amass': 'amass -h',
    }
    hints = {
        'maigret': '--timeout 10 borne le délai des requêtes ; le pseudonyme est un argument positionnel. Le délai global UCHAMBUZI reste distinct.',
        'blackbird': '--username introduit explicitement le pseudonyme. Les rapports internes temporaires ne remplacent pas le journal UCHAMBUZI.',
        'social-analyzer': '--mode fast sélectionne la recherche rapide ; --output json produit une sortie structurée ; --username introduit le pseudonyme.',
        'holehe': 'L’adresse email est un argument positionnel. La copie embarquée désactive sa vérification de mise à jour automatique.',
        'gau': 'Le parcours accompagné fournit seulement le domaine ou l’URL ; les URL retournées viennent de services tiers, pas d’une vérification du site cible.',
        'phoneinfoga': 'scan -n introduit le numéro ; --env-file /dev/null évite le chargement d’une configuration à clés ; -D désactive les cinq scanners réseau ou à clé nommés.',
        'whatsmyname': 'Utiliser /pseudo <pseudo> : le moteur natif n’a pas de commande shell.',
        'amass': 'v5.1.3 : -h, engine -h et subs -h sont des aides locales ; enum -h peut attendre le moteur pendant 60 s. Ne pas le sonder automatiquement. Lecture locale : subs -config CONFIG_LOCALE -dir DOSSIER_BASE -d example.test -names -nocolor. Voir docs/amass-v5.md pour la configuration isolée et le diagnostic réseau.',
    }
    return dict(purpose=purpose, why=why, input_label=label, input_kind=kind,
                outputs=outputs, limits=limits,
                example=examples.get(tool_id, tool['executable'] + ' --help'),
                input_example=input_example, guided=tool_id in GUIDED_TOOLS,
                help_hint=hints.get(tool_id, 'Exemple d’aide native seulement ; aucune action accompagnée qualifiée dans cette version.'))



def _installer_entry(tool_id, installer):
    rows = validate_catalog({'schema_version': 1, 'tools': list(installer.catalog)})
    tool = _entry(tool_id, rows)
    if tool is None:
        raise ValueError('Outil absent du catalogue approuvé.')
    return tool


def resolve_shell(tool_id, installer):
    """Resolve only catalogue executables; do not install, probe or execute."""
    tool = _installer_entry(tool_id, installer)
    if tool['source'] == 'builtin':
        return None
    if tool['source'] == 'vendored':
        if not tool.get('artifact'):
            return None
        return installer.executable(tool_id)
    return shutil.which(tool['executable'], path='/usr/bin:/bin')


def build_command(tool_id, target, installer):
    """Prepare a supported argv without invoking an execution or approval API."""
    tool = _installer_entry(tool_id, installer)
    if tool_id not in GUIDED_TOOLS:
        raise ValueError('Aucune action accompagnée qualifiée pour cet outil.')
    if (not isinstance(target, str) or not target.strip() or len(target) > 2048
            or any(ord(c) < 32 or ord(c) == 127 for c in target)
            or re.search(r'[;&|`$<>\\]', target)):
        raise ValueError('Indice invalide : texte de commande ou caractère de contrôle interdit.')
    target = target.strip()
    kind = ('url' if target.lower().startswith(('http://', 'https://')) else 'domain') if tool_id == 'gau' else guide_for(tool_id)['input_kind']
    result = classify(target, kind)
    if result['validation'] != 'valid':
        raise ValueError('Indice invalide : ' + result['explanation'])
    normalized = result['normalized']
    if normalized.startswith('-'):
        raise ValueError('Indice invalide : préfixe d’option interdit.')
    executable = resolve_shell(tool_id, installer)
    if not executable:
        raise ValueError('Copie vérifiée indisponible ; préparer cet outil avec /tools install ' + tool_id + '.')
    options = {
        'maigret': ('--timeout', '10', normalized),
        'blackbird': ('--username', normalized),
        'social-analyzer': ('--mode', 'fast', '--output', 'json', '--username', normalized),
        'holehe': (normalized,),
        'gau': (normalized,),
        'phoneinfoga': ('scan', '-n', normalized, '--env-file', '/dev/null', '-D', 'numverify',
                       '-D', 'googlecse', '-D', 'ovh', '-D', 'googlesearch'),
    }[tool_id]
    argv = [executable, *options]
    return dict(tool_id=tool_id, argv=argv, display=shlex.join(argv),
                activity='passive' if tool_id == 'phoneinfoga' else tool['activity'],
                needs_network=False if tool_id == 'phoneinfoga' else tool['needs_network'],
                input_kind=kind, target=normalized)
