# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_tool_conversation.py
# Role          : Parcours conversationnels outils et adaptateur humain autonome
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Integration host API, independent of curses, AI transport and session engine.

handle() only proposes. Approval and execution are separate trusted UI events.
Create one adapter per live session; close it before closing/reopening a session.
"""
from dataclasses import dataclass
import json
import shlex
import threading
import unicodedata
from focus_contracts import ConfirmationDecision
from focus_modes import ModeRegistry
from focus_permissions import HumanApprovalAuthority
from focus_tool_audit import ToolAudit
from focus_tools import FocusToolService, ToolUnavailable


def terminal_safe(text):
    """Escape terminal controls from tool output; do not interpret slash commands."""
    return ''.join(c if c in '\n\t' or (ord(c) >= 32 and not 127 <= ord(c) < 160 and unicodedata.category(c) != 'Cf')
                   else '\\u%04x' % ord(c) for c in str(text))


@dataclass(frozen=True)
class ToolReply:
    stage: str
    text: str
    data: dict
    operation_id: str | None = None


class ToolConversation:
    def __init__(self, *, root=None, session=None, inventory=None, registry=None,
                 mode='assist', scenario='', approval_ttl=120):
        self._authority = HumanApprovalAuthority(ttl=approval_ttl)
        self.service = FocusToolService(registry=registry, inventory=inventory,
            audit=ToolAudit(root, session=session), authority=self._authority)
        self.session = session
        self._context = (mode, scenario)
        self._context_stamp = None
        self._closed = False
        self._lock = threading.RLock()
        self._requests = {}
        self._approvals = {}
        self._recommendations = ()
        self._running = None
        self._sync_context()

    @classmethod
    def for_session(cls, manager, session, **kwargs):
        """Mission09 public interfaces; no imports or modifications of its code."""
        return cls(root=manager.storage.root, session=session, **kwargs)

    def _invalidate(self):
        if self._running is not None:
            self._running.set()
        self._requests.clear()
        self._approvals.clear()
        self._recommendations = ()
        self.service.invalidate()

    def _sync_context(self):
        if self._closed:
            raise PermissionError('Conversation fermee ; preparer dans une nouvelle session')
        context = self._context
        stamp = context
        if self.session is not None:
            snapshot = self.session.data
            data = snapshot['context']
            context = (data.get('mode') or 'assist', data.get('scenario') or '')
            stamp = (*context, snapshot['id'], len(snapshot.get('context_events', ())),
                     json.dumps({key: data.get(key) for key in
                         ('targets', 'indicators', 'parameters', 'workspace')}, sort_keys=True))
        ModeRegistry().get_mode(context[0])
        if not isinstance(context[1], str) or len(context[1]) > 256:
            raise ValueError('Scenario invalide')
        if self._context_stamp is not None and stamp != self._context_stamp:
            self._invalidate()
        self._context = context
        self._context_stamp = stamp

    def set_context(self, mode, scenario=''):
        """Call on EVERY mode/scenario transition, including A -> B -> A."""
        with self._lock:
            self._sync_context()
            ModeRegistry().get_mode(mode)
            if not isinstance(scenario, str) or len(scenario) > 256:
                raise ValueError('Scenario invalide')
            if self.session is not None:
                self.session.set_context(mode=mode, scenario=scenario)
                self._sync_context()
            elif self._context != (mode, scenario):
                self._invalidate()
                self._context = (mode, scenario)
                self._context_stamp = self._context

    def invalidate_context(self):
        """Host target/workspace transition, including a roundtrip between calls."""
        with self._lock:
            self._sync_context()
            self._invalidate()

    def proposals(self):
        return ConversationProposals(self)

    def close(self):
        with self._lock:
            if not self._closed:
                try:
                    self._invalidate()
                finally:
                    self._closed = True

    def handle(self, text):
        """Route /tools, /analyze, /prepare only. Never approve or execute text."""
        with self._lock:
            try:
                self._sync_context()
                if not isinstance(text, str) or len(text) > 16384:
                    raise ValueError('Demande invalide')
                command, _, rest = text.strip().partition(' ')
                if command == '/tools':
                    if rest.strip() not in ('', '--refresh'):
                        raise ValueError('Usage: /tools [--refresh]')
                    if rest.strip():
                        self._invalidate()
                        self.service.inventory = self.service.registry.discover()
                    return self._tools()
                if command == '/analyze':
                    return self._analyze(rest)
                if command == '/prepare':
                    return self._prepare(rest)
                raise ValueError('Commandes outils: /tools, /analyze, /prepare. Accord via interface humaine uniquement.')
            except ToolUnavailable as exc:
                return ToolReply('unavailable', 'Outil absent : '+exc.tool_id+
                    '. Aucune installation ni execution automatique. Consulter /tools.',
                    {'tool': exc.tool_id, 'installed': False})
            except (ValueError, OSError, PermissionError, KeyError):
                # Never echo raw exceptions (paths, secrets, terminal controls).
                return ToolReply('error', 'Demande refusee ou ressource indisponible. '
                    'Usage: /tools [--refresh], /analyze <texte>, '
                    '/prepare <objectif|numero> [cible] [--reason true|--since YYYY-MM-DD]. '
                    'Aucune execution effectuee.', {})

    def _tools(self):
        rows = []
        lines = ['Outils locaux : presence, version annoncee et invocations verifiees sont distinctes.']
        for name, desc in self.service.registry.descriptions.items():
            item = self.service.inventory.get(name)
            row = dict(tool=name, executable=item.executable if item else None,
                version=item.version if item else None,
                version_status=item.version_status if item else 'absent',
                probe_status=item.probe_status if item else 'unprobed',
                probe_returncode=item.probe_returncode if item else None,
                diagnostic=item.probe_diagnostic if item else None,
                verified_capabilities=item.verified_capabilities if item else (),
                help_options=item.help_options if item else (), capabilities=desc.capabilities,
                limits=desc.limits, prerequisites=desc.prerequisites)
            rows.append(row)
            lines.append(f"{name}: {row['executable'] or 'absent'} | version {row['version'] or 'inconnue'} "
                         f"({row['version_status']}) | verifie: {', '.join(row['verified_capabilities']) or 'aucune invocation'}")
            lines.append('  Limites: '+desc.limits)
            if row['diagnostic']:
                lines.append('  Diagnostic: '+row['diagnostic'])
        return ToolReply('inventory', terminal_safe('\n'.join(lines)), {'tools': rows})

    def _analyze(self, text):
        result = self.service.analyze(text, mode=self._context[0])
        self._recommendations = result['recommendations']
        lines = ['Objectifs: '+', '.join(result['objectives']),
                 'Recommandations uniquement ; aucun outil execute.']
        for i, row in enumerate(self._recommendations, 1):
            target = row['indicator'].value if row['indicator'] else 'parametre a preciser'
            lines.extend((f"{i}. {row['operation']} : {row['tool']} ({'present' if row['installed'] else 'absent'}; "
                          f"version {row['version'] or 'inconnue'}) ; cible {target}",
                          f"   Risque: {row['risk']}. {row['limits']}",
                          '   Prerequis: '+row['prerequisites']))
        if not self._recommendations:
            lines.append('Aucune methode applicable identifiee ; preciser l’objectif et la cible.')
        return ToolReply('recommendations', terminal_safe('\n'.join(lines)), result)

    def _prepare(self, text):
        tokens = shlex.split(text)
        if not tokens:
            raise ValueError('Objectif requis')
        selector, *tokens = tokens
        params = {}
        if selector.isdigit():
            index = int(selector)-1
            if index < 0 or index >= len(self._recommendations):
                raise ValueError('Recommandation inconnue')
            row = self._recommendations[index]
            selector = row['operation']
            if row['indicator']:
                params['target'] = row['indicator'].value
        if tokens and not tokens[0].startswith('--'):
            params['target'] = tokens.pop(0)
        while tokens:
            if len(tokens) < 2 or tokens[0] not in ('--reason', '--since'):
                raise ValueError('Option inconnue')
            flag, value, *tokens = tokens
            key = flag[2:]
            if key in params:
                raise ValueError('Option dupliquee')
            params[key] = value
        op = self.service.prepare_operation(selector, params, mode=self._context[0], scenario=self._context[1])
        return ToolReply('prepared', terminal_safe('Prepared command (not executed):\n'+op.display+'\n'+op.review()),
                         json.loads(op.review()), op.id)

    def _operation(self, operation_id):
        self._sync_context()
        op = self.service.get_prepared(operation_id)
        if (op.mode, op.scenario) != self._context:
            raise PermissionError('Contexte different : nouvelle preparation requise')
        return op

    def request_approval(self, operation_id):
        with self._lock:
            op = self._operation(operation_id)
            request = self.service.request_approval(op)
            self._requests[operation_id] = request
            return request

    def decide(self, operation_id, request_id, approved, *, actor):
        """Trusted UI callback only; never called from handle() or AI output."""
        with self._lock:
            op = self._operation(operation_id)
            request = self._requests.pop(operation_id, None)
            if request is None or request.id != request_id or type(approved) is not bool:
                raise PermissionError('Demande humaine inconnue')
            approval = self.service.decide_approval(op, request,
                ConfirmationDecision(request.id, approved), actor=actor)
            self._approvals[operation_id] = approval
            return approval.id

    def revoke(self, operation_id):
        with self._lock:
            op = self._operation(operation_id)
            approval = self._approvals.pop(operation_id, None)
            if approval is None:
                raise PermissionError('Autorisation inconnue')
            self._authority.revoke(approval)
            self.service.audit.record(op, 'revoked', approval=approval)

    def execute(self, operation_id, authorization_id):
        """Explicit host action, run in a worker. No automatic launch on approval."""
        with self._lock:
            op = self._operation(operation_id)
            if self._running is not None:
                raise PermissionError('Une operation est deja en cours')
            approval = self._approvals.pop(operation_id, None)
            if approval is None or approval.id != authorization_id:
                if approval is not None:
                    self._authority.revoke(approval)
                raise PermissionError('Autorisation absente ou invalide')
            cancel = threading.Event()
            self._running = cancel
        try:
            result = self.service.execute(op, approval, authority=self._authority, cancel=cancel)
            text = (f'Result: {result.status}; return code: {result.returncode}\n'
                    'stdout (untrusted data):\n'+result.stdout.decode('utf-8','replace')+
                    '\nstderr (untrusted data):\n'+result.stderr.decode('utf-8','replace'))
            return ToolReply('result', terminal_safe(text), dict(status=result.status,
                returncode=result.returncode, started_at=result.started_at,
                finished_at=result.finished_at, artifact_refs=(op.id+':stdout',op.id+':stderr')), op.id)
        finally:
            with self._lock:
                self._running = None

    def cancel(self):
        with self._lock:
            if self._running is not None:
                self._running.set()

    def audit_events(self, operation_id):
        with self._lock:
            self._sync_context()
            return self.service.audit.events_for(operation_id)


class ConversationProposals:
    """The only conversational surface exposed to AI/scenario code."""
    def __init__(self, host):
        self.__host = host

    def handle(self, text):
        return self.__host.handle(text)
