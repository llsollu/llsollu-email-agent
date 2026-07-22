"""워커 태스크: 에이전트 실행(run_agent)과 프로비저닝(setup_agent)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.config import settings
from app.db import SessionLocal
from app.framework.context import RunContext, SetupContext
from app.framework.registry import get_template
from app.models import Agent, AgentRun, Schedule
from app.services.crypto import decrypt_secrets
from app.services.graph import graph_client
from app.services.llm import LLMClient

SUBSCRIPTION_MINUTES = 120  # 갱신 주기보다 넉넉히

_llm = LLMClient()


async def run_agent(ctx, agent_id: str, trigger: str, payload: dict) -> dict:
    aid = uuid.UUID(agent_id)
    async with SessionLocal() as db:
        agent = await db.get(Agent, aid)
        if not agent or agent.deleted_at is not None:
            return {"skipped": "agent not found"}
        if agent.status not in ("active",) and trigger != "manual":
            return {"skipped": f"status={agent.status}"}

        template = get_template(agent.template_key)
        run = AgentRun(agent_id=aid, trigger_source=trigger, status="running")
        db.add(run)
        await db.flush()

        rctx = RunContext(
            agent_id=aid, run_id=run.id, trigger_source=trigger,
            config=agent.config or {}, secrets=decrypt_secrets(agent.secrets_enc),
            db=db, llm=_llm, graph=graph_client,
            trigger_payload=payload or {}, dry_run=bool((payload or {}).get("dry_run")),
        )
        try:
            result = await template.handle(rctx)
            run.status = "ok" if result.ok else "error"
            run.stats = {**result.stats, "events": rctx._events}
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return run.stats
        except Exception as e:  # noqa: BLE001
            run.status = "error"
            run.error = str(e)
            run.stats = {"events": rctx._events}
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            raise


async def setup_agent(ctx, agent_id: str) -> dict:
    aid = uuid.UUID(agent_id)
    async with SessionLocal() as db:
        agent = await db.get(Agent, aid)
        if not agent:
            return {"skipped": "not found"}
        template = get_template(agent.template_key)
        sctx = SetupContext(
            agent_id=aid, config=agent.config or {},
            secrets=decrypt_secrets(agent.secrets_enc), db=db, graph=graph_client,
        )
        try:
            await template.on_setup(sctx)
            # 스케줄형이면 Schedule 업서트
            if template.trigger.kind == "schedule":
                await _upsert_schedule(db, agent, template)
            # 이벤트형(메일 수신)
            if template.trigger.kind == "event":
                if settings.graph_webhook_base_url and settings.graph_configured:
                    await _ensure_subscription(agent, template)
                else:
                    # 폴링 모드: 활성화 시점을 커서로 기록 → 콜드스타트 시 과거 메일 일괄 처리 방지
                    cursor = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    await ctx["redis"].set(f"poll_cursor:{agent.id}", cursor, nx=True)
            agent.status = "active"
            agent.error_detail = None
        except Exception as e:  # noqa: BLE001
            agent.status = "error"
            agent.error_detail = str(e)
        await db.commit()
        return {"status": agent.status}


async def teardown_agent(ctx, agent_id: str, config: dict) -> dict:
    """삭제 시 정리: Graph 구독 해제."""
    sub = (config or {}).get("_graph_subscription")
    if sub and sub.get("id"):
        try:
            await graph_client.delete_subscription(sub["id"])
        except Exception:  # noqa: BLE001
            pass
    return {"status": "torn_down"}


async def _ensure_subscription(agent: Agent, template) -> None:
    """webhook 모드일 때만 구독 생성. base_url 미설정(폴링 모드)이면 skip."""
    if not (settings.graph_webhook_base_url and settings.graph_configured):
        return
    mailbox_field = template.trigger.detail.get("mailbox_field", "mailbox")
    mailbox = (agent.config or {}).get(mailbox_field)
    if not mailbox:
        raise ValueError(f"{mailbox_field} 설정이 필요합니다(webhook 구독)")

    # 기존 구독 있으면 먼저 해제
    old = (agent.config or {}).get("_graph_subscription")
    if old and old.get("id"):
        try:
            await graph_client.delete_subscription(old["id"])
        except Exception:  # noqa: BLE001
            pass

    url = settings.graph_webhook_base_url.rstrip("/") + "/api/webhooks/graph"
    sub = await graph_client.create_subscription(mailbox, url, minutes=SUBSCRIPTION_MINUTES)
    agent.config = {
        **(agent.config or {}),
        "_graph_subscription": {
            "id": sub.get("id"),
            "expires": sub.get("expirationDateTime"),
            "mailbox": mailbox,
        },
    }
    flag_modified(agent, "config")


async def _upsert_schedule(db, agent: Agent, template) -> None:
    from zoneinfo import ZoneInfo

    cron = (agent.config or {}).get("cron") or template.trigger.detail.get("default_cron", "0 9 * * *")
    # cron 은 SCHEDULER_TZ(예: Asia/Seoul) 기준으로 해석하고, aware datetime 으로 저장.
    base = datetime.now(ZoneInfo(settings.scheduler_tz))
    res = await db.execute(select(Schedule).where(Schedule.agent_id == agent.id))
    sched = res.scalar_one_or_none()
    next_run = croniter(cron, base).get_next(datetime)
    if sched is None:
        db.add(Schedule(agent_id=agent.id, cron=cron, timezone=settings.scheduler_tz,
                        next_run_at=next_run, enabled=True))
    else:
        sched.cron = cron
        sched.next_run_at = next_run
