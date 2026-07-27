"""홈 대시보드 집계 API.

에이전트 구성(분석/스케줄러)에 따라 필요한 섹션만 조립해 반환한다.
모든 수치는 서버에서 GROUP BY 로 집계하고, 시간창(최근 7/30/90일·이번달)으로 제한해
데이터가 커져도 조회 비용이 총량이 아니라 창 크기에 비례하도록 한다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import get_db
from app.models import (
    Agent,
    Issue,
    LLMJob,
    MailRecord,
    Project,
    Schedule,
    SentRecord,
    User,
)

router = APIRouter()


def _day(col):
    return cast(func.date_trunc("day", col), Date)


async def _pairs(db: AsyncSession, stmt) -> list[tuple]:
    return list((await db.execute(stmt)).all())


@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    d7, d14, d30, d90 = (now - timedelta(days=n) for n in (7, 14, 30, 90))
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    res = await db.execute(
        select(Agent).where(Agent.owner_user_id == user.id, Agent.deleted_at.is_(None)).order_by(Agent.created_at)
    )
    agents = res.scalars().all()
    tracker_ids = [a.id for a in agents if a.template_key == "project_tracker"]
    sched_ids = [a.id for a in agents if a.template_key == "mail_scheduler"]

    out: dict = {
        "agents": [
            {"id": str(a.id), "name": a.name, "template_key": a.template_key,
             "status": a.status, "view_type": _view_type(a)}
            for a in agents
        ],
        "analysis": None,
        "scheduler": None,
    }

    if tracker_ids:
        out["analysis"] = await _analysis(db, user.email, tracker_ids, d7, d14, d30, d90, month_start)
    if sched_ids:
        out["scheduler"] = await _scheduler(db, sched_ids, d7, d30, now)

    return out


def _view_type(a: Agent) -> str | None:
    try:
        from app.framework.registry import get_template
        return get_template(a.template_key).view.view_type
    except Exception:  # noqa: BLE001
        return None


async def _analysis(db, mailbox, tracker_ids, d7, d14, d30, d90, month_start) -> dict:
    base = [MailRecord.mailbox == mailbox, MailRecord.analyzed.is_(True)]

    # 일별 분석량(30일)
    daily = await _pairs(
        db,
        select(_day(MailRecord.received_at).label("d"), func.count())
        .where(*base, MailRecord.received_at >= d30)
        .group_by("d").order_by("d"),
    )
    # 카테고리 분포(30일). null 은 '미지정'으로 병합(coalesce 를 GROUP BY 에 쓰면
    # 바인드 파라미터 불일치로 Postgres 가 거부하므로 파이썬에서 병합).
    cat_rows = await _pairs(
        db,
        select(MailRecord.category, func.count())
        .where(*base, MailRecord.received_at >= d30)
        .group_by(MailRecord.category),
    )
    cat_map: dict[str, int] = {}
    for name, c in cat_rows:
        cat_map[name or "미지정"] = cat_map.get(name or "미지정", 0) + c
    cats = sorted(cat_map.items(), key=lambda x: -x[1])
    # 수신 역할(30일)
    role_rows = await _pairs(
        db,
        select(MailRecord.recipient_role, func.count())
        .where(*base, MailRecord.received_at >= d30)
        .group_by(MailRecord.recipient_role),
    )
    roles: dict[str, int] = {}
    for r, c in role_rows:
        roles[r or "other"] = roles.get(r or "other", 0) + c
    # 고객사 Top(90일)
    clients = await _pairs(
        db,
        select(MailRecord.client_name, func.count())
        .where(*base, MailRecord.received_at >= d90, MailRecord.client_name.isnot(None), MailRecord.client_name != "")
        .group_by(MailRecord.client_name).order_by(func.count().desc()).limit(8),
    )
    # 주간/전주 분석량(추세)
    week = (await db.execute(select(func.count()).where(*base, MailRecord.received_at >= d7))).scalar() or 0
    prev = (await db.execute(
        select(func.count()).where(*base, MailRecord.received_at >= d14, MailRecord.received_at < d7)
    )).scalar() or 0

    # 미해결 이슈: 유형/심각도
    itypes = await _pairs(
        db,
        select(Issue.type, func.count())
        .select_from(Issue).join(Project, Project.id == Issue.project_id)
        .where(Project.agent_id.in_(tracker_ids), Issue.status != "resolved")
        .group_by(Issue.type).order_by(func.count().desc()),
    )
    sev = dict(await _pairs(
        db,
        select(Issue.severity, func.count())
        .select_from(Issue).join(Project, Project.id == Issue.project_id)
        .where(Project.agent_id.in_(tracker_ids), Issue.status != "resolved")
        .group_by(Issue.severity),
    ))
    # 카드 상태 분포(비아카이브)
    statuses = dict(await _pairs(
        db,
        select(Project.status, func.count())
        .where(Project.agent_id.in_(tracker_ids), Project.archived_at.is_(None))
        .group_by(Project.status),
    ))
    # LLM 사용량(이번달)
    llm = (await db.execute(
        select(func.coalesce(func.sum(LLMJob.tokens_in), 0), func.coalesce(func.sum(LLMJob.tokens_out), 0), func.count())
        .where(LLMJob.agent_id.in_(tracker_ids), LLMJob.created_at >= month_start)
    )).one()

    # 미해결 이슈 = 스토리보드 + 진행 중 + 보류 카드 합(완료 제외). 칸반 보드와 동일 정의.
    open_issues = statuses.get("storyboard", 0) + statuses.get("active", 0) + statuses.get("on_hold", 0)
    to, cc, other = roles.get("to", 0), roles.get("cc", 0), roles.get("other", 0)
    role_total = to + cc + other or 1
    active_cards = statuses.get("active", 0) + statuses.get("on_hold", 0)

    return {
        "kpis": {
            "week_analyzed": week, "week_prev": prev,
            "open_issues": open_issues, "severity": sev,
            "active_cards": active_cards, "statuses": statuses,
            "direct_ratio": round(to / role_total * 100),
        },
        "daily": [{"date": str(d), "count": c} for d, c in daily],
        "categories": [{"name": n, "count": c} for n, c in cats],
        "clients": [{"name": n, "count": c} for n, c in clients],
        "issue_types": [{"type": t, "count": c} for t, c in itypes],
        "receipt": {"to": to, "cc": cc, "other": other},
        "llm": {"tokens_in": int(llm[0]), "tokens_out": int(llm[1]), "count": int(llm[2])},
    }


async def _scheduler(db, sched_ids, d7, d30, now) -> dict:
    # 주간 성공/실패
    week_rows = dict(await _pairs(
        db,
        select(SentRecord.status, func.count())
        .where(SentRecord.agent_id.in_(sched_ids), SentRecord.sent_at >= d7)
        .group_by(SentRecord.status),
    ))
    # 일별 성공/실패(30일)
    daily_rows = await _pairs(
        db,
        select(_day(SentRecord.sent_at).label("d"), SentRecord.status, func.count())
        .where(SentRecord.agent_id.in_(sched_ids), SentRecord.sent_at >= d30)
        .group_by("d", SentRecord.status).order_by("d"),
    )
    daily: dict[str, dict] = {}
    for d, status, c in daily_rows:
        row = daily.setdefault(str(d), {"date": str(d), "sent": 0, "failed": 0})
        if status == "sent":
            row["sent"] += c
        elif status == "failed":
            row["failed"] += c

    # 최근 발송
    recent = await _pairs(
        db,
        select(SentRecord.agent_id, SentRecord.subject, SentRecord.status, SentRecord.sent_at)
        .where(SentRecord.agent_id.in_(sched_ids))
        .order_by(SentRecord.sent_at.desc()).limit(10),
    )
    # 스케줄(다음 실행/활성)
    scheds = {
        s.agent_id: s
        for s in (await db.execute(select(Schedule).where(Schedule.agent_id.in_(sched_ids)))).scalars().all()
    }
    # 스케줄러별 주간 집계
    per_rows = await _pairs(
        db,
        select(SentRecord.agent_id, SentRecord.status, func.count())
        .where(SentRecord.agent_id.in_(sched_ids), SentRecord.sent_at >= d7)
        .group_by(SentRecord.agent_id, SentRecord.status),
    )
    per: dict = {}
    for aid, status, c in per_rows:
        p = per.setdefault(str(aid), {"sent": 0, "failed": 0})
        if status in ("sent", "failed"):
            p[status] += c

    agent_names = {
        a.id: a.name
        for a in (await db.execute(select(Agent).where(Agent.id.in_(sched_ids)))).scalars().all()
    }
    next_run = None
    for s in scheds.values():
        if s.enabled and s.next_run_at and (next_run is None or s.next_run_at < next_run):
            next_run = s.next_run_at

    return {
        "kpis": {
            "week_sent": week_rows.get("sent", 0),
            "week_failed": week_rows.get("failed", 0),
            "active_schedules": sum(1 for s in scheds.values() if s.enabled),
            "total_schedulers": len(sched_ids),
            "next_run_at": next_run.isoformat() if next_run else None,
        },
        "daily": list(daily.values()),
        "agents": [
            {
                "id": str(aid), "name": agent_names.get(aid, ""),
                "next_run_at": (scheds[aid].next_run_at.isoformat() if aid in scheds and scheds[aid].next_run_at else None),
                "enabled": (scheds[aid].enabled if aid in scheds else False),
                "week_sent": per.get(str(aid), {}).get("sent", 0),
                "week_failed": per.get(str(aid), {}).get("failed", 0),
            }
            for aid in sched_ids
        ],
        "recent": [
            {"agent": agent_names.get(aid, ""), "subject": subj or "(제목 없음)",
             "status": status, "sent_at": sent_at.isoformat() if sent_at else None}
            for aid, subj, status, sent_at in recent
        ],
    }
