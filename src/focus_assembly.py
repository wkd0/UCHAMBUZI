# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_assembly.py
# Role          : Raccordement des scenarios et outils a la TUI finale
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
import asyncio
import getpass
import os
from pathlib import Path
import shlex
import threading
from dataclasses import replace
from focus_contracts import ConfirmationDecision
from focus_orchestrator import FocusScenariosCatalog
from focus_permissions import HumanApprovalAuthority
from focus_tool_audit import ToolAudit
from focus_tools import FocusToolService


class FinalCatalog(FocusScenariosCatalog):
    def scenarios(self, profile_id=None):
        values = super().scenarios(profile_id)
        # Les instructions sont des definitions livrees, jamais des entrees d'enquete.
        return tuple(replace(v, description='\n'.join((self.registry.get_scenario(v.id).ai_instructions,
            *self.registry.get_scenario(v.id).methodology,
            *self.registry.get_scenario(v.id).limits_and_precautions))) for v in values)

    def get_scenario(self, profile_id, scenario_id=None):
        original = profile_id if scenario_id is None else scenario_id
        sid = {"timeline": "timeline_analysis"}.get(original, original)
        value = next((s for s in self.scenarios(None if scenario_id is None else profile_id) if s.id == sid), None)
        return replace(value, id=original) if value else None


class ToolUI:
    """Hote humain : propositions, accord et lancement restent trois actions."""
    def __init__(self, controller):
        self.c = controller
        self.host = None
        self._session = None
        self.authorizations = {}
        self.running = False

    @property
    def service(self):
        return self.host.service if self.host else None

    def invalidate(self):
        self.authorizations.clear()
        if self.host:
            self.host.invalidate_context()

    def close(self):
        self.authorizations.clear()
        if self.host:
            self.host.close()
        self.host = None

    def cancel(self):
        if not self.running:
            return False
        self.host.cancel()
        self.c.status_notice = 'Interruption de l’outil demandée.'
        return True

    async def ensure(self):
        from focus_tool_conversation import ToolConversation
        session = self.c.settings_ui.session
        if self.host is not None and session is not self._session:
            self.close()
        if self.host is None:
            kwargs = dict(mode=self.c.profile.id, scenario=self.c.scenario.id if self.c.scenario else '')
            if session is not None:
                self.host = await asyncio.to_thread(ToolConversation.for_session, self.c.settings_ui.sessions, session, **kwargs)
            else:
                self.host = await asyncio.to_thread(ToolConversation, **kwargs)
            self._session = session
        self.host.set_context(self.c.profile.id, self.c.scenario.id if self.c.scenario else '')
        from focus_orchestrator import ToolServiceBridge
        manager = self.c.settings_ui.scenarios
        self.scenario_tools = ToolServiceBridge(self.host.service).inspect_tools_for_scenario(manager.active_mode, manager.active_scenario) if manager else None

    async def command(self, text):
        parts = shlex.split(text)
        if not parts or parts[0] not in ('/tools', '/analyze', '/prepare', '/operation', '/approve', '/execute', '/copy'):
            return False
        c = self.c
        if parts[0] == '/copy':
            if len(parts) != 2:
                raise ValueError('/copy CHEMIN : exporter la derniere reponse originale')
            message = next((e.message for e in reversed(c.entries[0]) if e.message and e.message.role.value == 'assistant'), None)
            if message is None:
                raise ValueError('Aucune reponse a copier')
            target = Path(parts[1]).expanduser()
            if not target.is_absolute():
                target = Path(c.settings_ui.values['workspace'] or Path.cwd()) / target
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
                stream.write(message.text)
            c.status_notice = 'Texte original exporte : ' + str(target)
            return True
        if self.running:
            raise ValueError('Une operation est active ; Ctrl+C pour interrompre')
        await self.ensure()
        if parts[0] in ('/tools', '/analyze', '/prepare', '/operation'):
            command = '/prepare' + text[len('/operation'):] if parts[0] == '/operation' else text
            if parts[0] == '/analyze':
                self.invalidate()
            reply = await asyncio.to_thread(self.host.handle, command)
            c.active_section = 1
            c.add_panel(1, 'Outils — ' + reply.stage, reply.text +
                ('\nIdentifiant : ' + reply.operation_id + '\n/approve ID puis /execute ID' if reply.operation_id else ''))
            c.status_notice = 'Analyse locale disponible dans Enquête.' if parts[0] == '/analyze' else 'Parcours outils disponible dans Enquête.'
            return True
        if len(parts) != 2:
            raise ValueError('/approve ID ou /execute ID')
        oid = parts[1]
        if parts[0] == '/approve':
            host = self.host
            request = host.request_approval(oid)
            def decision(value):
                try:
                    auth = host.decide(oid, request.id, value.approved, actor=getpass.getuser())
                except (PermissionError, ValueError, KeyError):
                    c.status_notice = 'Accord refuse ou invalide ; preparer de nouveau.'
                    return
                if host is self.host:
                    self.authorizations[oid] = auth
                    c.status_notice = 'Accord reçu ; /execute ' + oid + ' pour lancer explicitement.'
            c.request_confirmation(request.action, request.details, decision)
        else:
            auth = self.authorizations.pop(oid, None)
            if auth is None:
                raise PermissionError('Accord absent ; utilisez /approve ID puis /execute ID')
            host = self.host
            self.running = True
            async def execute():
                try:
                    reply = await asyncio.to_thread(host.execute, oid, auth)
                    c.active_section = 1
                    c.add_panel(1, 'Resultat outil', reply.text)
                finally:
                    host.cancel()
                    self.running = False
            c.settings_ui.spawn(execute())
        return True
