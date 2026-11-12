# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_legacy_adapter.py
# Role          : Adaptateur de démonstration vers la session existante
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Pont transitoire : un seul delta après réponse complète, pas de streaming réel."""
import asyncio
from focus_contracts import Message, Role, TextDelta, TurnFinished, TurnStarted, TurnState
from conversation import RuntimeErrorLocal


class LegacyConversation:
    def __init__(self, session):
        self.session = session
        self._lock = asyncio.Lock()

    async def stream(self, turn_id: str, message: Message):
        if message.role != Role.USER or not message.text.strip():
            raise ValueError('Un message utilisateur non vide est requis.')
        async with self._lock:
            yield TurnStarted(turn_id, message.id)
            try:
                # Le moteur historique bloque : l'exécuter hors de la boucle UI.
                # shield + attente à l'annulation évitent une mutation tardive concurrente.
                task = asyncio.create_task(asyncio.to_thread(self.session.respond, message.text))
                try:
                    answer = await asyncio.shield(task)
                except asyncio.CancelledError:
                    try:
                        await task
                    except Exception:
                        pass
                    raise
            except RuntimeErrorLocal:
                yield TurnFinished(turn_id, TurnState.FAILED, 'engine_unavailable', 'Moteur indisponible ou réponse incomplète.')
            except Exception:
                yield TurnFinished(turn_id, TurnState.FAILED, 'internal_error', 'Erreur interne du moteur.')
            else:
                yield TextDelta(turn_id, answer)
                yield TurnFinished(turn_id, TurnState.COMPLETE)
