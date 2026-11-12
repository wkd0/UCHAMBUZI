# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_providers.py
# Role          : Fournisseurs HTTP et decodage incremental des reponses IA
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Transports Ollama local et API Chat Completions compatible OpenAI.

Aucun proxy, redirection ou secret dans les exceptions. Les flux sont lus en
lignes d'octets completes, puis decodes en UTF-8 strict.
"""
from dataclasses import dataclass, field
import http.client
import json
import math
import os
import socket
import threading
import time
from urllib.parse import urlsplit

from conversation import (OllamaRuntime, OllamaStream, interruptible_http, RuntimeErrorLocal, RuntimeCancelled, RuntimeTimeout,
                          ProviderRefusalError, is_policy_error, is_provider_refusal)


class ConfiguredOllamaRuntime(OllamaRuntime):
    """Adaptateur REPL pour un serveur Ollama choisi explicitement, sans proxy."""

    _CONFIG_FIELDS = frozenset(('model', 'port', 'timeout', 'host'))

    def __setattr__(self, name, value):
        if getattr(self, '_config_sealed', False) and name in self._CONFIG_FIELDS:
            raise AttributeError('Configuration du fournisseur immuable ; créez un nouvel adaptateur.')
        object.__setattr__(self, name, value)

    def __init__(self, model=None, port=11434, timeout=60.0, *, host='127.0.0.1'):
        super().__init__(model, port, timeout)
        from focus_settings import validate_ia
        validate_ia(dict(model=model, host=host, port=port, timeout=timeout))
        self.host = host
        self._config_sealed = True

    def _request(self, method, path, payload=None, on_chunk=None, *, cancellation=None, on_thinking=None):
        if self.host == '127.0.0.1':
            return super()._request(method, path, payload, on_chunk, cancellation=cancellation, on_thinking=on_thinking)
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        expired, cancelled = threading.Event(), threading.Event()
        timer = response = None
        interrupt = interruptible_http(connection, cancelled, time.monotonic() + self.timeout)

        def cancel_request():
            interrupt(cancelled)

        if cancellation is None:
            self._cancel_request = cancel_request
        try:
            if cancellation is not None:
                cancellation.check()
                cancellation.attach(cancel_request)
            timer = threading.Timer(self.timeout, lambda: interrupt(expired))
            timer.daemon = True
            timer.start()
            body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
            connection.connect()
            if cancellation is not None:
                cancellation.check()
            connection.request(method, path, body, {'Content-Type': 'application/json'})
            response = connection.getresponse()
            if cancellation is not None:
                cancellation.check()
            if response.status != 200:
                raise RuntimeErrorLocal(f'Erreur du moteur Ollama (HTTP {response.status}).')
            if on_chunk is None:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise RuntimeErrorLocal('Réponse du moteur trop volumineuse.')
                result = json.loads(raw)
            else:
                stream, total = OllamaStream(on_chunk, on_thinking), 0
                while True:
                    raw = response.readline(2_000_001)
                    if cancellation is not None:
                        cancellation.check()
                    total += len(raw)
                    if not raw or total > 2_000_000:
                        raise RuntimeErrorLocal('Flux interrompu ou trop volumineux.')
                    result = json.loads(raw)
                    message = result.get('message', {})
                    text = message.get('content', '')
                    if (not isinstance(text, str) or message.get('role', 'assistant') != 'assistant'
                            or message.get('tool_calls') or message.get('function_call')):
                        raise RuntimeErrorLocal('Fragment du moteur invalide.')
                    stream.feed(message)
                    if result.get('done') is True:
                        result['message'] = {'role': 'assistant', 'content': stream.finish()}
                        break
            if expired.is_set():
                raise TimeoutError()
            if cancelled.is_set():
                raise RuntimeCancelled('Requête interrompue.')
            return result
        except (OSError, ValueError, TypeError, AttributeError, http.client.HTTPException) as exc:
            if cancelled.is_set():
                raise RuntimeCancelled('Requête interrompue.') from exc
            if expired.is_set() or isinstance(exc, TimeoutError):
                raise RuntimeTimeout(f'Délai total de {self.timeout:g} s dépassé.') from exc
            raise RuntimeErrorLocal('Moteur indisponible ou réponse invalide.') from exc
        finally:
            if cancellation is not None:
                cancellation.detach()
            elif self._cancel_request is cancel_request:
                self._cancel_request = None
            if timer is not None:
                timer.cancel()
            if response is not None:
                response.close()
            connection.close()


class ProviderError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Capabilities:
    temperature: bool = True
    max_tokens: bool = True
    context_size: bool = False
    streaming: bool = True
    tools: bool = False


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float | None = None
    max_tokens: int | None = None
    context_size: int | None = None
    timeout: float = 300.0
    streaming: bool = True
    options: dict = field(default_factory=dict)

    def validate(self, capabilities):
        if type(self.timeout) not in (int, float) or not math.isfinite(self.timeout) or not 0 < self.timeout <= 600:
            raise ProviderError('invalid_settings')
        if self.streaming is not True or not capabilities.streaming or self.options:
            raise ProviderError('unsupported_parameter')
        if self.temperature is not None:
            if not capabilities.temperature:
                raise ProviderError('unsupported_parameter')
            if type(self.temperature) not in (int, float) or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
                raise ProviderError('invalid_settings')
        for value, supported in ((self.max_tokens, capabilities.max_tokens), (self.context_size, capabilities.context_size)):
            if value is not None:
                if not supported:
                    raise ProviderError('unsupported_parameter')
                if type(value) is not int or not 1 <= value <= 10000000:
                    raise ProviderError('invalid_settings')


@dataclass(frozen=True)
class AvailableModel:
    id: str
    provider: str
    local: bool
    details: dict = field(default_factory=dict)


class HTTPProvider:
    """Fournisseur configure explicitement; secret lu depuis une variable d'environnement."""
    def __init__(self, provider_id, endpoint, *, protocol, secret_env=None, enabled=True):
        if protocol not in ('ollama', 'openai') or not provider_id:
            raise ValueError('Configuration fournisseur invalide')
        url = urlsplit(endpoint)
        if url.username or url.password or url.query or url.fragment or not url.hostname:
            raise ValueError('Endpoint invalide')
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError('Port fournisseur invalide')
        if protocol == 'ollama':
            if url.scheme != 'http' or url.hostname != '127.0.0.1':
                raise ValueError('Ollama doit utiliser 127.0.0.1 en HTTP')
        elif url.scheme != 'https':
            raise ValueError('HTTPS requis pour un fournisseur externe')
        self.id, self.protocol, self.enabled = provider_id, protocol, enabled
        self.endpoint, self.secret_env = url, secret_env
        self.local = protocol == 'ollama'
        self.capabilities = Capabilities(context_size=self.local)

    def _connection(self, timeout):
        cls = http.client.HTTPConnection if self.local else http.client.HTTPSConnection
        return cls(self.endpoint.hostname, self.endpoint.port, timeout=timeout)

    def _path(self, suffix):
        return self.endpoint.path.rstrip('/') + suffix

    def _headers(self):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.secret_env:
            key = os.environ.get(self.secret_env)
            if not key or '\n' in key or '\r' in key:
                raise ProviderError('authentication')
            headers['Authorization'] = 'Bearer ' + key
        return headers

    def _request(self, conn, method, path, body=None):
        conn.request(method, self._path(path), body=body, headers=self._headers())
        response = conn.getresponse()
        if response.status != 200:
            if not self.local:
                try:
                    raw = response.read(2_000_001)
                    if len(raw) <= 2_000_000 and is_policy_error(json.loads(raw)):
                        raise ProviderRefusalError('Requête refusée par la politique du fournisseur.')
                except (ValueError, UnicodeDecodeError):
                    pass
            code = 'authentication' if response.status in (401, 403) else 'quota' if response.status == 429 else 'model_not_found' if response.status == 404 else 'provider_unavailable'
            raise ProviderError(code)
        return response

    def list_models(self, timeout=5):
        if not self.enabled:
            raise ProviderError('provider_disabled')
        conn = self._connection(timeout)
        try:
            response = self._request(conn, 'GET', '/api/tags' if self.local else '/models')
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ProviderError('invalid_response')
            payload = json.loads(raw.decode('utf-8'))
            if not isinstance(payload, dict):
                raise ProviderError('invalid_response')
            items = payload['models' if self.local else 'data']
            if not isinstance(items, list):
                raise ValueError()
            result = []
            for item in items:
                if not isinstance(item, dict):
                    raise ProviderError('invalid_response')
                name = item['name' if self.local else 'id']
                if not isinstance(name, str) or not name:
                    raise ValueError()
                result.append(AvailableModel(name, self.id, self.local, item.get('details', {}) if self.local else {}))
            return result
        except ProviderError:
            raise
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            raise ProviderError('provider_unavailable') from None
        finally:
            conn.close()

    def generate(self, model, messages, settings, emit, stop, bind):
        """Bloquant : execute dans un thread par le moteur; bind permet la fermeture."""
        settings.validate(self.capabilities)
        conn = self._connection(settings.timeout)
        bind(conn)
        try:
            if stop.is_set():
                return
            body = {'model': model, 'messages': messages, 'stream': True}
            params = {}
            if settings.temperature is not None:
                params['temperature'] = settings.temperature
            if settings.max_tokens is not None:
                params['num_predict' if self.local else 'max_tokens'] = settings.max_tokens
            if settings.context_size is not None:
                params['num_ctx'] = settings.context_size
            if self.local:
                body['options'] = params
            else:
                body.update(params)
            response = self._request(conn, 'POST', '/api/chat' if self.local else '/chat/completions', json.dumps(body, ensure_ascii=False).encode('utf-8'))
            complete = False
            finish_seen = False
            while not stop.is_set():
                line = response.readline(1_000_001)
                if len(line) > 1_000_000:
                    raise ProviderError('invalid_response')
                if not line:
                    break
                if self.local:
                    item = json.loads(line.decode('utf-8'))
                    if not isinstance(item, dict):
                        raise ProviderError('invalid_response')
                    if item.get('error'):
                        raise ProviderError('provider_error')
                    message = item.get('message', {})
                    if not isinstance(message, dict):
                        raise ProviderError('invalid_response')
                    if message.get('role', 'assistant') != 'assistant' or message.get('tool_calls') or message.get('function_call'):
                        raise ProviderError('unsupported_response')
                    text = message.get('content', '')
                    if not isinstance(text, str):
                        raise ProviderError('invalid_response')
                    if text:
                        emit(text)
                    if item.get('done') is True:
                        if item.get('done_reason') != 'stop':
                            raise ProviderError('incomplete_response')
                        complete = True
                        break
                else:
                    if not line.startswith(b'data:'):
                        continue
                    data = line[5:].strip()
                    if data == b'[DONE]':
                        complete = finish_seen
                        break
                    item = json.loads(data.decode('utf-8'))
                    if not isinstance(item, dict):
                        raise ProviderError('invalid_response')
                    choices = item.get('choices', [])
                    if not isinstance(choices, list):
                        raise ProviderError('invalid_response')
                    for choice in choices:
                        if not isinstance(choice, dict):
                            raise ProviderError('invalid_response')
                        delta = choice.get('delta', {})
                        if not isinstance(delta, dict):
                            raise ProviderError('invalid_response')
                        if delta.get('refusal') or choice.get('finish_reason') == 'content_filter':
                            raise ProviderRefusalError('Requête refusée par la politique du fournisseur.')
                        if delta.get('tool_calls') or delta.get('function_call'):
                            raise ProviderError('unsupported_response')
                        text = delta.get('content')
                        if text is not None:
                            if not isinstance(text, str):
                                raise ProviderError('invalid_response')
                            if text:
                                if is_provider_refusal(text):
                                    raise ProviderRefusalError('Requête refusée par la politique du fournisseur.')
                                emit(text)
                        reason = choice.get('finish_reason')
                        if reason is not None:
                            if reason != 'stop':
                                raise ProviderError('incomplete_response')
                            finish_seen = True
            if not stop.is_set() and not complete:
                raise ProviderError('incomplete_response')
        except ProviderError:
            raise
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            raise ProviderError('provider_unavailable') from None
        finally:
            conn.close()


def interrupt_connection(conn):
    if conn is not None:
        try:
            if conn.sock:
                conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()
