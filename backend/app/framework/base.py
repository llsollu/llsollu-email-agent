"""에이전트 템플릿 프레임워크의 핵심 타입.

Agent = Trigger(언제) · Source(무엇을) · Processor(어떻게) · Action(무엇을) · View(어떻게 보여줄지)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from app.framework.context import RunContext, RunResult, SetupContext

TriggerKind = Literal["event", "schedule"]
FieldType = Literal["string", "text", "secret", "email", "url", "select", "cron", "bool", "int"]


@dataclass
class ConfigField:
    key: str
    label: str
    type: FieldType = "string"
    required: bool = False
    help: str | None = None
    options: list[str] | None = None
    default: object | None = None
    secret: bool = False  # True면 secrets_enc 로 저장


@dataclass
class TriggerSpec:
    kind: TriggerKind
    # event: 구독 대상(예: "mailbox" 설정 키). schedule: 기본 cron 힌트.
    detail: dict = field(default_factory=dict)


@dataclass
class ViewSpec:
    view_type: str  # 프론트 뷰 레지스트리 키 (예: "kanban", "scheduler_panel")
    data_endpoints: list[str] = field(default_factory=list)


@runtime_checkable
class AgentTemplate(Protocol):
    key: str
    name: str
    version: str
    description: str
    trigger: TriggerSpec
    view: ViewSpec

    def config_schema(self) -> list[ConfigField]: ...

    async def on_setup(self, ctx: SetupContext) -> None: ...

    async def handle(self, ctx: RunContext) -> RunResult: ...

    async def on_teardown(self, ctx: SetupContext) -> None: ...


class BaseTemplate:
    """선택적 기본 구현 — on_setup/on_teardown 기본 no-op."""

    key: str = ""
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    trigger: TriggerSpec
    view: ViewSpec

    def config_schema(self) -> list[ConfigField]:
        return []

    async def on_setup(self, ctx: SetupContext) -> None:
        return None

    async def on_teardown(self, ctx: SetupContext) -> None:
        return None

    async def handle(self, ctx: RunContext) -> RunResult:
        raise NotImplementedError
