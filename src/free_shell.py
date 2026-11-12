# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : free_shell.py
# Role          : Shell Bash libre interactif et capture locale des sorties
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Only explicit human input enters this shell, never model or tool output."""
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import uuid
from datetime import datetime, timezone

from rich.text import Text

import installation
from conversation import safe_display, detect_prompt_injection


def execute_shell(command, directory):
    """Hand the real terminal to util-linux script (PTY, sudo, resize, Ctrl+C).

    The caller owns approval and terminal suspension. No timeout or whitelist:
    this is the investigator's Bash, with the investigator's Unix permissions.
    Each invocation starts a fresh shell; /terminal preserves state until exit.
    """
    if not shutil.which('script'):
        raise ValueError('Le paquet util-linux (script) est requis pour le terminal.')
    directory = Path(directory)
    installation.no_links(directory)
    workspace = directory / 'workspace'
    installation.private_directory(workspace)
    logs = directory / 'shell'
    installation.private_directory(logs)
    log = logs / (uuid.uuid4().hex + '.log')
    # Exclusive private creation, including while sudo or other children run.
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    started = datetime.now(timezone.utc).isoformat()
    shell_command = '/bin/bash -i' if command is None else '/bin/bash -c ' + shlex.quote(command)
    environment = dict(os.environ, SHELL='/bin/bash')
    result = subprocess.run(['script', '--quiet', '--return', '--flush',
                             '--command', shell_command, '--log-out', str(log.resolve())],
                            cwd=workspace, env=environment)
    # Hash the full raw transcript without putting an unbounded log in memory.
    digest = hashlib.sha256()
    with log.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block)
        stream.seek(max(0, stream.tell() - 24000))
        decoded = stream.read().decode('utf-8', errors='replace').replace('\r\n', '\n')
        excerpt = safe_display(Text.from_ansi(decoded).plain)
    return dict(tool='bash', command=command if command is not None else '/bin/bash -i',
                activity='unrestricted', cwd=str(workspace), started_at=started,
                finished_at=datetime.now(timezone.utc).isoformat(), returncode=result.returncode,
                transcript=str(log), transcript_sha256=digest.hexdigest(),
                stdout_excerpt=excerpt, excerpt_truncated=log.stat().st_size > 24000,
                detected_patterns=detect_prompt_injection([excerpt]))
