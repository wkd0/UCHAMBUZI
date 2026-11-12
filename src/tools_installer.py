# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : tools_installer.py
# Role          : Installation locale des artefacts explicitement verifies
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Installation hors ligne des copies vendor et des imports vérifiés.

Le catalogue fige les empreintes ; aucune récupération réseau implicite.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import subprocess
import tempfile
import zipfile


class InstallerError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _component(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', value) or value in ('.', '..'):
        raise InstallerError('Identifiant, version ou nom de fichier invalide.')
    return value


def _safe_zip(archive, destination):
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = info.filename
            path = PurePosixPath(name)
            mode = info.external_attr >> 16
            if (not name or '\\' in name or path.is_absolute() or '..' in path.parts
                    or (mode & 0o170000) == 0o120000):
                raise InstallerError('Chemin ou lien interdit dans l’archive.')
        zf.extractall(destination)


def _is_bytecode_cache(path):
    """Python may create these derived files after installation/use."""
    parts = PurePosixPath(path).parts
    return len(parts) >= 2 and parts[-2] == '__pycache__' and parts[-1].endswith('.pyc')


def _bundle_python(filename):
    """Use the ABI pinned by our wheel bundle, independently of Kali's default."""
    match = re.search(r'-cp(\d)(\d+)\.zip$', filename)
    if not match:
        return os.sys.executable
    version = tuple(map(int, match.groups()))
    if os.sys.version_info[:2] == version:
        return os.sys.executable
    program = shutil.which(f'python{version[0]}.{version[1]}', path='/usr/bin:/bin')
    if program is None:
        raise InstallerError(f'Ce bundle exige Python {version[0]}.{version[1]} et son paquet venv ; aucune dépendance téléchargée.')
    return program


class ToolsInstaller:
    def __init__(self, catalog, root=None, case_manager=None, confirm=None, output=print):
        self.catalog = tuple(catalog)
        self.vendor_root = Path(__file__).resolve().parent.parent / 'vendor'
        # Réservé au futur dépôt approuvé ; aucune récupération réseau implicite.
        self.repository_url = os.environ.get('UCHAMBUZI_TOOLS_URL', '')
        self.root = Path(root) if root is not None else Path(os.environ.get(
            'UCHAMBUZI_TOOLS_ROOT', Path.home() / '.local/share/uchambuzi-data/tools'))
        self.case_manager = case_manager
        self.confirm = confirm or (lambda prompt: input(prompt).strip().lower() in ('o', 'oui'))
        self.output = output

    def _tool(self, name):
        matches = [item for item in self.catalog if name in (item.get('id'), item.get('name'))]
        if len(matches) != 1:
            raise InstallerError('Outil absent ou ambigu dans le catalogue.')
        tool = matches[0]
        _component(tool['id'])
        return tool

    def _artifact(self, tool):
        a = tool.get('artifact')
        if tool.get('source') != 'vendored' or not isinstance(a, dict):
            raise InstallerError('Aucune copie vérifiée disponible pour cet outil.')
        if tool.get('license') == 'NOASSERTION':
            raise InstallerError('Licence non déclarée : distribution et installation bloquées.')
        _component(tool.get('version_pin'))
        _component(a.get('file'))
        _component(tool.get('executable'))
        if a.get('install') in ('apt', 'pipx'):
            command = ('apt-get install ./'+a['file'] if a['install'] == 'apt' else 'pipx install --pip-args="--no-index --no-deps" ./'+a['file'])
            self.output('Commande prévue (sans sudo implicite) : '+command)
            raise InstallerError('Méthode '+a['install']+' non disponible pour les copies tierces dans cette version ; aucune commande exécutée.')
        if not re.fullmatch(r'[0-9a-f]{64}', str(a.get('sha256', ''))) or a.get('install') not in ('binary', 'venv'):
            raise InstallerError('Artefact ou méthode non pris en charge.')
        return a

    def _source(self, tool):
        """Prefer the project copy; never hide a corrupt vendor copy by fallback."""
        a = self._artifact(tool)
        folder = self.vendor_root / tool['id']
        for candidate in (folder / 'bin' / a['file'], folder / a['file']):
            if candidate.exists() or candidate.is_symlink():
                if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(self.vendor_root.resolve()):
                    raise InstallerError('Artefact vendor interdit.')
                return candidate
        return self.root / '.imports' / a['sha256']

    def verify_artifact(self, name):
        tool = self._tool(name)
        source = self._source(tool)
        return source.is_file() and not source.is_symlink() and digest(source) == self._artifact(tool)['sha256']

    def _target(self, tool):
        return self.root / _component(tool['id']) / _component(tool['version_pin'])

    def _approve(self, action, tool, source, method):
        self.output(f"{action} : {tool['name']} | source : {source} | version : {tool['version_pin']} | cible : {self._target(tool)} | méthode : {method}")
        return self.confirm('Confirmer [o/N] : ')

    def _record(self, action, tool, result):
        if self.case_manager and self.case_manager.active_case_id:
            self.case_manager.record_execution({'tool': tool['id'], 'operation': action, 'result': result, 'version': tool.get('version_pin')})

    def import_archive(self, path):
        source = Path(path)
        if not source.is_file() or source.is_symlink():
            raise InstallerError('Archive locale introuvable.')
        sha = digest(source)
        matches = [(t, t.get('artifact')) for t in self.catalog if isinstance(t.get('artifact'), dict)
                   and t['artifact'].get('sha256') == sha]
        if len(matches) != 1:
            raise InstallerError('Archive inconnue ou ambiguë dans le catalogue.')
        tool, artifact = matches[0]
        self._artifact(tool)
        if not self._approve('Importer', tool, str(source), 'copie locale'):
            return False
        folder = self.root / '.imports'
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, folder / sha)
        self._record('import', tool, 'importé')
        return True

    def executable(self, name):
        """Résout une installation vérifiée ou un binaire vendor de même empreinte."""
        tool = self._tool(name)
        if not tool.get('artifact'):
            return None
        target = self._target(tool)
        if target.exists():
            if not self.verify(name):
                return None
            matches = [p for p in target.rglob(tool['executable'])
                       if p.is_file() and not p.is_symlink() and os.access(p, os.X_OK)]
            return str(matches[0]) if len(matches) == 1 else None
        artifact = self._artifact(tool)
        source = self._source(tool)
        if (artifact['install'] == 'binary' and source.name == tool['executable']
                and source.resolve().is_relative_to(self.vendor_root.resolve())
                and self.verify_artifact(name) and os.access(source, os.X_OK)):
            return str(source)
        return None

    def setup(self):
        """Prépare toutes les copies embarquées hors ligne après un accord global."""
        tools = [t for t in self.catalog if t.get('source') == 'vendored' and t.get('artifact')]
        for tool in tools:
            self.output(f"Préparer : {tool['id']} {tool['version_pin']} → {self._target(tool)}")
        if not self.confirm('Préparer les copies embarquées vérifiées, sans réseau ? [o/N] : '):
            return False
        success = True
        for tool in tools:
            try:
                if not self.verify_artifact(tool['id']):
                    raise InstallerError('Empreinte SHA-256 incorrecte ou artefact absent.')
                if self._target(tool).exists():
                    if not self.verify(tool['id']):
                        raise InstallerError('Installation existante altérée ; aucun remplacement automatique.')
                else:
                    self.install(tool['id'], approved=True)
                self.output(tool['id'] + ' : prêt')
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                success = False
                self.output(tool['id'] + ' : échec — ' + str(exc))
        return success

    def _system_install(self, tool, action):
        # Noms de paquets figés ; aucune chaîne utilisateur ne devient commande.
        packages = {'dig': 'bind9-dnsutils', 'exiftool': 'libimage-exiftool-perl',
                    'strings': 'binutils', 'theharvester': 'theharvester'}
        package = packages.get(tool['id'], tool['id'])
        argv = ['apt-get', 'install', package]
        self.output('Commande système (sans sudo implicite) : '+shlex.join(argv))
        if not self.confirm('Exécuter cette commande apt ? [o/N] : '):
            return False
        result = subprocess.run(argv, check=False)
        self._record(action, tool, 'installé' if result.returncode == 0 else 'échec apt')
        if result.returncode:
            raise InstallerError('apt a échoué ; les privilèges système restent à la charge de l’utilisateur.')
        return True

    def install(self, name, *, approved=False):
        tool = self._tool(name)
        if tool.get('source') == 'kali':
            return self._system_install(tool, 'install')
        a = self._artifact(tool)
        source = self._source(tool)
        if not source.is_file() or source.is_symlink():
            raise InstallerError('Artefact absent de vendor/ et des imports locaux.')
        if not approved and not self._approve('Installer', tool, str(source), a['install']):
            return False
        if digest(source) != a['sha256']:
            self._record('install', tool, 'empreinte incorrecte')
            raise InstallerError('Empreinte SHA-256 incorrecte.')
        target = self._target(tool)
        if target.exists():
            raise InstallerError('Cette version est déjà installée.')
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=target.parent) as work:
            stage = Path(work) / 'payload'
            stage.mkdir()
            if a['install'] == 'binary':
                if zipfile.is_zipfile(source):
                    _safe_zip(source, stage)
                    candidates = [p for p in stage.rglob(tool['executable']) if p.is_file()]
                    if len(candidates) != 1:
                        raise InstallerError('Binaire absent ou ambigu dans l’archive.')
                    binary = candidates[0]
                else:
                    binary = stage / tool['executable']
                    shutil.copyfile(source, binary)
                binary.chmod(0o755)
            else:
                checked = Path(work) / 'checked'
                _safe_zip(source, checked)
                subprocess.run([_bundle_python(a['file']), '-m', 'venv', str(stage)], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if source.suffix == '.whl' or a['file'].endswith('.whl'):
                    wheel = Path(work) / a['file']
                    shutil.copyfile(source, wheel)
                    args = ['--no-deps', str(wheel)]
                else:
                    wheels = sorted(checked.glob('*.whl'))
                    if not wheels:
                        raise InstallerError('Bundle Python sans wheels.')
                    if tool['id'] == 'blackbird':
                        shutil.copytree(checked / 'app', stage / 'app')
                        args = ['--find-links', str(checked), '-r', str(stage / 'app/requirements.txt')]
                    else:
                        args = ['--find-links', str(checked), tool['id']]
                subprocess.run([str(stage / 'bin/python'), '-m', 'pip', 'install',
                                '--no-index', '--disable-pip-version-check', *args], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if tool['id'] == 'blackbird':
                launcher = stage / 'bin/blackbird'
                launcher.write_text('#!' + str(target / 'bin/python') + '\n'
                    'import os, sys, shutil, signal, subprocess, tempfile\n'
                    'from pathlib import Path\n'
                    'if any(a == "-ai" or (a.startswith("--") and any(flag.startswith(a.split("=")[0]) for flag in ("--ai", "--setup-ai"))) for a in sys.argv[1:]):\n'
                    '    sys.exit("Fonctions avec cle API indisponibles dans UCHAMBUZI")\n'
                    'root = Path(__file__).resolve().parents[1]\n'
                    'runtime = root.parent.parent / ".runtime"\n'
                    'runtime.mkdir(mode=0o700, exist_ok=True)\n'
                    'signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))\n'
                    'with tempfile.TemporaryDirectory(prefix="blackbird-", dir=runtime) as work:\n'
                    '    app = Path(work) / "app"\n'
                    '    shutil.copytree(root / "app", app)\n'
                    '    result = subprocess.call([str(root / "bin/python"), str(app / "blackbird.py"), "--no-update", *sys.argv[1:]], cwd=app)\n'
                    'sys.exit(result)\n', encoding='utf-8')
                launcher.chmod(0o755)
            if a['install'] == 'venv':
                for script in (stage / 'bin').iterdir():
                    if script.is_file() and not script.is_symlink():
                        data = script.read_bytes()
                        if data.startswith(b'#!'):
                            script.write_bytes(data.replace(os.fsencode(stage), os.fsencode(target), 1))
            files = {str(p.relative_to(stage)): digest(p) for p in stage.rglob('*') if p.is_file() and not p.is_symlink()}
            links = {str(p.relative_to(stage)): os.readlink(p) for p in stage.rglob('*') if p.is_symlink()}
            (stage / '.uchambuzi.json').write_text(json.dumps(
                {'artifact_sha256': a['sha256'], 'files': files, 'symlinks': links}, sort_keys=True), encoding='utf-8')
            stage.rename(target)
        self._record('install', tool, 'installé')
        return True

    def verify(self, name):
        tool = self._tool(name)
        a = self._artifact(tool)
        target = self._target(tool)
        if target.is_symlink() or not target.is_dir() or not self.verify_artifact(name):
            return False
        try:
            manifest = json.loads((target / '.uchambuzi.json').read_text(encoding='utf-8'))
            files = manifest['files']
            valid = (manifest['artifact_sha256'] == a['sha256'] and
                     isinstance(files, dict) and bool(files))
            links = manifest.get('symlinks')
            if links is not None and not isinstance(links, dict):
                valid = False
            if links is None:
                # Older venv manifests did not record their interpreter links.
                # Accept only standard links into root-owned system Python dirs.
                links = {}
            expected = set()
            for key, value in (files.items() if isinstance(files, dict) else ()):
                rel = PurePosixPath(key) if isinstance(key, str) else PurePosixPath('/')
                if (not isinstance(key, str) or not key or rel.is_absolute()
                        or any(part in ('', '.', '..') for part in rel.parts)):
                    valid = False
                    continue
                expected.add(key)
                path = target.joinpath(*rel.parts)
                parents = tuple(path.parents)
                if (any(parent.is_symlink() for parent in parents if parent != target)
                        or path.is_symlink() or not path.is_file()
                        or not isinstance(value, str) or digest(path) != value):
                    valid = False
            actual = set()
            actual_links = {}
            for path in target.rglob('*'):
                if path.is_symlink():
                    relative = path.relative_to(target).as_posix()
                    actual_links[relative] = os.readlink(path)
                    continue
                if path == target / '.uchambuzi.json' or not path.is_file():
                    continue
                relative = path.relative_to(target).as_posix()
                actual.add(relative)
            if manifest.get('symlinks') is None:
                for relative, link_target in actual_links.items():
                    link = target / relative
                    linked = link.resolve()
                    if link.is_dir():
                        if relative != 'lib64' or link_target != 'lib' or linked != (target / 'lib').resolve():
                            valid = False
                        else:
                            links[relative] = link_target
                    else:
                        if (not re.fullmatch(r'bin/python(?:3(?:\.\d+)?)?', relative)
                                or linked.parent not in (Path('/usr/bin'), Path('/usr/local/bin'))
                                or not re.fullmatch(r'python(?:3(?:\.\d+)?)?', linked.name)
                                or not linked.is_file() or not os.access(linked, os.X_OK)):
                            valid = False
                        else:
                            links[relative] = link_target
            else:
                for relative in actual_links:
                    link = target / relative
                    linked = link.resolve()
                    if (link.is_dir() and not linked.is_relative_to(target.resolve())):
                        valid = False
                    elif not link.is_dir() and not linked.is_relative_to(target.resolve()):
                        if (not re.fullmatch(r'bin/python(?:3(?:\.\d+)?)?', relative)
                                or linked.parent not in (Path('/usr/bin'), Path('/usr/local/bin'))
                                or not re.fullmatch(r'python(?:3(?:\.\d+)?)?', linked.name)
                                or not linked.is_file() or not os.access(linked, os.X_OK)):
                            valid = False
            extra = actual - expected
            valid = valid and expected <= actual and all(_is_bytecode_cache(path) for path in extra) and actual_links == links
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
        self._record('verify', tool, 'valide' if valid else 'échec')
        return valid

    def remove(self, name):
        tool = self._tool(name)
        self._artifact(tool)
        target = self._target(tool)
        if not target.is_dir() or target.is_symlink():
            raise InstallerError('Version installée introuvable.')
        if not self._approve('Supprimer', tool, 'installation locale', 'suppression'):
            return False
        shutil.rmtree(target)
        if not any(target.parent.iterdir()):
            target.parent.rmdir()
        self._record('remove', tool, 'supprimé')
        return True

    def update(self, name):
        # Une nouvelle version du catalogue est nécessaire ; aucune découverte réseau.
        return self.install(name)

    def handle(self, arguments):
        """Point d'entrée pour le routeur /tools du lot d'intégration."""
        if arguments.strip() in ('setup', 'install all'):
            return self.setup()
        parts = arguments.split(maxsplit=1)
        if len(parts) != 2 or parts[0] not in ('install', 'update', 'remove', 'verify', 'import'):
            raise InstallerError('Usage : /tools install|update|remove|verify <nom> ou /tools import <fichier>')
        action, value = parts
        if action == 'import':
            return self.import_archive(value)
        if action == 'verify':
            valid = self.verify_artifact(value)
            self._record('verify', self._tool(value), 'valide' if valid else 'échec')
            self.output('Artefact SHA-256 : ' + ('valide' if valid else 'échec'))
            return valid
        return getattr(self, action)(value)

    def custom_tools(self):
        folder = self.root / 'custom'
        return [(p.name, 'unverified') for p in sorted(folder.iterdir()) if p.is_file()] if folder.is_dir() else []
