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
import json
import re
import shutil
import threading
import time

from focus_contracts import Message, Role, TextDelta, TurnFinished, TurnStarted, TurnState
from ai_calibration import response_guide_for, resolve_model_profile
from focus_modes import create_default_mode_engine
from conversation import (ProviderRefusalError, SYSTEM, asks_local_system,
                          local_system_inventory, sanitize_prompt_data)
from focus_providers import GenerationSettings, HTTPProvider, ProviderError, interrupt_connection


_LOCAL_TOOL_STATUS_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r'\b(?:is|are)\s+([a-z][a-z0-9_.+-]{0,63})\s+(?:installed|present|available|current|version)\b',
    r'\b([a-z][a-z0-9_.+-]{0,63})\s+(?:(?:is|are)\s+)?installed\b',
    r'\b([a-z][a-z0-9_.+-]{0,63})\s+est-(?:il|elle)\s+(?:installé|installée|présent|présente|disponible|à\s+jour|version)\b',
    r'\b([a-z][a-z0-9_.+-]{0,63})\s+est\s+(?:installé|installée|à\s+jour)\b',
    r'\b([a-z][a-z0-9_.+-]{0,63})\s+(?:(?:is|are)\s+)?(?:up[ -]to[ -]date|à\s+jour)\b',
))


def _local_facts_for(text, provider):
    """Collecte des faits locaux limités à la question, uniquement pour un modèle local."""
    if not provider.local:
        return None
    facts = {}
    if asks_local_system(text):
        facts['inventaire_systeme_local'] = local_system_inventory()
    tools = []
    seen = set()
    for pattern in _LOCAL_TOOL_STATUS_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1).casefold()
            if name in seen or name in {'and', 'et', 'la', 'le', 'les', 'the', 'a', 'an'}:
                continue
            # « mise à jour » is a common French noun phrase, not a command
            # named `mise` whose installation status the user asked about.
            if name == 'mise' and 'à jour' in match.group(0).casefold():
                continue
            if name == 'jour' and 'mise à jour' in text[max(0, match.start() - 8):match.end()].casefold():
                continue
            seen.add(name)
            path = shutil.which(name)
            tools.append({'commande': name, 'presence': 'présente' if path else 'absente',
                          'chemin': path})
    if tools:
        facts['outils_locaux'] = tools
    return facts or None


def _local_tool_status_answer(facts):
    """Répond sans modèle aux demandes dont la présence locale est vérifiée."""
    tools = facts.get('outils_locaux') if isinstance(facts, dict) else None
    if not isinstance(tools, list) or len(tools) != 1:
        return None
    tool = tools[0]
    if not isinstance(tool, dict) or not isinstance(tool.get('commande'), str):
        return None
    name = tool['commande']
    if tool.get('presence') == 'présente' and isinstance(tool.get('chemin'), str):
        return (f"Vérification locale : `{name}` est présent dans le PATH "
                f"({tool['chemin']}). Sa version installée et son état de mise à jour "
                "n'ont pas été vérifiés. Aucune requête réseau ni modification du système n'a été effectuée.")
    if tool.get('presence') == 'absente':
        return (f"Vérification locale : `{name}` n'a pas été trouvé dans le PATH. "
                "Cela ne suffit pas à confirmer l'état de son paquet ni à conclure qu'il n'est pas installé. "
                "Aucune requête réseau ni modification du système n'a été effectuée.")
    return None


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

    def system_instructions(self, question):
        """Compose le prompt réellement envoyé, commun à l'aperçu et au transport."""
        instructions = SYSTEM + '\n' + self.mode_engine.compose_active_instructions(
            active_scenario=self.scenario)
        family = self.provider_id if self.provider_id in (
            'ollama', 'openai', 'anthropic', 'grok', 'xai') else ''
        profile = resolve_model_profile(family, self.model_id)
        if profile.instructions:
            instructions += '\n' + profile.instructions
        answer_guide = response_guide_for(question)
        if answer_guide:
            instructions += '\n' + answer_guide
        return instructions

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
            # Même consigne pour l'aperçu de consentement et la requête envoyée.
            instructions = self.system_instructions(message.text)
            if any(not isinstance(m, Message) or m.role not in (Role.USER, Role.ASSISTANT) for m in self.history):
                raise ProviderError('invalid_history')
            messages = [{'role': 'system', 'content': instructions}]
            messages.extend({'role': m.role.value, 'content': m.text} for m in self.history)
            local_facts = _local_facts_for(message.text, provider)
            local_answer = _local_tool_status_answer(local_facts)
            if local_answer:
                yield TextDelta(turn_id, local_answer)
                yield TurnFinished(turn_id, TurnState.COMPLETE)
                return
            if local_facts:
                content = json.dumps({
                    'demande': sanitize_prompt_data(message.text),
                    'contexte_technique_local_non_fiable': sanitize_prompt_data(local_facts),
                }, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
            else:
                content = message.text
            messages.append({'role': 'user', 'content': content})
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
