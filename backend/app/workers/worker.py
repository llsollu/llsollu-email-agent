"""arq 워커 진입점.

실행: `arq app.workers.worker.WorkerSettings`
- run_agent / setup_agent 태스크 처리
- 매분 cron: dispatch_schedules(도래 스케줄 → run 투입), poll_mailboxes(수신 메일 폴링)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from arq import cron
from croniter import croniter
from sqlalchemy import delete, select, update

from app.config import settings
from app.db import SessionLocal
from app.framework.registry import load_builtin_templates
from app.models import Agent, AgentRun, Project, Schedule
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
        # 커서 경계에서의 유실 방지를 위해 overlap 만큼 겹쳐 조회(재분석은 멱등).
        try:
            base_dt = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
            query_since = (base_dt - timedelta(seconds=settings.mail_poll_overlap_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            query_since = since_iso
        try:
            messages = await graph_client.list_messages(mailbox, since_iso=query_since, top=settings.mail_poll_top)
        except Exception:  # noqa: BLE001
            continue
        newest = since_iso
        for msg in messages:
            rcv = msg.get("receivedDateTime")
            # 커서보다 엄격히 최신인 메일만 처리(overlap 로 재조회된 기존 메일 재큐 방지).
            if not rcv or rcv <= since_iso:
                continue
            await redis.enqueue_job("run_agent", str(agent.id), "email", msg)
            enqueued += 1
            if newest is None or rcv > newest:
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


async def prune_agent_runs(ctx) -> dict:
    """보존 기간(run_retention_days) 경과한 실행 이력 삭제 → agent_runs 무한 적재 방지."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.run_retention_days)
    async with SessionLocal() as db:
        res = await db.execute(
            delete(AgentRun).where(AgentRun.started_at < cutoff)
        )
        await db.commit()
        return {"deleted": res.rowcount or 0}


async def archive_projects(ctx) -> dict:
    """완료 후 project_archive_days 경과한 카드를 아카이브 → 보드 무한 누적 방지."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.project_archive_days)
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        res = await db.execute(
            update(Project)
            .where(
                Project.status == "completed",
                Project.archived_at.is_(None),
                Project.last_activity_at < cutoff,
            )
            .values(archived_at=now)
        )
        await db.commit()
        return {"archived": res.rowcount or 0}


async def _startup(ctx) -> None:
    load_builtin_templates()


class WorkerSettings:
    redis_settings = redis_settings()
    functions = [run_agent, setup_agent, teardown_agent]
    cron_jobs = [
        cron(dispatch_schedules, minute=set(range(60)), run_at_startup=False),
        cron(poll_mailboxes, minute=set(range(60)), run_at_startup=False),
        cron(renew_subscriptions, minute={0, 15, 30, 45}, run_at_startup=True),
        # 장기 운용 정리(하루 1회, 새벽)
        cron(prune_agent_runs, hour={4}, minute={10}, run_at_startup=False),
        cron(archive_projects, hour={4}, minute={20}, run_at_startup=False),
    ]
    on_startup = _startup
    max_jobs = 10
