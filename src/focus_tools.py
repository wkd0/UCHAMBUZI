# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# Fichier       : focus_tools.py
# Role          : Preparation recommandations et execution controlee Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""API autonome pour /tools, /analyze, /prepare ; aucune execution dans prepare.

Les modeles ne recoivent que ProposalTools, jamais HumanApprovalAuthority.
"""
from dataclasses import dataclass, replace
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import stat
import uuid
from urllib.parse import urlsplit
from focus_contracts import ToolResult
from focus_modes import ModeRegistry
from focus_permissions import Risk, HumanApprovalAuthority, Approval
from focus_tool_process import run
from focus_tool_registry import ToolRegistry, identity

class ToolUnavailable(ValueError):
    def __init__(self, tool_id):
        self.tool_id = tool_id
        super().__init__('Outil absent : ' + tool_id)


@dataclass(frozen=True)
class Indicator:
    kind: str
    value: str
    exists: bool | None = None


def identify(value, *, kind=None):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('Indice vide, trop long ou contenant des controles')
    if kind == 'file' or value.startswith(('/', './', '../', '~/')):
        path = Path(value).expanduser().absolute()
        return Indicator('file', str(path), path.is_file())
    try:
        addr = ipaddress.ip_address(value)
        return Indicator('ipv'+str(addr.version), str(addr))
    except ValueError:
        pass
    if '://' in value:
        try:
            parsed = urlsplit(value)
            if (parsed.scheme not in ('http','https') or not parsed.hostname or
                parsed.username or parsed.password or parsed.query or parsed.fragment):
                raise ValueError('URL avec secrets/parametres ou protocole non pris en charge')
            identify(parsed.hostname)
            parsed.port
            return Indicator('url', value)
        except (ValueError, UnicodeError) as exc:
            raise ValueError('URL invalide ou sensible') from exc
    try:
        domain = value.rstrip('.').encode('idna').decode('ascii').lower()
    except UnicodeError as exc:
        raise ValueError('Domaine invalide') from exc
    labels = domain.split('.')
    if (len(domain)<=253 and len(labels)>=2 and not all(x.isdigit() for x in labels) and
        all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', x) for x in labels)):
        return Indicator('domain',domain)
    raise ValueError('Type inconnu : preciser le chemin ou fournir un indice valide')


def analyze_text(text):
    """Extraction deterministe, aucune inference sur OS, ports ou contenu."""
    if not isinstance(text, str) or len(text)>16384:
        raise ValueError('Demande trop longue')
    found=[]
    try:
        tokens=shlex.split(text)
    except ValueError:
        tokens=text.split()
    for token in tokens:
        try:
            indicator=identify(token.strip(' ,;()'))
        except ValueError:
            continue
        if indicator not in found:
            found.append(indicator)
    lowered=text.casefold()
    objectives=tuple(name for words,name in (
        (('dns','domaine','resolution','résolution'),'dns'),
        (('port','scan','service'),'ports'), (('empreinte','hash','sha256'),'hash'),
        (('metadonn','métadonn','exif'),'metadata'), (('journal','log'),'logs'),
        (('capture','pcap'),'pcap'), (('chaine','chaîne','strings'),'strings'))
        if any(word in lowered for word in words))
    return tuple(found), objectives or ('identify',)

# Declarative metadata is not an executable template. Templates below are trusted code.
_OPERATIONS = {
 'interfaces': ('ip', Risk.LOCAL_READ, 'system_diagnostics'),
 'sockets': ('ss', Risk.LOCAL_READ, 'network_monitoring'),
 'dns': ('dig', Risk.NETWORK, 'passive_dns'),
 'registration': ('whois', Risk.PASSIVE_INTELLIGENCE, 'whois_lookup'),
 'ports': ('nmap', Risk.ACTIVE, 'port_scanning'),
 'metadata': ('exiftool', Risk.LOCAL_READ, 'metadata_extraction'),
 'pcap': ('tshark', Risk.LOCAL_READ, 'network_monitoring'),
 'identify': ('file', Risk.LOCAL_READ, 'malware_triage'),
 'hash': ('sha256sum', Risk.LOCAL_READ, 'disk_forensics'),
 'strings': ('strings', Risk.LOCAL_READ, 'malware_triage'),
 'signatures': ('binwalk', Risk.LOCAL_READ, 'file_carving'),
 'logs': ('journalctl', Risk.LOCAL_READ, 'log_analysis'),
 'ruleset': ('nft', Risk.PRIVILEGED, 'firewall_configuration'),
 'manual': ('man', Risk.LOCAL_READ, 'documentation_tools'),
 'services': ('systemctl', Risk.LOCAL_READ, 'service_management'),
}
_FILE_OPS={'metadata','pcap','identify','hash','strings','signatures'}
_NETWORK_OPS={'dns','registration','ports'}

@dataclass(frozen=True)
class PreparedOperation:
    id: str
    tool_id: str
    operation: str
    program: str
    args: tuple[str,...]
    target: str
    scope: str
    risk: Risk
    mode: str
    scenario: str
    version: str | None
    compatibility: str
    executable_identity: tuple
    resource_identity: tuple
    timeout: float
    output_limit: int
    effects: str
    privileges: str
    sent_data: str
    verification: str
    rollback: str

    @property
    def display(self):
        return shlex.join((self.program,*self.args))

    def review(self):
        return json.dumps(dict(operation_id=self.id, program=self.program, arguments=self.args,
            target=self.target, scope=self.scope, risk=self.risk.value, mode=self.mode,
            scenario=self.scenario, version=self.version, compatibility=self.compatibility,
            effects=self.effects, privileges=self.privileges, sent_data=self.sent_data,
            timeout_seconds=self.timeout, output_limit_bytes=self.output_limit,
            resources='CPU/memoire dependantes du fichier et de l’outil ; pas de limite memoire dure',
            verification=self.verification, rollback=self.rollback),ensure_ascii=False,indent=2)

class FocusToolService:
    def __init__(self, *, registry=None, inventory=None, audit=None, authority=None):
        self.registry=registry or ToolRegistry()
        self.inventory=inventory if inventory is not None else self.registry.discover()
        self.audit=audit
        self._authority=authority
        self._prepared={}

    def invalidate(self):
        """Host context/session change: all old preparations become unusable."""
        operations = tuple(self._prepared.values())
        if self._authority is not None:
            self._authority.invalidate(op.id for op in operations)
        self._prepared.clear()
        if self.audit:
            for operation in operations:
                self.audit.record(operation, 'invalidated')

    def tools_for_mode(self, mode='assist'):
        selected=ModeRegistry().get_mode(mode)
        return dict(mode=selected.id, categories=selected.recommended_tool_categories,
            tools=tuple(d for d in self.registry.descriptions.values()
                if set(d.categories)&set(selected.recommended_tool_categories)
                or d.id in selected.recommended_tools),
            limit='Le catalogue initial ne couvre pas toutes les categories du mode.')

    def analyze(self,text, *, mode='assist'):
        indicators, objectives=analyze_text(text)
        modes=self.tools_for_mode(mode)
        recommendations=[]
        for indicator in indicators or (None,):
            choices=list(objectives)
            if objectives==('identify',) and indicator:
                choices=['identify','hash','metadata'] if indicator.kind=='file' else ['dns','registration']
            if indicator and indicator.kind == 'file' and 'logs' in choices:
                choices = [op for op in choices if op != 'logs'] + ['identify', 'hash', 'strings']
            for operation in dict.fromkeys(choices):
                if operation not in _OPERATIONS:
                    continue
                if indicator and operation in _FILE_OPS and indicator.kind!='file':
                    continue
                if indicator and operation in _NETWORK_OPS and indicator.kind=='file':
                    continue
                if indicator and operation in ('logs', 'interfaces', 'sockets', 'services', 'ruleset'):
                    # These templates inspect this host, not a supplied remote host/file.
                    continue
                tool,risk,category=_OPERATIONS[operation]
                item=self.inventory.get(tool)
                desc=self.registry.descriptions[tool]
                recommendations.append(dict(operation=operation,tool=tool,indicator=indicator,
                    installed=bool(item and item.executable),version=item.version if item else None,
                    verified_capabilities=item.verified_capabilities if item else (),
                    risk=risk.value,category=category,capabilities=desc.capabilities,
                    limits=desc.limits,prerequisites=desc.prerequisites,
                    method='Examiner la proposition puis preparer et demander un accord humain.',
                    preferred_in_mode=category in modes['categories']))
        return dict(indicators=indicators,objectives=objectives,recommendations=tuple(recommendations),
                    mode=mode,categories=modes['categories'])

    def prepare(self, request):
        """focus_contracts.ToolService ; la representation argv reste dans get_prepared."""
        operation=self.prepare_operation(request.operation, request.arguments, tool_id=request.tool_id)
        return ToolResult(request.id, operation.review(), operation.display)

    def get_prepared(self, operation_id):
        return self._prepared[operation_id]

    def prepare_operation(self, operation, parameters=None, *, tool_id=None, mode='assist', scenario='',
                          timeout=10.0, output_limit=65536):
        params=dict(parameters or {})
        if operation not in _OPERATIONS:
            raise ValueError('Operation non prise en charge')
        name,risk,_=_OPERATIONS[operation]
        if tool_id is not None and tool_id!=name:
            raise ValueError('Outil incompatible')
        ModeRegistry().get_mode(mode)
        if not isinstance(scenario,str) or len(scenario)>256:
            raise ValueError('Scenario invalide')
        if type(output_limit) is not int or not 0 < timeout<=300 or not 0<output_limit<=4*1024*1024:
            raise ValueError('Bornes invalides')
        allowed={'target','reason'} if operation=='ports' else {'target','since'} if operation=='logs' else {'target'}
        if set(params)-allowed or any(not isinstance(v,str) for v in params.values()):
            raise ValueError('Parametre inconnu ou non textuel')
        installed=self.inventory.get(name)
        if not installed or not installed.executable:
            raise ToolUnavailable(name)
        target=params.get('target','')
        resource=()
        if operation in _FILE_OPS:
            indicator=identify(target,kind='file')
            path=Path(indicator.value).resolve(strict=True)
            st=path.stat()
            if not stat.S_ISREG(st.st_mode) or not os.access(path,os.R_OK):
                raise ValueError('Fichier regulier lisible requis')
            target=str(path)
            resource=identity(path)
        elif operation in _NETWORK_OPS:
            indicator=identify(target)
            if indicator.kind=='url':
                indicator=identify(urlsplit(indicator.value).hostname)
            if indicator.kind not in ('ipv4','ipv6','domain'):
                raise ValueError('Cible reseau requise')
            target=indicator.value
        elif operation=='manual':
            if target not in self.registry.descriptions:
                raise ValueError('Sujet de manuel absent du catalogue')
        elif target:
            raise ValueError('Cette operation n’accepte pas de cible')
        else:
            target='local'
        args={
            'interfaces': ('-j','address','show'), 'sockets': ('-t','-u','-n'),
            'dns': (('-x',target) if operation=='dns' and identify(target).kind in ('ipv4','ipv6') else (target,'A'))+('+time=2','+tries=1'), 'registration': (target,),
            'ports': ('-sT','-Pn','-n','--max-retries','1','--host-timeout','20s','-p','1-1024',target),
            'metadata': ('-json',target), 'pcap': ('-n','-r',target,'-c','100'),
            'identify': ('--brief','--',target), 'hash': ('--',target),
            'strings': ('-n','8','--',target), 'signatures': (target,),
            'logs': ('--no-pager','-n','100','-o','json'), 'ruleset': ('list','ruleset'),
            'manual': ('-P','cat','--',target), 'services': ('--no-pager','list-units','--type=service'),
        }[operation]
        if operation == 'ports' and identify(target).kind == 'ipv6':
            args = ('-6', *args)
        if 'reason' in params:
            if params['reason']!='true' or '--reason' not in installed.help_options:
                raise ValueError('Option --reason non verifiee par --help')
            args=('--reason',*args)
        if 'since' in params:
            if ('--since' not in installed.help_options or
                not re.fullmatch(r'\d{4}-\d{2}-\d{2}',params['since'])):
                raise ValueError('Option --since inconnue ou date invalide')
            import datetime
            datetime.date.fromisoformat(params['since'])
            args=(*args,'--since',params['since'])
        effects=('Trafic DNS/WHOIS ; cible divulguee au service et aux intermediaires.'
            if risk in (Risk.NETWORK,Risk.PASSIVE_INTELLIGENCE) else
            'Connexions TCP actives, alertes et charge possibles ; accord du proprietaire requis.'
            if risk==Risk.ACTIVE else 'Lecture locale ; atime et traces systeme possibles, contenu sensible.')
        prepared=PreparedOperation(uuid.uuid4().hex,name,operation,installed.executable,tuple(args),target,
            ('ports TCP 1-1024 sur une cible' if operation=='ports' else 'Ressource exacte uniquement'),
            risk,mode,scenario,installed.version,
            'Proposition non verifiee fonctionnellement ; version '+(installed.version or 'inconnue')+
            '. Options facultatives verifiees dans --help uniquement.',
            installed.identity,resource,timeout,output_limit,effects,
            'Privileges administrateur possibles ; execution interdite ici' if risk==Risk.PRIVILEGED else 'Utilisateur courant uniquement',
            target if operation in _NETWORK_OPS else 'Aucun envoi reseau demande',
            'Verifier code retour, stderr et contenu ; succes du processus ne prouve pas la conclusion.',
            'Aucune annulation des paquets ou des lectures deja effectuees ; arret du groupe possible.')
        self._prepared[prepared.id]=prepared
        if self.audit:
            self.audit.record(prepared,'prepared')
        return prepared

    def request_approval(self, operation):
        if self._authority is None or self.audit is None or self._prepared.get(operation.id) is not operation:
            raise PermissionError('Preparation, audit et autorite humaine requis')
        request = self._authority.request(operation)
        self.audit.record(operation, 'requested')
        return request

    def decide_approval(self, operation, request, decision, *, actor):
        if self._authority is None or self.audit is None or self._prepared.get(operation.id) is not operation:
            raise PermissionError('Operation inconnue')
        try:
            approval = self._authority.decide(operation, request, decision, actor=actor)
        except PermissionError:
            self.audit.record(operation, 'denied')
            raise
        self.audit.record(operation, 'approved', approval=approval)
        return approval

    def execute(self, operation, approval, *, authority, cancel=None):
        """Only the human host calls this; it must supply its private authority."""
        try:
            if self._prepared.get(operation.id) is not operation:
                raise PermissionError('Operation non preparee par ce service')
            if authority is not self._authority or type(authority) is not HumanApprovalAuthority:
                raise PermissionError('Autorite humaine non raccordee')
            authority.consume(operation,approval)
            if operation.risk in (Risk.PRIVILEGED,Risk.LOCAL_CHANGE):
                raise PermissionError('Modification/privileges interdits par cet executeur')
            if os.geteuid()==0 or os.getuid()!=os.geteuid() or os.stat(operation.program).st_mode & (stat.S_ISUID|stat.S_ISGID):
                raise PermissionError('Execution privilegiee refusee')
            if identity(operation.program)!=operation.executable_identity:
                raise PermissionError('Executable modifie : preparer a nouveau')
            if operation.resource_identity and identity(operation.target)!=operation.resource_identity:
                raise PermissionError('Ressource modifiee : preparer a nouveau')
            if self.audit is None:
                raise PermissionError('Audit requis pour executer')
        except (PermissionError,OSError):
            if authority is self._authority and type(authority) is HumanApprovalAuthority and isinstance(approval, Approval):
                authority.revoke(approval)
            known = self._prepared.get(operation.id)
            if self.audit and known is not None:
                self.audit.record(known,'denied')
            raise
        self.audit.record(operation,'started',approval=approval)
        result=run(operation.program,operation.args,timeout=operation.timeout,
                   output_limit=operation.output_limit,cancel=cancel)
        self.audit.record(operation,'finished',approval=approval,result=result)
        if result.status == 'succeeded':
            item = self.inventory[operation.tool_id]
            capability = 'invocation:' + operation.operation
            self.inventory[operation.tool_id] = replace(item, verified_capabilities=tuple(
                sorted(set(item.verified_capabilities) | {capability})))
        return result


class ProposalTools:
    """Surface a transmettre aux scenarios/IA : donnees et preparation seulement."""
    def __init__(self, service):
        self.__service = service

    def prepare(self, request):
        return self.__service.prepare(request)

    def analyze(self, text, *, mode='assist'):
        return self.__service.analyze(text, mode=mode)

    def tools_for_mode(self, mode='assist'):
        return self.__service.tools_for_mode(mode)
