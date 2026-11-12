# ============================================================================
# UCHAMBUZI - Assistant IA local pour l'investigation numerique
# ============================================================================
# Fichier       : focus_contracts.py
# Role          : Contrats communs typés de l'architecture Focus
# Projet initie : Wakanda (WKD) - 2026
# Contributions : Communaute des developpeurs UCHAMBUZI
# Copyright     : (c) 2026 Wakanda (WKD) et contributeurs respectifs
# ============================================================================
"""Contrats v1 en mémoire ; aucun format de stockage ou transport implicite."""
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Mapping, Protocol, Sequence, Union

CONTRACT_VERSION = 1


class Role(str, Enum):
    USER = 'user'
    ASSISTANT = 'assistant'


class TurnState(str, Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    COMPLETE = 'complete'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass(frozen=True)
class Message:
    id: str
    role: Role
    text: str


@dataclass(frozen=True)
class Model:
    provider: str
    id: str
    local: bool


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    instructions: str = ''


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str = ''


@dataclass(frozen=True)
class Settings:
    model: Model | None = None
    profile_id: str | None = None
    timeout_seconds: float = 300.0
    context_budget_bytes: int = 16000


@dataclass(frozen=True)
class SessionSnapshot:
    id: str
    messages: tuple[Message, ...] = ()
    settings: Settings = field(default_factory=Settings)
    scenario_id: str | None = None


@dataclass(frozen=True)
class ToolRequest:
    id: str
    tool_id: str
    operation: str
    arguments: Mapping[str, str]


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    summary: str
    prepared_command: str | None = None


@dataclass(frozen=True)
class ConfirmationRequest:
    id: str
    action: str
    details: str


@dataclass(frozen=True)
class ConfirmationDecision:
    request_id: str
    approved: bool


@dataclass(frozen=True)
class TurnStarted:
    turn_id: str
    message_id: str


@dataclass(frozen=True)
class TextDelta:
    turn_id: str
    text: str


@dataclass(frozen=True)
class TurnFinished:
    turn_id: str
    state: TurnState
    error_code: str | None = None
    # Message sûr pour l'utilisateur ; jamais de contenu d'enquête dans les logs.
    message: str | None = None

    def __post_init__(self):
        if self.state not in (TurnState.COMPLETE, TurnState.FAILED, TurnState.CANCELLED):
            raise ValueError('Un événement final exige un état terminal.')
        if self.state == TurnState.FAILED and not self.error_code:
            raise ValueError('Une erreur exige un code stable.')
        if self.state != TurnState.FAILED and self.error_code is not None:
            raise ValueError('Un code erreur exige un échec.')


ConversationEvent = Union[TurnStarted, TextDelta, TurnFinished]


class ConversationEngine(Protocol):
    def stream(self, turn_id: str, message: Message) -> AsyncIterator[ConversationEvent]: ...


class SessionStore(Protocol):
    def load(self, session_id: str) -> SessionSnapshot: ...
    def save(self, snapshot: SessionSnapshot) -> None: ...


class Catalog(Protocol):
    def profiles(self) -> Sequence[Profile]: ...
    def scenarios(self) -> Sequence[Scenario]: ...


class ToolService(Protocol):
    def prepare(self, request: ToolRequest) -> ToolResult: ...


class ConfirmationService(Protocol):
    async def confirm(self, request: ConfirmationRequest) -> ConfirmationDecision: ...


def approved_for(request: ConfirmationRequest, decision: ConfirmationDecision) -> bool:
    """Un accord ne vaut que pour la demande exacte ; absence/refus => interdit."""
    return decision.request_id == request.id and decision.approved is True
