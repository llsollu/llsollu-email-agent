"""arq 워커 진입점.

실행: `arq app.workers.worker.WorkerSettings`
- run_agent / setup_agent 태스크 처리
- 매분 cron: dispatch_schedules(도래 스케줄 → run 투입), poll_mailboxes(수신 메일 폴링)
"""

from __future__ import annotations

from datetime import datetime, timezone

from arq import cron
from croniter import croniter
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.framework.registry import load_builtin_templates
from app.models import Agent, Schedule
from app.services.graph import graph_client
from app.services.queue import redis_settings
from app.workers.tasks import SUBSCRIPTION_MINUTES, run_agent, setup_agent, teardown_agent


async def dispatch_schedules(ctx) -> dict:
    """도래한(enabled, next_run_at<=now) 스케줄을 찾아 run 투입 후 next_run_at 재계산."""
    from zoneinfo import ZoneInfo

    now = datetime.now(timezone.utc)
    dispatched = 0
    async with SessionLocal() as db:
        res = await db.execute(
            select(Schedule).where(Schedule.enabled.is_(True), Schedule.next_run_at <= now)
        )
        for sched in res.scalars().all():
            agent = await db.get(Agent, sched.agent_id)
            if not agent or agent.deleted_at is not None or agent.status != "active":
                continue
            await ctx["redis"].enqueue_job("run_agent", str(sched.agent_id), "schedule", {})
            # 다음 실행은 스케줄 자신의 타임존 기준으로 재계산 (aware 로 저장)
            base = datetime.now(ZoneInfo(sched.timezone))
            sched.last_run_at = now
            sched.next_run_at = croniter(sched.cron, base).get_next(datetime)
            dispatched += 1
        await db.commit()
    return {"dispatched": dispatched}


async def poll_mailboxes(ctx) -> dict:
    """Graph webhook 미사용 환경용 폴링. active project_tracker 에이전트의 새 메일을 run 으로 투입."""
    if not settings.graph_configured or settings.graph_webhook_base_url:
        return {"skipped": "graph 미설정 또는 webhook 모드"}
    redis = ctx["redis"]
    enqueued = 0
    async with SessionLocal() as db:
        res = await db.execute(
            select(Agent).where(
                Agent.template_key == "project_tracker",
                Agent.status == "active",
                Agent.deleted_at.is_(None),
            )
        )
        agents = res.scalars().all()
    for agent in agents:
        mailbox = (agent.config or {}).get("mailbox")
        if not mailbox:
            continue
        cursor_key = f"poll_cursor:{agent.id}"
        since = await redis.get(cursor_key)
        since_iso = since.decode() if since else None
        # 커서 없음(콜드스타트/구버전 에이전트) → 지금을 커서로 기록하고 이번 라운드는 건너뜀
        if since_iso is None:
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            await redis.set(cursor_key, now_iso)
            continue
        try:
            messages = await graph_client.list_messages(mailbox, since_iso=since_iso, top=25)
        except Exception:  # noqa: BLE001
            continue
        newest = since_iso
        for msg in messages:
            await redis.enqueue_job("run_agent", str(agent.id), "email", msg)
            enqueued += 1
            rcv = msg.get("receivedDateTime")
            if rcv and (newest is None or rcv > newest):
                newest = rcv
        if newest and newest != since_iso:
            await redis.set(cursor_key, newest)
    return {"enqueued": enqueued}


async def renew_subscriptions(ctx) -> dict:
    """만료 임박한 Graph 구독을 갱신. webhook 모드에서만 동작."""
    if not (settings.graph_configured and settings.graph_webhook_base_url):
        return {"skipped": "폴링 모드"}
    from datetime import datetime, timedelta, timezone

    from sqlalchemy.orm.attributes import flag_modified

    soon = datetime.now(timezone.utc) + timedelta(minutes=45)
    renewed = 0
    async with SessionLocal() as db:
        res = await db.execute(
            select(Agent).where(Agent.status == "active", Agent.deleted_at.is_(None))
        )
        for agent in res.scalars().all():
            sub = (agent.config or {}).get("_graph_subscription")
            if not sub or not sub.get("id"):
                continue
            try:
                exp = datetime.fromisoformat(str(sub.get("expires")).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                exp = soon  # 파싱 실패 시 갱신 시도
            if exp <= soon:
                try:
                    r = await graph_client.renew_subscription(sub["id"], minutes=SUBSCRIPTION_MINUTES)
                    sub["expires"] = r.get("expirationDateTime")
                    agent.config = {**agent.config, "_graph_subscription": sub}
                    flag_modified(agent, "config")
                    renewed += 1
                except Exception:  # noqa: BLE001
                    continue
        await db.commit()
    return {"renewed": renewed}


async def _startup(ctx) -> None:
    load_builtin_templates()


class WorkerSettings:
    redis_settings = redis_settings()
    functions = [run_agent, setup_agent, teardown_agent]
    cron_jobs = [
        cron(dispatch_schedules, minute=set(range(60)), run_at_startup=False),
        cron(poll_mailboxes, minute=set(range(60)), run_at_startup=False),
        cron(renew_subscriptions, minute={0, 15, 30, 45}, run_at_startup=True),
    ]
    on_startup = _startup
    max_jobs = 10
