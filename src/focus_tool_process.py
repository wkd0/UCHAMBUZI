# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_tool_process.py
# Role          : Processus bornes sans shell
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Linux/POSIX : sortie bornee, groupe de processus et environnement minimal."""
from dataclasses import dataclass
import datetime
import os
import selectors
import signal
import subprocess
import time
import tempfile

@dataclass(frozen=True)
class ProcessResult:
    status: str
    returncode: int | None
    stdout: bytes = b''
    stderr: bytes = b''
    started_at: str | None = None
    finished_at: str | None = None
    pid: int | None = None


def run(program, args, *, timeout=5.0, output_limit=65536, cancel=None):
    # A real, private, disposable HOME supports tools such as binwalk without
    # loading the user's plugins/configuration or writing into their home.
    with tempfile.TemporaryDirectory(prefix='uchambuzi-tool-') as home:
        return _run(program, args, timeout=timeout, output_limit=output_limit,
                    cancel=cancel, home=home)


def _run(program, args, *, timeout, output_limit, cancel, home):
    if type(output_limit) is not int or not 0 < timeout <= 300 or not 0 < output_limit <= 4 * 1024 * 1024:
        raise ValueError('Bornes invalides')
    if cancel is not None and cancel.is_set():
        return ProcessResult('cancelled', None)
    env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': home, 'XDG_CONFIG_HOME': home + '/.config',
           'PAGER': 'cat', 'MANPAGER': 'cat'}
    try:
        child = subprocess.Popen([program, *args], shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, start_new_session=True,
            close_fds=True, cwd='/')
    except OSError:
        return ProcessResult('spawn_error', None)
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chunks = [bytearray(), bytearray()]
    status = None
    deadline = time.monotonic() + timeout
    def stop():
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        with selectors.DefaultSelector() as sel:
            for i, pipe in enumerate((child.stdout, child.stderr)):
                os.set_blocking(pipe.fileno(), False)
                sel.register(pipe, selectors.EVENT_READ, i)
            while sel.get_map() or child.poll() is None:
                if cancel is not None and cancel.is_set():
                    status = 'cancelled'
                    break
                if time.monotonic() >= deadline:
                    status = 'timeout'
                    break
                for key, _ in sel.select(min(.05, max(0, deadline-time.monotonic()))):
                    block = os.read(key.fileobj.fileno(), 8192)
                    if not block:
                        sel.unregister(key.fileobj)
                        continue
                    remaining = output_limit - sum(map(len, chunks))
                    chunks[key.data].extend(block[:remaining])
                    if len(block) > remaining:
                        status = 'output_limit'
                        break
                if status:
                    break
    finally:
        stop()  # Kill surviving descendants even when the direct child has exited.
        child.wait()
        child.stdout.close()
        child.stderr.close()
    return ProcessResult(status or ('succeeded' if child.returncode == 0 else 'failed'),
                         child.returncode, bytes(chunks[0]), bytes(chunks[1]), started_at,
                         datetime.datetime.now(datetime.timezone.utc).isoformat(), child.pid)
