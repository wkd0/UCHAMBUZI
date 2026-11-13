#!/usr/bin/env python3
# ============================================================================
# UCHAMBUZI - Assistant local pour l'investigation numerique
# ============================================================================
# Fichier       : uchambuzi.py
# Role          : CLI francophone, diagnostics et recommandations en apercu
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Terminal intégré; seules les vérifications locales de version peuvent lancer des outils."""
import parcours
import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
import os
import shutil
import textwrap
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

from conversation import (DEFAULT_TIMEOUT, DEFAULT_CONTEXT_BUDGET, OllamaRuntime, Session,
                          RuntimeErrorLocal, RuntimeIncomplete, ProviderManager, safe_display,
                          audit_file_prompt_injection)
import documentation_locale
import indices_outils
import installation
import commandes
from parcours import (analyse, prepare_selected, refusal, render_analysis, render_preparation,
                      context_for_choice, CaseManager, methods_reviews, stage_corpus_file)

VERSION = '2.0.0'
REPOSITORY = 'https://github.com/wkd0/UCHAMBUZI.git'
SOURCE_BRANCH = 'beta'


COMMAND_ALIASES = {
    '/case': '/investigation', '/cases': '/investigation',
    '/aide': '/help', '/analyse': '/analyze', '/indice': '/indicator',
    '/cible': '/target', '/preparer': '/prepare', '/outils': '/tools',
    '/contexte': '/context', '/modeles': '/models', '/parametres': '/settings',
    '/ia': '/ai', '/dossier': '/investigation', '/methodes': '/methods',
    '/auditer': '/audit', '/chercher': '/search', '/quitter': '/exit',
    '/specialite': '/mode', '/activite': '/scenario',
}


def normalize_command(text):
    """Normalise uniquement le nom et son séparateur ; conserve les arguments."""
    text = text.strip()
    match = re.match(r'(\S+)(\s+)(.*)', text, re.S)
    command = match[1] if match else text
    canonical = COMMAND_ALIASES.get(command, command)
    if canonical not in (*COMMAND_ALIASES.values(), '/reset', '/quit', '/mode', '/scenario'):
        return text
    return canonical + (' ' + match[3] if match else '')


def terminal_color():
    """La couleur est réservée aux terminaux interactifs compatibles."""
    return (sys.stdout.isatty() and 'NO_COLOR' not in os.environ
            and os.environ.get('TERM') != 'dumb')


def terminal_banner(width=None):
    """Bannière inspirée du symbole officiel, adaptée au terminal."""
    width = width if width is not None else shutil.get_terminal_size((80, 24)).columns
    if width >= 62:
        art = ("          ·──────── ◉ ────────·\n"
               "            U C H A M B U Z I\n"
               "     INVESTIGATION NUMÉRIQUE LOCALE")
    elif width >= 25:
        art = "    ·──── ◉ ────·\n    U C H A M B U Z I"
    else:
        art = "UCHAMBUZI"
    if terminal_color():
        return "\033[38;2;232;93;38m" + art + "\033[0m"
    return art


def terminal_panel(title, body, width=None):
    """Encadre un texte sûr, sans permettre les contrôles terminaux externes."""
    width = width if width is not None else shutil.get_terminal_size((80, 24)).columns
    title, body = safe_display(title).replace("\n", " ").expandtabs(), safe_display(body).expandtabs()
    if width < 20:
        return "\n".join(textwrap.wrap(title, max(1, width)) + [part for line in body.splitlines() for part in (textwrap.wrap(line, max(1, width)) or [""])])
    inner = min(width, 80) - 4
    lines = []
    for line in body.splitlines() or ['']:
        lines.extend(textwrap.wrap(line, inner, replace_whitespace=False,
                                   drop_whitespace=False) or [''])
    header = (' ' + title + ' ')[:inner + 2]
    border = '+' + header + '-' * (inner + 2 - len(header)) + '+'
    output = [border] + ['| ' + line.ljust(inner) + ' |' for line in lines] + ['+' + '-' * (inner + 2) + '+']
    if terminal_color():
        output[0] = '\033[38;2;232;93;38m' + output[0] + '\033[0m'
        output[-1] = '\033[38;2;232;93;38m' + output[-1] + '\033[0m'
    return '\n'.join(output)


def show_result(title, renderer, value):
    """Présente les résultats existants sans modifier leur logique métier."""
    output = StringIO()
    with redirect_stdout(output):
        renderer(value)
    print(terminal_panel(title, 'Détails ci-dessous :'))
    print(output.getvalue().rstrip())


def paths():
    return installation.paths()


def doctor():
    print(f'UCHAMBUZI {VERSION} — diagnostic\nPython : {sys.version.split()[0]}')
    try:
        installation.check_system_prerequisites()
    except (OSError, ValueError) as exc:
        print('Prérequis système invalides : ' + safe_display(exc))
        return 1
    inst_state = installation.inspect_installation()
    if inst_state.get('installed'):
        status_label = 'intègre' if inst_state.get('valid') else 'anomalie détectée'
        print(safe_display(f"Installation : {inst_state.get('version', 'inconnue')} ({status_label})"))
        if not inst_state.get('valid'):
            for issue in inst_state.get('issues', ()):
                print('  Anomalie : ' + safe_display(issue))
            return 1
    print(safe_display(f'Données utilisateur : {installation.user_data_path()}'))
    print('Outils : présence dans PATH seulement, sans lancement.')
    for item in indices_outils.inventory():
        print(safe_display(f"  {item['id']} : {item['executable_path'] or 'absent'}"))
    import documentation_locale
    import commandes
    try:
        corpus = documentation_locale.Corpus()
        for source in corpus.data['sources']:
            ref = corpus.reference(source['id'])
            print(safe_display(f"Source {ref['id']} : {ref['availability']}, {ref['freshness']}"))
        if installation.checksum(commandes.SYNTAX.read_bytes()) != commandes.SYNTAX_SHA256:
            raise ValueError('Note syntaxique altérée.')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Documentation indisponible : ' + safe_display(exc))
        return 1
    print('IA : adaptateur local disponible, aucun moteur ni modèle interrogé par ce diagnostic.')
    return 0


def install(source):
    launcher = installation.install(source, version=VERSION, repository=REPOSITORY, branch=SOURCE_BRANCH)
    print(safe_display(f'Installé : {launcher}\nDonnées : {installation.user_data_path()}\nAjoutez ~/.local/bin au PATH si nécessaire.'))
    return 0


def update(source, yes=False):
    app, _ = paths()
    meta = installation.metadata(app)
    source = Path(source or meta['source']).expanduser().resolve()
    source_text = (source / 'src/uchambuzi.py').read_text(encoding='utf-8')
    match = re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)", source_text, re.M)
    declared = re.search(r"^REPOSITORY\s*=\s*['\"]([^'\"]+)", source_text, re.M)
    repo = installation.local_git(source, 'remote', 'get-url', 'origin') or (declared.group(1) if declared else None)
    if not match or not declared or repo != meta['repository'] or declared.group(1) != meta['repository']:
        raise ValueError('Source locale ou dépôt non reconnu; mise à jour refusée.')
    target_version = match.group(1)
    same_version = (target_version == meta['version'])
    print(safe_display(f"Source : {source}\nVersion installée : {meta['version']} ; proposée : {target_version}\nAucun accès distant."))
    if same_version:
        print(safe_display(f"Même version ({target_version}) déjà installée : actualisation/réinstallation sur place (aucune montée de version)."))
    if not yes and input('Confirmer la mise à jour ? (oui/N) ').strip().lower() != 'oui':
        print('Mise à jour annulée.')
        return 0
    launcher = installation.install(source, version=target_version, repository=repo, branch=SOURCE_BRANCH)
    if same_version:
        print(safe_display(f'Version {target_version} déjà installée : fichiers vérifiés et synchronisés ({launcher}). Aucune montée de version. Données supplémentaires conservées.'))
    else:
        print(safe_display(f'Mis à jour ({meta["version"]} -> {target_version}) : {launcher}. Données supplémentaires conservées.'))
    return 0


def update_release(tag, yes=False):
    app, _ = paths()
    meta = installation.metadata(app)
    if meta['repository'] != installation.RELEASE_REPOSITORY:
        raise ValueError('Depot installe different du depot officiel ; mise a jour refusee.')
    tag, version = installation.release_identity(tag)
    print(safe_display(f"Version installee : {meta['version']} ; proposee : {version}.\n"
                      f"Acces reseau explicite : GitHub wkd0/UCHAMBUZI, release {tag}.\n"
                      'Archive et SHA256SUMS seront verifies avant installation.'))
    if not yes and input('Autoriser le telechargement GitHub et la mise a jour ? (oui/N) ').strip().lower() != 'oui':
        print('Mise a jour annulee ; aucun acces distant.')
        return 0
    with installation.verified_release_source(tag) as (source, target_version, verified_tag):
        launcher = installation.install(source, version=target_version,
            repository=installation.RELEASE_REPOSITORY, branch=SOURCE_BRANCH,
            source_reference=app, release_tag=verified_tag)
    print(safe_display(f"Mis a jour ({meta['version']} -> {version}) : {launcher}. Donnees utilisateur conservees."))
    return 0


def repair(source=None, yes=False):
    state = installation.inspect_installation()
    if state.get('installed'):
        print(safe_display(f"Installation détectée : {state.get('version', 'inconnue')} ({'intègre' if state.get('valid') else 'à réparer'})"))
        for issue in state.get('issues', ()):
            print('  Anomalie : ' + safe_display(issue))
    else:
        print('Aucune installation valide détectée ; réparation / réinstallation depuis la source locale.')
    confirm_fn = (lambda: True) if yes else (
        lambda: input('Confirmer la réparation avec sauvegarde des fichiers modifiés ? (oui/N) ').strip().lower() == 'oui'
    )
    result = installation.repair(
        source,
        version=VERSION,
        repository=REPOSITORY,
        branch=SOURCE_BRANCH,
        confirm=confirm_fn,
    )
    if not result['repaired']:
        print('Réparation annulée.')
        return 0
    if result['backups']:
        print('Fichiers modifiés sauvegardés avant réparation :')
        for bkp in result['backups']:
            print('  ' + safe_display(bkp))
    print(safe_display(f"Installation réparée : {result['launcher']}\nDonnées préservées : {result['data_path']}"))
    return 0


def uninstall(*, yes=False, purge_data=False, purge_ai=False, remove_models=()):
    if purge_data or purge_ai or remove_models:
        details = ['fichiers du manifeste et lanceur']
        if purge_data:
            details.append(f'données utilisateur ({installation.user_data_path()})')
        if remove_models:
            details.append('modèles IA locaux (' + ', '.join(remove_models) + ')')
        if purge_ai:
            details.append('composant IA local Ollama (binaire utilisateur, service utilisateur et répertoire ~/.ollama)')
        print(safe_display('Retrait demandé : ' + ', '.join(details) + '.'))
    else:
        print('Retrait limité aux fichiers du manifeste, dont les modules et les ressources distribuées ; données supplémentaires conservées.')
    if purge_ai or remove_models:
        ai_info = installation.inspect_local_ai_environment()
        print(safe_display('Impact IA locale : ' + ai_info['shared_component_warning']))
    confirm_fn = (lambda: True) if yes else (
        lambda: input('Retirer les fichiers gérés inchangés ? (oui/N) ').strip().lower() == 'oui'
    )
    removed = installation.uninstall(
        confirm=confirm_fn,
        purge_data=purge_data,
        purge_ai=purge_ai,
        remove_models=tuple(remove_models),
    )
    if not removed:
        print('Annulée.')
        return 0
    msg = 'Désinstallation terminée'
    if purge_data:
        msg += ' ; données utilisateur supprimées.'
    else:
        msg += ' ; autres données conservées.'
    if purge_ai:
        msg += ' Désinstallation d’Ollama exécutée.'
    elif remove_models:
        msg += ' Modèle(s) IA retiré(s).'
    print(safe_display(msg))
    return 0


def prepare_interactive(analysis, number):
    choices = analysis.get('choices', [])
    if number < 1 or number > len(choices):
        return refusal('invalid_selection', 'Faire /analyze puis choisir un numéro affiché.')
    if choices[number - 1]['recommendation']['tool'] not in commandes.EXACT_VERSIONS:
        return refusal('unsupported_tool', 'Aucune règle de préparation pour cet outil; recommandation informative seulement.')
    indicator = choices[number - 1]['indicator']
    kind, target = indicator['type'], indicator['normalized']
    if kind == 'file':
        root = input('Racine de travail autorisée (chemin absolu, vide = annuler) : ').strip()
        if not root:
            return refusal('cancelled', 'Préparation annulée.')
        parameters, constraints = {}, {'file_roots': [root]}
        if choices[number - 1]['recommendation']['tool'] == 'strings':
            minimum = input('Longueur minimale des chaînes (entier 4 à 64) : ').strip()
            if not re.fullmatch(r'[0-9]{1,2}', minimum):
                return refusal('unsafe_option', 'Longueur minimale invalide.')
            parameters['min_length'] = int(minimum)
    elif kind in ('domain', 'ip'):
        resolver = input('Résolveur autorisé (IP explicite) : ').strip()
        record_type = input('Type DNS (A, AAAA, MX, TXT) : ').strip().upper() if kind == 'domain' else None
        print(safe_display(f'Cible : {target} ; résolveur : {resolver}. Requête active si exécutée manuellement.'))
        if input('Confirmer ce périmètre pour la préparation seulement ? (oui/N) ').strip().lower() != 'oui':
            return refusal('network_forbidden', 'Périmètre réseau non confirmé.')
        parameters = {'resolver': resolver}
        if record_type is not None:
            parameters['record_type'] = record_type
        constraints = {'allow_network': True, 'authorized_targets': [target], 'authorized_resolvers': [resolver]}
    else:
        return refusal('unsupported_indicator', 'Pour URL/e-mail, examiner la cible dérivée avec /target N puis choisir explicitement ce nouvel indice.')
    print('Contrôles locaux de version bornés ; aucune commande d’investigation exécutée.')
    return prepare_selected(analysis, number, parameters=parameters, constraints=constraints)


def select_derived(analysis, number):
    choices = analysis.get('choices', [])
    if number < 1 or number > len(choices):
        raise ValueError('Numéro de proposition invalide.')
    indicator = choices[number - 1]['indicator']
    if indicator['validation'] != 'valid' or indicator['type'] not in ('email', 'url'):
        raise ValueError('Choisir une proposition pour URL ou e-mail valide.')
    value = indicator['normalized']
    host = value.rsplit('@', 1)[1] if indicator['type'] == 'email' else urlsplit(value).hostname
    print(safe_display(f'Indice original : {indicator["original"]}\nDomaine/hôte extrait proposé : {host}'))
    print('Ce choix ne constitue aucune autorisation réseau ni préparation de commande.')
    if input('Sélectionner cet indice dérivé ? (oui/N) ').strip().lower() != 'oui':
        print('Transformation annulée.')
        return analysis
    kind = 'ip' if indices_outils.classify(host, 'ip')['validation'] == 'valid' else 'domain'
    return analyse(host, kind=kind)


def configure_provider(manager, timeout):
    print(safe_display('Mode : ' + manager.mode + ' ; fournisseur distant : ' +
                      ('OpenAI / ' + manager.remote.model if manager.remote else 'non configuré') +
                      ' ; clé : jamais affichée. Configuration en mémoire.'))
    choice = input('Choix : local / configure / activate / back : ').strip().lower()
    choice = {'configurer': 'configure', 'activer': 'activate', 'retour': 'back'}.get(choice, choice)
    if choice == 'local':
        manager.select_local(); print('Mode local activé.')
    elif choice == 'configure':
        provider = input('Fournisseur (openai) : ').strip().lower()
        model = input('Modèle distant : ').strip()
        manager.configure_remote(provider, model, timeout)
        manager.select_local()
        print('Configuration enregistrée en mémoire ; mode local actif. Clé via OPENAI_API_KEY.')
    elif choice == 'activate':
        manager.select_remote(); print('Mode distant activé ; chaque envoi exige une confirmation.')
    elif choice != 'back':
        print('Choix inconnu.')


def remote_turn(manager, text):
    print(safe_display('Moteur : OpenAI / ' + manager.remote.model + '. Aucun historique ni fichier joint automatiquement.'))
    print('Vérifiez les secrets et les données d’enquête ; une demande confirmée peut être facturée.')
    action = input('Conserver (entrée), remplacer (r), annuler (a) : ').strip().lower()
    if action not in ('', 'r'):
        print('Transmission annulée.'); return
    if action == 'r':
        text = input('Texte expurgé : ').strip()
    if not text:
        print('Transmission annulée : texte vide.'); return
    payload = manager.remote.payload(text)
    print('Corps JSON destiné à api.openai.com :')
    print(safe_display(json.dumps(payload, ensure_ascii=True, indent=2)))
    if input('Confirmer cet envoi distant potentiellement payant ? (oui/N) ').strip().lower() != 'oui':
        print('Transmission annulée.'); return
    print(f'Réponse IA distante en cours (délai configuré {manager.remote.timeout:g} s ; Ctrl+C pour interrompre)…', flush=True)
    started = time.monotonic()
    answer = manager.remote.chat(payload['messages'], consent=True)
    print(terminal_panel('Réponse distante (non vérifiée)', answer))
    print('Sources et faits à contrôler.')
    print(f'Temps de réponse : {time.monotonic() - started:.1f} s.')


def interactive(model=None, port=11434, timeout=DEFAULT_TIMEOUT, runtime=None, context_budget=DEFAULT_CONTEXT_BUDGET, case_id=None):
    from focus_ui import DefaultCatalog
    try:
        adapter = runtime if runtime is not None else OllamaRuntime(model, port, timeout)
        session = Session(adapter, context_budget) if (runtime is not None or model is not None) else None
        catalog = DefaultCatalog()
        active_profile = catalog.get_profile('assist')
        active_scenario = None
        sessions = {(active_profile.id, None): session} if session else {}
        cases = CaseManager()
        initial_case = cases.open_case(case_id) if case_id is not None else None
    except ValueError as exc:
        print('Configuration invalide : ' + safe_display(exc)); return 2
    print(terminal_banner())
    ai_status = (f'locale — {safe_display(adapter.model)}'
                 if session is not None and getattr(adapter, 'model', None)
                 else ('locale — active' if session is not None else 'non configurée'))
    case_line = f'\nDossier : {safe_display(cases.active_case_id)}' if cases.active_case_id else ''
    print(terminal_panel(
        'Session',
        f'Version : {VERSION}\nIA : {ai_status}{case_line}\nMode : préparation, sans exécution\nTapez /help pour afficher les commandes.'
    ))
    if session is None:
        print('IA non configurée : fonctions locales disponibles ; --model NAME active un modèle local déjà présent.')
    analysis = (initial_case.get('latest_analysis') or {'choices': []}) if initial_case else {'choices': []}
    manager = ProviderManager(adapter)
    latest_analysis = analysis if analysis.get('choices') and not analysis.get('errors') else None
    selected_context = None
    context_enabled = False
    while True:
        try:
            s = normalize_command(input('\nuchambuzi> '))
            if s == '/mode' or s.startswith('/mode '):
                name = s[len('/mode'):].strip().lower()
                if not name or name in ('list', 'liste'):
                    print('Modes : ' + ', '.join(p.name for p in catalog.profiles()))
                    print('Actif : ' + active_profile.name + ' ; /mode NOM pour changer.')
                elif catalog.get_profile(name) is None:
                    print('Mode inconnu ; /mode affiche les choix.')
                else:
                    active_profile = catalog.get_profile(name)
                    active_scenario = None
                    if session is not None:
                        key = (active_profile.id, None)
                        if key not in sessions:
                            sessions[key] = Session(adapter, context_budget)
                        session = sessions[key]
                    selected_context, context_enabled = None, False
                    print('Mode : ' + active_profile.name + ' ; contexte de conversation isolé. /scenario pour les activités. Aucun droit supplémentaire.')
            elif s == '/scenario' or s.startswith('/scenario '):
                name = s[len('/scenario'):].strip().lower()
                available = catalog.scenarios(active_profile.id)
                if not name or name in ('list', 'liste'):
                    print('Scénarios : ' + ', '.join(sc.id for sc in available) + ' ; /scenario off pour conversation libre.')
                elif name != 'off' and catalog.get_scenario(active_profile.id, name) is None:
                    print('Scénario inconnu pour ce mode.')
                else:
                    active_scenario = None if name == 'off' else catalog.get_scenario(active_profile.id, name)
                    if session is not None:
                        key = (active_profile.id, active_scenario.id if active_scenario else None)
                        if key not in sessions:
                            sessions[key] = Session(adapter, context_budget)
                        session = sessions[key]
                    selected_context, context_enabled = None, False
                    print('Scénario : ' + (active_scenario.id if active_scenario else 'libre') + ' ; contexte de conversation isolé.')
            elif s in ('/exit', '/quit', 'exit'):
                print('Fin de session.'); return 0
            elif s == '/help':
                print(terminal_panel('Aide', '/mode [NAME] — spécialité ; /scenario [NAME|off] — activité\n/help — aide et commandes\n/analyze TEXT — indices et sources\n/indicator TYPE VALUE — indice explicite\n/target N — sélectionner un hôte dérivé\n/prepare N — préparer une commande sans exécution\n/investigation [create ID|open ID|status|list|rename TITRE|archive|delete|close] — dossiers d’enquête isolés\n/methods [list|approve|reject|stage] — méthodes validées et corpus\n/audit PATH — auditer un fichier suspect contre l’injection de prompt\n/search QUERY — recherche documentaire locale pondérée\n/tools — présence locale ; /models — modèles locaux\n/context [N|off] — gérer le contexte ; /reset — effacer la session\n/ai — état ; /settings — fournisseur ; /exit — fermer\nLes réponses IA restent à vérifier.'))
            elif s.startswith('/audit '):
                target_path = s[len('/audit '):].strip()
                report = audit_file_prompt_injection(target_path)
                cases.record_security_audit(report)
                from focus_ui import audit_description
                body = audit_description(report)
                print(terminal_panel('Audit anti-injection de prompt', body))
            elif s.startswith('/search '):
                query = s[len('/search '):].strip()
                corpus = documentation_locale.Corpus()
                results = corpus.search_ranked(query)
                if not results:
                    print(terminal_panel('Recherche documentaire', f"Aucun outil ou manuel local trouvé pour : {query}"))
                else:
                    lines = []
                    for result in results:
                        item = result['item']
                        if result['kind'] == 'tool':
                            lines.append(f"[{result['kind']}] {result['id']} (score {result['score']}) — {item['objective']} [fiche outil]")
                        else:
                            lines.append(f"[{result['kind']}] {result['id']} (score {result['score']}) — {item.get('title', result['id'])}"
                                         + f" [source : {parcours.readable_code(item['availability'])}, {parcours.readable_code(item['verification'])}, {parcours.readable_code(item['freshness'])}, {parcours.readable_code(item['compatibility'])}]")
                    print(terminal_panel('Recherche documentaire pondérée', '\n'.join(lines)))
            elif s == '/methods' or s.startswith('/methods '):
                arg = s[len('/methods'):].strip()
                reviews = methods_reviews()
                corpus = documentation_locale.Corpus()
                if not arg or arg in ('list', 'liste'):
                    approved = reviews.approved(corpus, indices_outils.inventory())
                    if not approved:
                        print(terminal_panel('Méthodes éprouvées', 'Aucune méthode approuvée enregistrée. Utilisez /methods approve <N> <auteur> | <motif> après /analyze.'))
                    else:
                        lines = []
                        for review in approved:
                            event = review['event']
                            proposal = event['proposal']
                            status = ('remplacée' if review['superseded'] else
                                      'à réexaminer : ' + ', '.join(review['reasons']) if review['potentially_obsolete'] else 'courante')
                            lines.append(f"{proposal['tool']} ({proposal['indicator_type']}) — revue par {event['actor']} le {event['timestamp']} [{status}]")
                        lines.append('Approbations documentaires déclaratives ; aucune autorisation d’exécution.')
                        print(terminal_panel('Revues documentaires', '\n'.join(lines)))
                elif arg.startswith(('approve ', 'approuver ', 'reject ', 'rejeter ')):
                    parts = arg.split(maxsplit=2)
                    verb = parts[0]
                    decision = 'approved' if verb in ('approve', 'approuver') else 'rejected'
                    if len(parts) < 3 or '|' not in parts[2]:
                        raise ValueError('Usage : /methods approve <N> <auteur> | <motif> (ou reject).')
                    number = int(parts[1])
                    actor, reason = [p.strip() for p in parts[2].split('|', 1)]
                    choices = analysis.get('choices', [])
                    if number < 1 or number > len(choices):
                        raise ValueError('Numéro de recommandation invalide ; exécutez /analyze d’abord.')
                    rec = choices[number - 1]['recommendation']
                    confirm = input(f"Confirmer la décision humaine '{decision}' pour {rec['tool']} ? (oui/N) ").strip().lower() == 'oui'
                    entry = reviews.record(rec, decision, actor, reason, human_confirmed=confirm)
                    print(terminal_panel('Validation humaine de méthode', f"Outil : {entry['proposal']['tool']} ({entry['proposal']['indicator_type']})\nDécision documentaire : {entry['decision']} par {entry['actor']}\nHorodatage : {entry['timestamp']}"))
                elif arg.startswith(('stage ', 'preparer-corpus ')):
                    candidate_path = arg.split(maxsplit=1)[1].strip()
                    staged = stage_corpus_file(candidate_path)
                    print(terminal_panel('Mise à jour du corpus en quarantaine', f"Fichier isolé : {staged}\nValidation humaine hors ligne requise avant remplacement du catalogue actif."))
                else:
                    raise ValueError('Sous-commande /methods inconnue ; utilisez list, approve, reject ou stage.')
            elif s == '/investigation' or s.startswith('/investigation '):
                arg = s[len('/investigation'):].strip()
                action_parts = arg.split(maxsplit=1)
                action = action_parts[0].lower() if action_parts else 'status'
                opening_action = action if action in ('create', 'open') else None
                if opening_action:
                    if len(action_parts) != 2:
                        raise ValueError('Usage : /investigation '+action+' <id> [titre]')
                    arg = action_parts[1]
                if not arg or arg in ('status', 'statut'):
                    if not cases.active_case_id:
                        print(terminal_panel('Dossier d’enquête', 'Aucun dossier actif. Utilisez /investigation <id> [titre] pour ouvrir un dossier isolé, ou /investigation list.'))
                    else:
                        info = cases.status()
                        body = (f"Dossier : {info['case_id']}"
                                + (f" — {info['title']}" if info['title'] else '')
                                + f"\nChemin : {info['path']}\nIndices : {info['indicators_count']} ; commandes : {info['prepared_commands_count']} ; contextes : {info['contexts_count']}"
                                + f"\nJournal : {info['journal_entries_count']} événement(s)")
                        print(terminal_panel('Dossier d’enquête', body))
                elif arg in ('list', 'liste'):
                    items = cases.list_cases()
                    if not items:
                        print(terminal_panel('Dossiers d’enquête', 'Aucun dossier d’enquête enregistré.'))
                    else:
                        lines = [f"{it['case_id']} : {it['indicators_count']} indice(s), {it['prepared_commands_count']} commande(s), {it['journal_entries_count']} événement(s)" + ('' if it.get('structure') == 'valid' else ' — dossier inaccessible : contrôle échoué') for it in items]
                        print(terminal_panel('Dossiers d’enquête', '\n'.join(lines)))
                elif arg in ('log', 'journal'):
                    if not cases.active_case_id:
                        print('Aucun dossier actif ; ouvrez un dossier avec /investigation <id>.')
                    else:
                        entries = cases.read_journal()
                        from focus_ui import journal_description
                        lines = [f"#{e['seq']} [{e['timestamp']}] {journal_description(e)}" for e in entries]
                        print(terminal_panel('Journal d’enquête horodaté', '\n'.join(lines)))
                elif action == 'rename':
                    cases.rename_case(action_parts[1] if len(action_parts) > 1 else '')
                    print(safe_display('Dossier renommé : '+cases.status()['title']))
                elif action in ('close', 'fermer', 'archive', 'delete'):
                    if len(action_parts) > 1:
                        raise ValueError('Cette action concerne le dossier actif ; aucun identifiant attendu.')
                    if action == 'delete' and cases.active_case_id:
                        question = ('Supprimer définitivement le dossier '+cases.active_case_id+
                                    ' et tous ses résultats ? [o/N] ')
                        if input(question).strip().lower() not in ('o', 'oui', 'y', 'yes'):
                            print('Suppression annulée.')
                            continue
                    closed = (cases.archive_case() if action == 'archive' else
                              cases.delete_case() if action == 'delete' else cases.close_case())
                    if closed is None:
                        print('Aucun dossier actif.')
                    else:
                        for saved_session in sessions.values():
                            if saved_session: saved_session.reset()
                        analysis = {'choices': []}
                        latest_analysis = None
                        selected_context = None
                        context_enabled = False
                        label = {'archive': 'archivé', 'delete': 'supprimé'}.get(action, 'fermé')
                        print(safe_display(f'Dossier {closed} {label} ; contexte et session isolés réinitialisés.'))
                else:
                    parts = arg.split(maxsplit=1)
                    cid = parts[0]
                    title = parts[1] if len(parts) > 1 else None
                    state = cases.open_case(cid, title=title, create_only=opening_action == 'create',
                                            existing_only=opening_action == 'open')
                    for saved_session in sessions.values():
                        if saved_session: saved_session.reset()
                    analysis = state.get('latest_analysis') or {'choices': []}
                    latest_analysis = analysis if analysis.get('choices') and not analysis.get('errors') else None
                    selected_context = None
                    context_enabled = False
                    info = cases.status(cid)
                    print(terminal_panel(
                        'Dossier d’enquête actif',
                        f"Dossier : {info['case_id']}" + (f" — {info['title']}" if info['title'] else '')
                        + f"\nChemin : {info['path']}\nIndices : {info['indicators_count']} ; commandes : {info['prepared_commands_count']} ; contextes : {info['contexts_count']}"
                    ))
            elif s == '/reset':
                for saved_session in sessions.values():
                    if saved_session: saved_session.reset()
                analysis = {'choices': []}
                latest_analysis = None
                selected_context = None
                context_enabled = False
                print('Session et contexte effacés.')
            elif s == '/context' or (s.startswith('/context ') and s != '/context off'):
                if manager.mode == 'distant':
                    print('Le contexte structuré reste local ; reformulez manuellement les seuls éléments autorisés.')
                elif latest_analysis is None:
                    print('Aucune analyse disponible ; utilisez /analyze TEXT.')
                elif session is None:
                    print('IA non configurée : aucun contexte ne sera transmis.')
                else:
                    selected_context = (context_for_choice(latest_analysis, int(s.split()[1]))
                                        if s != '/context' else latest_analysis)
                    context_enabled = True
                    cases.record_context(selected_context)
                    print('Contexte sélectionné pour les prochains messages IA. Sources et limites incluses ; un contexte identique reste dans l’historique sans copie supplémentaire.')
                    if s != '/context':
                        print(safe_display(selected_context['selection_limits']))
                    print(f'Budget des messages : {session.context_budget} octets, sans suppression silencieuse. La fenêtre du modèle peut être plus petite ; /reset efface l’historique.')
            elif s == '/context off':
                context_enabled = False
                print('Ajout du contexte désactivé ; les tours précédents restent dans l’historique jusqu’à /reset.')
            elif s == '/ai':
                print(terminal_panel('État IA', ('Moteur distant OpenAI : ' + manager.remote.model) if manager.mode == 'distant' else
                      (('Moteur Ollama local configuré : ' + str(model or getattr(adapter, 'model', 'modèle non indiqué')) + ' ; disponibilité non vérifiée.') if session else 'IA non configurée.')))
            elif s == '/settings':
                try:
                    configure_provider(manager, timeout)
                except (EOFError, KeyboardInterrupt):
                    print('\nConfiguration interrompue.')
            elif s == '/models':
                try:
                    names = adapter.list_models()
                    print('Modèles annoncés par le serveur local (exécution locale non certifiée) :')
                    for name in names:
                        print('  ' + safe_display(name))
                    if not names:
                        print('  Aucun modèle annoncé.')
                except (RuntimeErrorLocal, AttributeError) as exc:
                    print('Liste indisponible : ' + safe_display(exc))
                except KeyboardInterrupt:
                    print('\nConsultation interrompue.')
            elif s == '/tools':
                items = indices_outils.inventory()
                print(terminal_panel('Outils — présence locale', '\n'.join(f"{item['id']} : {item['executable_path'] or 'absent'}" for item in items)))
            elif s.startswith('/prepare '):
                result = prepare_interactive(analysis, int(s.split(maxsplit=1)[1]))
                from focus_ui import render_preparation_readable
                show_result('Commande préparée et avertissements', render_preparation_readable, result)
                analysis = dict(analysis, last_preparation=result)
                latest_analysis = analysis
                context_enabled = False
                cases.record_preparation(result)
                print('Résultat non transmis au modèle. /context permet de le sélectionner.')
                # Aucune réponse de modèle ne traite ni ne remplace ce résultat.
            elif s.startswith('/target '):
                context_enabled = False
                latest_analysis = None
                analysis = select_derived(analysis, int(s.split(maxsplit=1)[1]))
                latest_analysis = analysis if not analysis.get('errors') else None
                cases.record_analysis(analysis)
                show_result('Analyse et recommandations', render_analysis, analysis)
                print('Analyse non transmise au modèle. /context permet de la sélectionner.')
            elif s and manager.mode == 'distant' and not s.startswith(('/analyze ', '/indicator ')):
                if s.startswith('/'):
                    print('Commande inconnue ; /help pour les commandes disponibles.'); continue
                try:
                    remote_turn(manager, s)
                except RuntimeIncomplete as exc:
                    print(safe_display(exc) + '\nTexte partiel distant (non vérifié) :\n' + safe_display(exc.partial))
                except RuntimeErrorLocal as exc:
                    print('Erreur IA : ' + safe_display(exc))
                except (EOFError, KeyboardInterrupt):
                    print('\nTransmission interrompue ; aucun repli automatique. Le fournisseur peut avoir traité la demande.')
            elif s.startswith('/analyze ') or s.startswith('/indicator ') or (s and (not s.startswith('/') or Path(s).is_file())):
                explicit = s.startswith(('/analyze ', '/indicator '))
                if explicit:
                    latest_analysis = None
                    context_enabled = False
                new_analysis = None
                if explicit or session is None or indices_outils.extract(s) or s.startswith(('/', './', '../', '~/')):
                    if s.startswith('/indicator '):
                        _, kind, value = s.split(maxsplit=2)
                        new_analysis = analyse(value, kind=kind)
                    else:
                        value = s[len('/analyze '):] if s.startswith('/analyze ') else s
                        new_analysis = analyse(value)
                if new_analysis is not None:
                    analysis = new_analysis
                    latest_analysis = analysis if not analysis.get('errors') else None
                    context_enabled = False
                    cases.record_analysis(analysis)
                    show_result('Analyse et recommandations', render_analysis, analysis)
                    print('Analyse non transmise au modèle. /context permet de la sélectionner.')
                if session and not explicit:
                    try:
                        print(f'Réponse IA en cours (délai maximal {timeout:g} s ; Ctrl+C pour interrompre l’attente)…', flush=True)
                        started = time.monotonic()
                        answer = session.respond(s, selected_context if context_enabled else None)
                        if getattr(session, 'last_injection_alerts', None):
                            print(safe_display('Alerte sécurité : motif d’injection de prompt détecté et isolé (' + ', '.join(session.last_injection_alerts) + ').'))
                        print(terminal_panel('Réponse du modèle (non vérifiée)', answer))
                        print(f'Temps de réponse : {time.monotonic() - started:.1f} s.')
                    except RuntimeIncomplete as exc:
                        print(safe_display(exc) + '\nTexte partiel (non vérifié, tour non enregistré) :\n' + safe_display(exc.partial))
                    except RuntimeErrorLocal as exc:
                        print('Erreur IA : ' + safe_display(exc))
                    except KeyboardInterrupt:
                        print('\nInférence interrompue ; tour non enregistré, session conservée. Le calcul du serveur peut continuer.')
            elif s:
                print('Commande inconnue ; /help pour les commandes disponibles.')
        except (EOFError, KeyboardInterrupt):
            print('\nFin de session.'); return 0
        except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
            analysis = {'choices': []}
            latest_analysis = None
            context_enabled = False
            print('Opération refusée : ' + safe_display(exc))


TUI_SECTIONS = ('Conversation', 'Enquête', 'Aide')


def tui_section(text):
    """Classe les échanges selon la commande saisie, sans interpréter la réponse IA."""
    normalized = normalize_command(text)
    command = normalized.split(maxsplit=1)[0] if normalized else ''
    return {'/analyze': 1, '/indicator': 1, '/target': 1, '/tools': 1,
            '/prepare': 1, '/investigation': 1, '/methods': 1, '/audit': 1, '/search': 1,
            '/help': 2, '/settings': 2, '/ai': 2,
            '/models': 2, '/context': 2, '/reset': 2}.get(command, 0)


def run_tui(arguments=None, **kwargs):
    """Lance le moteur REPL interactif moderne Focus."""
    try:
        from focus_repl import run_focus_repl
        runner = run_focus_repl
    except ImportError:
        from focus_ui import run_focus_tui
        runner = run_focus_tui
    if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get('TERM') in ('', 'dumb'):
        print('TUI indisponible sur ce terminal ; retour au terminal classique.', file=sys.stderr)
        return None
    if kwargs:
        return runner(**kwargs)
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--model')
    p.add_argument('--port', type=int)
    p.add_argument('--timeout', type=float)
    p.add_argument('--context-budget', type=int)
    p.add_argument('--case')
    parsed, _ = p.parse_known_args(arguments or [])
    preferences = installation.load_preferences()
    values = dict(
        model=parsed.model if parsed.model is not None else preferences.get('model'),
        port=parsed.port if parsed.port is not None else preferences.get('port', 11434),
        timeout=parsed.timeout if parsed.timeout is not None else preferences.get('timeout', DEFAULT_TIMEOUT),
        context_budget=parsed.context_budget if parsed.context_budget is not None else preferences.get('context_budget', DEFAULT_CONTEXT_BUDGET),
    )
    installation.validate_preferences(values)
    return runner(
        model=values['model'],
        port=values['port'],
        timeout=values['timeout'],
        context_budget=values['context_budget'],
        case_id=parsed.case,
    )


def main():
    p = argparse.ArgumentParser(prog='uchambuzi', description='Assistant local pour l’investigation numérique ; opérations sous contrôle humain.')
    p.add_argument('--tui', action='store_true', help='ouvrir l’interface TUI Focus (comportement par défaut sur un terminal interactif)')
    p.add_argument('--legacy-tui', action='store_true', help='forcer l’ancienne interface curses (mode dégradé)')
    p.add_argument('--no-tui', '--classic', dest='no_tui', action='store_true', help='forcer le mode texte séquentiel (accessibilité / scripts)')
    p.add_argument('--model', help='modèle Ollama déjà présent localement')
    p.add_argument('--port', type=int)
    p.add_argument('--timeout', type=float,
                   help='délai total par requête IA, en secondes : 300 par défaut, > 0 et <= 600')
    p.add_argument('--context-budget', type=int,
                   help='budget des messages locaux en octets : 16000 par défaut, 1024 à 128000 ; refus sans troncature')
    p.add_argument('--case', help='identifiant du dossier d’enquête isolé (uchambuzi-data/cases/<id>)')
    p.add_argument('action', nargs='?', choices=('doctor', 'update', 'repair', 'uninstall'))
    p.add_argument('--save-config', action='store_true', help='enregistrer explicitement les préférences locales puis quitter')
    p.add_argument('--source', type=Path, help='chemin du dépôt ou de l’archive source locale')
    p.add_argument('--release', help='tag GitHub explicite a telecharger et verifier (update uniquement)')
    p.add_argument('--yes', action='store_true', help='confirmer sans invite interactive (update, repair, uninstall)')
    p.add_argument('--purge-data', action='store_true', help='supprimer explicitement les données utilisateur (uchambuzi-data) lors de uninstall')
    p.add_argument('--purge-ai', '--purge-ollama', dest='purge_ai', action='store_true',
                   help='désinstaller explicitement Ollama et ses données locales lors de uninstall')
    p.add_argument('--remove-model', dest='remove_models', action='append', default=[],
                   help='retirer explicitement un modèle IA local lors de uninstall')
    p.add_argument('--version', action='version', version=f'UCHAMBUZI {VERSION}')
    a = p.parse_args()
    if a.release and (a.action != 'update' or a.source is not None):
        p.error('--release exige update et ne se combine pas avec --source')
    try:
        if a.action == 'doctor': return doctor()
        if a.action == 'update': return update_release(a.release, a.yes) if a.release else update(a.source, a.yes)
        if a.action == 'repair': return repair(a.source, a.yes)
        if a.action == 'uninstall':
            return uninstall(yes=a.yes, purge_data=a.purge_data, purge_ai=a.purge_ai, remove_models=a.remove_models)
        if a.source: return install(a.source)
        preferences = installation.load_preferences()
        values = dict(model=a.model if a.model is not None else preferences.get('model'),
                      port=a.port if a.port is not None else preferences.get('port', 11434),
                      timeout=a.timeout if a.timeout is not None else preferences.get('timeout', DEFAULT_TIMEOUT),
                      context_budget=a.context_budget if a.context_budget is not None else preferences.get('context_budget', DEFAULT_CONTEXT_BUDGET))
        installation.validate_preferences(values)
        if a.save_config:
            installation.save_preferences(values)
            print(safe_display('Configuration enregistrée : ' + str(installation.user_data_path() / 'config/settings.json')))
            return 0
        interactive_tty = (
            sys.stdin.isatty()
            and sys.stdout.isatty()
            and os.environ.get('TERM') not in ('', 'dumb')
            and not os.environ.get('UCHAMBUZI_NO_TUI')
        )
        if (a.tui or interactive_tty) and not getattr(a, 'no_tui', False):
            if not interactive_tty:
                print('retour au terminal classique', file=sys.stderr)
            else:
                if getattr(a, 'legacy_tui', False) or os.environ.get('UCHAMBUZI_LEGACY_TUI'):
                    from focus_ui import run_focus_tui
                    runner = run_focus_tui
                else:
                    try:
                        from focus_repl import run_focus_repl
                        runner = run_focus_repl
                    except ImportError:
                        from focus_ui import run_focus_tui
                        runner = run_focus_tui
                result = runner(
                    model=values['model'],
                    port=values['port'],
                    timeout=values['timeout'],
                    context_budget=values['context_budget'],
                    case_id=a.case,
                )
                if result is not None:
                    return result
        if a.case is not None:
            return interactive(values['model'], values['port'], values['timeout'],
                               context_budget=values['context_budget'], case_id=a.case)
        return interactive(values['model'], values['port'], values['timeout'], context_budget=values['context_budget'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Opération refusée : ' + safe_display(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
