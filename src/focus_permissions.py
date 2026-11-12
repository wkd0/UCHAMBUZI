# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_permissions.py
# Role          : Approbation humaine liee a une operation unique
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Autorite detenue par l'hote humain, jamais injectee dans le moteur IA.

Limite de confiance : Python partage le processus de l'hote, ce n'est pas un
bac a sable contre du code Python malveillant dans ce meme processus.
"""
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import secrets
import threading
import time
from focus_contracts import ConfirmationRequest, approved_for

class Risk(str, Enum):
    LOCAL_READ = 'local_read'
    PASSIVE_INTELLIGENCE = 'passive_intelligence'
    NETWORK = 'network'
    ACTIVE = 'authorized_active'
    LOCAL_CHANGE = 'local_change'
    PRIVILEGED = 'privileged_or_disruptive'

@dataclass(frozen=True)
class Approval:
    id: str
    operation_id: str
    fingerprint: str
    actor: str
    expires: float


def fingerprint(operation):
    from dataclasses import asdict
    return hashlib.sha256(json.dumps(asdict(operation), sort_keys=True,
        ensure_ascii=False).encode()).hexdigest()

class HumanApprovalAuthority:
    def __init__(self, *, ttl=120):
        if not 0 < ttl <= 600:
            raise ValueError('Duree invalide')
        self.ttl = ttl
        self._pending = {}
        self._issued = {}
        self._lock = threading.Lock()

    def request(self, operation):
        request = ConfirmationRequest(secrets.token_hex(16), 'Execute prepared command',
                                      operation.review())
        with self._lock:
            self._pending[request.id] = (request, fingerprint(operation), time.monotonic()+self.ttl)
        return request

    def decide(self, operation, request, decision, *, actor):
        # Called only by the trusted human UI adapter, never by the AI adapter.
        with self._lock:
            stored = self._pending.pop(request.id, None)
            if (not stored or stored[0] != request or stored[1] != fingerprint(operation)
                or stored[2] <= time.monotonic() or not approved_for(request, decision)
                or not actor or len(actor) > 120):
                raise PermissionError('Approbation absente, refusee ou invalide')
            approval = Approval(secrets.token_hex(24), operation.id, stored[1], actor,
                                min(stored[2], time.monotonic()+self.ttl))
            self._issued[approval.id] = approval
            return approval

    def consume(self, operation, approval):
        with self._lock:
            issued = self._issued.pop(getattr(approval, 'id', None), None)
            if (issued is not approval or issued is None or
                issued.expires <= time.monotonic() or issued.operation_id != operation.id or
                issued.fingerprint != fingerprint(operation)):
                raise PermissionError('Autorisation invalide, expiree ou deja utilisee')

    def revoke(self, approval):
        with self._lock:
            self._issued.pop(approval.id, None)

    def invalidate(self, operation_ids):
        """Invalidate requests and grants on host context/session transitions."""
        ids = set(operation_ids)
        with self._lock:
            # Pending records are bound by fingerprint; clear requests on any
            # transition. This authority belongs to exactly one conversation.
            self._pending.clear()
            for key, approval in list(self._issued.items()):
                if approval.operation_id in ids:
                    del self._issued[key]
