"""템플릿에 주입되는 실행/셋업 컨텍스트."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.graph import GraphClient
    from app.services.llm import LLMClient


@dataclass
class RunResult:
    ok: bool = True
    stats: dict = field(default_factory=dict)
    message: str | None = None


@dataclass
class SetupContext:
    """on_setup/on_teardown 용. 자격증명 검증·구독 생성 등."""

    agent_id: uuid.UUID
    config: dict
    secrets: dict
    db: AsyncSession
    graph: GraphClient


@dataclass
class RunContext:
    """handle() 용. 워커가 트리거마다 생성."""

    agent_id: uuid.UUID
    run_id: uuid.UUID
    trigger_source: str  # schedule|email|manual
    config: dict
    secrets: dict
    db: AsyncSession
    llm: LLMClient
    graph: GraphClient
    trigger_payload: dict = field(default_factory=dict)
    dry_run: bool = False

    _events: list[dict] = field(default_factory=list)

    def log(self, event: str, **data) -> None:
        """agent_run.stats.events 에 누적될 구조화 로그."""
        self._events.append({"event": event, **data})
