# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_ai.py
# Role          : Orchestration des fournisseurs et des tours Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Moteur Focus asynchrone; aucune persistance ou autorisation d'outil implicite."""
import asyncio
import threading
import time

from focus_contracts import Message, Role, TextDelta, TurnFinished, TurnStarted, TurnState
from focus_modes import create_default_mode_engine
from focus_model_profiles import resolve_model_profile
from conversation import ProviderRefusalError
from focus_providers import GenerationSettings, HTTPProvider, ProviderError, interrupt_connection


class FocusAI:
    def __init__(self, providers=None, *, mode_engine=None):
        default_provider = providers is None
        providers = list(providers) if providers is not None else [HTTPProvider('ollama', 'http://127.0.0.1:11434', protocol='ollama')]
        self.providers = {p.id: p for p in providers}
        if len(self.providers) != len(providers):
            raise ValueError('Identifiants de fournisseurs dupliques')
        self.provider_id = 'ollama' if default_provider else None
        self.model_id = 'redsage-qwen3:8b-dpo' if default_provider else None
        self.settings = GenerationSettings()
        self.mode_engine = mode_engine or create_default_mode_engine()
        self.history = ()
        self.scenario = None
        self._active = None
        self._busy = False

    async def models(self, provider_id, *, allow_external=False):
        provider = self.providers.get(provider_id)
        if provider is None:
            raise ProviderError('provider_not_found')
        if not provider.enabled:
            raise ProviderError('provider_disabled')
        if not provider.local and not allow_external:
            raise ProviderError('external_consent_required')
        return await asyncio.to_thread(provider.list_models)

    async def discover(self):
        """Sonde uniquement les fournisseurs locaux actives; aucun trafic externe."""
        result = {}
        for provider in self.providers.values():
            if provider.local and provider.enabled:
                try:
                    result[provider.id] = await self.models(provider.id)
                except ProviderError:
                    result[provider.id] = None
        return result

    async def select(self, provider_id, model_id, *, allow_external=False):
        if self._busy:
            raise ProviderError('turn_active')
        models = await self.models(provider_id, allow_external=allow_external)
        if self._busy:
            raise ProviderError('turn_active')
        if model_id not in [m.id for m in models]:
            raise ProviderError('model_not_found')
        self.provider_id, self.model_id = provider_id, model_id

    def configure(self, settings):
        if self._busy:
            raise ProviderError('turn_active')
        if not isinstance(settings, GenerationSettings):
            raise ProviderError('invalid_settings')
        if self.provider_id:
            settings.validate(self.providers[self.provider_id].capabilities)
        self.settings = settings

    def cancel(self, turn_id):
        active = self._active
        if active and active['id'] == turn_id:
            active['stop'].set()
            interrupt_connection(active['connection'])
            active['loop'].call_soon_threadsafe(active['queue'].put_nowait, ('cancel', None))
            return True
        return False

    async def stream(self, turn_id: str, message: Message, *, allow_external=False):
        if self._busy:
            raise ProviderError('turn_active')
        self._busy = True
        iterator = self._stream(turn_id, message, allow_external=allow_external)
        try:
            async for event in iterator:
                yield event
        finally:
            await iterator.aclose()
            self._busy = False

    async def _stream(self, turn_id: str, message: Message, *, allow_external=False):
        if not isinstance(message, Message) or message.role != Role.USER or not message.text.strip() or not turn_id:
            raise ValueError('Tour utilisateur invalide')
        yield TurnStarted(turn_id, message.id)
        provider = self.providers.get(self.provider_id)
        if provider is None or not self.model_id:
            yield TurnFinished(turn_id, TurnState.FAILED, 'provider_not_selected', 'Aucun fournisseur et modele selectionnes.')
            return
        if not provider.enabled:
            yield TurnFinished(turn_id, TurnState.FAILED, 'provider_disabled', 'Fournisseur desactive.')
            return
        if not provider.local and not allow_external:
            yield TurnFinished(turn_id, TurnState.FAILED, 'external_consent_required', 'Transmission externe non autorisee.')
            return
        try:
            self.settings.validate(provider.capabilities)
            instructions = self.mode_engine.compose_active_instructions(active_scenario=self.scenario)
            family = provider.id if provider.id in ('ollama', 'openai', 'anthropic', 'grok', 'xai') else ''
            profile = resolve_model_profile(family, self.model_id)
            if profile.instructions:
                instructions += '\n' + profile.instructions
            if any(not isinstance(m, Message) or m.role not in (Role.USER, Role.ASSISTANT) for m in self.history):
                raise ProviderError('invalid_history')
            messages = [{'role': 'system', 'content': instructions}]
            messages.extend({'role': m.role.value, 'content': m.text} for m in self.history)
            messages.append({'role': 'user', 'content': message.text})
        except ProviderError as exc:
            yield TurnFinished(turn_id, TurnState.FAILED, exc.code, 'Parametres ou historique invalides.')
            return
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        stop = threading.Event()
        active = {'id': turn_id, 'stop': stop, 'connection': None, 'loop': loop, 'queue': queue}
        self._active = active
        def send(kind, value=None):
            if not stop.is_set():
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, (kind, value))
                except RuntimeError:
                    pass
        def bind(conn):
            active['connection'] = conn
            if stop.is_set():
                interrupt_connection(conn)
        def worker():
            try:
                provider.generate(self.model_id, messages, self.settings, lambda text: send('text', text), stop, bind)
                send('done')
            except ProviderRefusalError:
                send('error', 'provider_refusal')
            except ProviderError as exc:
                send('error', exc.code)
            except Exception:
                send('error', 'provider_error')
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        deadline = time.monotonic() + self.settings.timeout
        try:
            while True:
                try:
                    kind, value = await asyncio.wait_for(queue.get(), max(0, deadline - time.monotonic()))
                except asyncio.TimeoutError:
                    yield TurnFinished(turn_id, TurnState.FAILED, 'timeout', 'Delai de generation depasse.')
                    break
                if stop.is_set() or kind == 'cancel':
                    yield TurnFinished(turn_id, TurnState.CANCELLED)
                    break
                if kind == 'text':
                    yield TextDelta(turn_id, value)
                elif kind == 'done':
                    yield TurnFinished(turn_id, TurnState.COMPLETE)
                    break
                else:
                    yield TurnFinished(turn_id, TurnState.FAILED, value, 'Echec du fournisseur IA.')
                    break
        except asyncio.CancelledError:
            yield TurnFinished(turn_id, TurnState.CANCELLED)
        finally:
            stop.set()
            interrupt_connection(active['connection'])
            if self._active is active:
                self._active = None
