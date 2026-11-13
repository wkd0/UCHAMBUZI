# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_responses_runtime.py
# Role          : Transport distant Responses explicite et borne
#
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Transport HTTPS Responses ; pas de proxy, outils ni consentement implicite.

Le rappel ``on_chunk`` reçoit la réponse en une fois après validation complète :
ce transport n'implémente pas encore le streaming incrémental.
"""
import http.client
import ipaddress
import json
import math
import os
import re
import socket
import threading
import time
from urllib.parse import urlsplit

from conversation import (SYSTEM, RuntimeCancelled, RuntimeErrorLocal,
                          RuntimeIncomplete, RuntimeTimeout, ProviderRefusalError,
                          interruptible_http, is_policy_error, is_provider_refusal)

_MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}\Z')
_ENV = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,127}\Z')
_HOST = re.compile(r'[A-Za-z0-9.-]{1,253}\Z')
_PATH = re.compile(r'(?:/[A-Za-z0-9._~-]+)*\Z')
_MAX_REQUEST = 128_000
_MAX_RESPONSE = 2_000_000


class ResponsesRuntime:
    """Un fournisseur explicite ; chaque appel exige un accord humain distinct."""

    requires_consent = True
    _CONFIG_FIELDS = frozenset(('model', 'family', 'model_family', 'api_key_env', 'timeout',
                                'host', 'port', 'base_url', 'path'))

    def __setattr__(self, name, value):
        if getattr(self, '_config_sealed', False) and name in self._CONFIG_FIELDS:
            raise AttributeError('Configuration du fournisseur immuable ; créez un nouvel adaptateur.')
        object.__setattr__(self, name, value)

    def __init__(self, model, base_url, *, family, api_key_env, timeout=60.0):
        if not isinstance(model, str) or not _MODEL.fullmatch(model):
            raise ValueError('Nom de modèle invalide.')
        if family not in ('openai', 'grok'):
            raise ValueError('Famille de modèle non prise en charge.')
        if not isinstance(api_key_env, str) or not _ENV.fullmatch(api_key_env):
            raise ValueError('Nom de variable API invalide.')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError('Délai distant invalide.')
        if (not isinstance(base_url, str) or len(base_url) > 1024
                or any(ord(c) <= 32 or ord(c) >= 127 for c in base_url)
                or '\\' in base_url or '?' in base_url or '#' in base_url):
            raise ValueError('Adresse distante invalide.')
        try:
            parsed = urlsplit(base_url)
            port = parsed.port if parsed.port is not None else 443
        except ValueError:
            raise ValueError('Adresse distante invalide.') from None
        hostname = parsed.hostname or ''
        if ':' in hostname:
            try:
                ipaddress.IPv6Address(hostname)
                valid_host = True
            except ValueError:
                valid_host = False
        else:
            valid_host = bool(_HOST.fullmatch(hostname)) and '..' not in hostname
        if (parsed.scheme != 'https' or not parsed.netloc or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or not valid_host or not 1 <= port <= 65535
                or not _PATH.fullmatch(parsed.path.rstrip('/'))
                or any(part in ('.', '..') for part in parsed.path.split('/'))):
            raise ValueError('Adresse distante HTTPS invalide.')
        self.model, self.family = model, family
        self.model_family = family
        self.api_key_env, self.timeout = api_key_env, float(timeout)
        self.host, self.port = parsed.hostname, port
        self.base_url = base_url.rstrip('/')
        self.path = parsed.path.rstrip('/') + '/responses'
        self._cancel_request = None
        self._turn_lock = threading.Lock()
        self.last_stats = None
        self._config_sealed = True

    def cancel(self):
        """Interrompt seulement la requête de cet adaptateur, si elle existe."""
        interrupt = self._cancel_request
        if interrupt is not None:
            interrupt()

    def preview_payload(self, messages):
        """Contenu exact de la requête, sans en-têtes ni clé."""
        return {'model': self.model, 'input': messages, 'stream': False, 'store': False}

    def _payload(self, messages, key):
        if (not isinstance(messages, list) or not 2 <= len(messages) <= 101
                or not isinstance(messages[0], dict)
                or not isinstance(messages[0].get('content'), str)
                or not messages[0]['content'].startswith(SYSTEM)):
            raise RuntimeErrorLocal('Structure de messages distants refusée.')
        for index, message in enumerate(messages):
            if (type(message) is not dict or set(message) != {'role', 'content'}
                    or not isinstance(message['content'], str) or not message['content'].strip()
                    or (index == 0 and message['role'] != 'system')
                    or (index > 0 and message['role'] not in ('user', 'assistant'))
                    or key in message['content']):
                raise RuntimeErrorLocal('Structure ou contenu des messages distants refusé.')
        if messages[-1]['role'] != 'user' or key in self.model or key in self.base_url:
            raise RuntimeErrorLocal('Structure ou contenu des messages distants refusé.')
        payload = self.preview_payload(messages)
        try:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        except (TypeError, ValueError, UnicodeError):
            raise RuntimeErrorLocal('Messages distants invalides.') from None
        if len(body) > _MAX_REQUEST:
            raise RuntimeErrorLocal('Contexte distant trop volumineux.')
        return body

    @staticmethod
    def _answer(data, key):
        if not isinstance(data, dict) or not isinstance(data.get('output'), list):
            raise RuntimeErrorLocal('Réponse distante invalide.')
        if data.get('error') is not None:
            raise RuntimeErrorLocal('Erreur signalée par le fournisseur distant.')
        if data.get('status') == 'completed' and data.get('incomplete_details') is not None:
            raise RuntimeErrorLocal('Statut de réponse distante contradictoire.')
        pieces = []
        for item in data['output']:
            if not isinstance(item, dict):
                raise RuntimeErrorLocal('Réponse distante invalide.')
            if item.get('tool_calls') or item.get('function_call'):
                raise RuntimeErrorLocal('Appel d’outil distant non pris en charge.')
            kind = item.get('type')
            if kind == 'reasoning':
                continue
            if kind != 'message' or item.get('role') != 'assistant':
                raise RuntimeErrorLocal('Appel d’outil ou réponse distante non prise en charge.')
            if item.get('status') not in (None, 'completed') or not isinstance(item.get('content'), list):
                raise RuntimeErrorLocal('Message distant invalide.')
            for content in item['content']:
                if not isinstance(content, dict):
                    raise RuntimeErrorLocal('Contenu distant invalide.')
                if content.get('type') == 'refusal':
                    raise ProviderRefusalError('Requête refusée par le fournisseur.')
                if content.get('type') != 'output_text' or not isinstance(content.get('text'), str):
                    raise RuntimeErrorLocal('Contenu distant non pris en charge.')
                pieces.append(content['text'])
        answer = ''.join(pieces).replace(key, '[clé masquée]')
        if data.get('status') != 'completed':
            raise RuntimeIncomplete(answer, 'réponse distante non terminée')
        if not answer.strip():
            raise RuntimeErrorLocal('Réponse distante vide.')
        if is_provider_refusal(answer):
            raise ProviderRefusalError('Requête refusée par le fournisseur.')
        return answer

    def chat(self, messages, *, consent=False, on_chunk=None, cancellation=None):
        if consent is not True:
            raise RuntimeErrorLocal('Consentement explicite requis pour chaque requête distante.')
        key = os.environ.get(self.api_key_env, '')
        if (not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key)):
            raise RuntimeErrorLocal('Clé API absente ou invalide dans la variable configurée.')
        if on_chunk is not None and not callable(on_chunk):
            raise RuntimeErrorLocal('Rappel de réponse invalide.')
        body = self._payload(messages, key)
        if cancellation is not None:
            cancellation.check()
        if not self._turn_lock.acquire(blocking=False):
            raise RuntimeErrorLocal('Une requête distante est déjà en cours.')
        deadline = time.monotonic() + self.timeout
        connection = response = timer = None
        expired, cancelled = threading.Event(), threading.Event()
        try:
            connection = http.client.HTTPSConnection(self.host, self.port, timeout=self.timeout)
            interrupt = interruptible_http(connection, cancelled, deadline)
            def stop(flag):
                interrupt(flag)
                sock = getattr(connection, 'sock', None)
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
            def cancel_request():
                stop(cancelled)
            if cancellation is not None:
                cancellation.attach(cancel_request)
            else:
                self._cancel_request = cancel_request
            timer = threading.Timer(self.timeout, lambda: stop(expired))
            timer.daemon = True
            timer.start()
            connection.request('POST', self.path, body, {
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
                'User-Agent': 'UCHAMBUZI/1.1.0',
            })
            response = connection.getresponse()
            raw = response.read(_MAX_RESPONSE + 1)
            if expired.is_set() or time.monotonic() >= deadline:
                raise TimeoutError()
            if cancelled.is_set():
                raise RuntimeCancelled('Requête distante interrompue.')
            if len(raw) > _MAX_RESPONSE:
                raise RuntimeErrorLocal('Réponse distante trop volumineuse.')
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                data = None
            if response.status != 200 and is_policy_error(data):
                raise ProviderRefusalError('Requête refusée par le fournisseur.')
            if response.status in (401, 403):
                raise RuntimeErrorLocal('Authentification ou autorisation API refusée.')
            if response.status != 200:
                raise RuntimeErrorLocal(f'API distante indisponible ou erreur (HTTP {response.status}).')
            answer = self._answer(data, key)
            if cancellation is not None:
                cancellation.check()
            if on_chunk is not None:
                on_chunk(answer)
            return answer
        except (OSError, ValueError, TypeError, http.client.HTTPException):
            if cancelled.is_set():
                raise RuntimeCancelled('Requête distante interrompue.') from None
            if expired.is_set() or time.monotonic() >= deadline:
                raise RuntimeTimeout('Délai distant dépassé ; aucune relance automatique.') from None
            raise RuntimeErrorLocal('Erreur réseau ou réponse distante invalide.') from None
        finally:
            try:
                if timer is not None:
                    timer.cancel()
                if cancellation is not None:
                    cancellation.detach()
                else:
                    self._cancel_request = None
                if response is not None:
                    response.close()
                if connection is not None:
                    connection.close()
            finally:
                self._turn_lock.release()
