"""관리자 전용 API. 메타데이터·집계·운영 상태만 다루며 타인의 메일 내용은 노출하지 않는다."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Date, cast, delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_admin_user, is_effective_admin
from app.config import settings
from app.db import get_db
from app.models import Agent, AgentRun, LLMJob, Project, User

router = APIRouter(prefix="/admin")


# ─────────── 사용자 ───────────
@router.get("/users")
async def list_users(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    counts = dict((await db.execute(
        select(Agent.owner_user_id, func.count())
        .where(Agent.deleted_at.is_(None)).group_by(Agent.owner_user_id)
    )).all())
    return [
        {
            "id": str(u.id), "email": u.email, "display_name": u.display_name,
            "department": u.department,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "agent_count": counts.get(u.id, 0),
            "is_admin": is_effective_admin(u),
            "is_active": u.is_active,
            "bootstrap": settings.is_bootstrap_admin(u.email),
            "has_password": bool(u.password_hash),
        }
        for u in users
    ]


class UserPatch(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None
    reset_password: bool | None = None


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: uuid.UUID, body: UserPatch,
    admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 부트스트랩 관리자(env)는 권한/활성 변경 불가 — 잠금장치.
    locked = settings.is_bootstrap_admin(target.email)
    if body.is_admin is not None:
        if locked:
            raise HTTPException(status_code=400, detail="환경변수로 지정된 관리자는 권한을 변경할 수 없습니다")
        target.is_admin = body.is_admin
    if body.is_active is not None:
        if target.id == admin.id:
            raise HTTPException(status_code=400, detail="본인 계정은 비활성화할 수 없습니다")
        if locked and body.is_active is False:
            raise HTTPException(status_code=400, detail="환경변수로 지정된 관리자는 비활성화할 수 없습니다")
        target.is_active = body.is_active
    if body.reset_password:
        target.password_hash = None  # 다음 로그인 시 비밀번호 재설정 유도
    await db.commit()
    return {"status": "ok"}


# ─────────── 에이전트 현황 ───────────
@router.get("/agents")
async def list_all_agents(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Agent, User.email, User.display_name)
        .join(User, User.id == Agent.owner_user_id)
        .where(Agent.deleted_at.is_(None)).order_by(Agent.status.desc(), Agent.created_at)
    )).all()
    # 에이전트별 최근 실행 1건
    last_runs: dict[uuid.UUID, AgentRun] = {}
    ids = [a.id for a, _, _ in rows]
    if ids:
        run_rows = (await db.execute(
            select(AgentRun).where(AgentRun.agent_id.in_(ids)).order_by(AgentRun.started_at.desc())
        )).scalars().all()
        for r in run_rows:
            last_runs.setdefault(r.agent_id, r)
    out = []
    for a, email, name in rows:
        lr = last_runs.get(a.id)
        out.append({
            "id": str(a.id), "name": a.name, "template_key": a.template_key,
            "status": a.status, "error_detail": a.error_detail,
            "owner": name or email, "owner_email": email,
            "last_run_at": lr.started_at.isoformat() if lr else None,
            "last_run_status": lr.status if lr else None,
        })
    return out


# ─────────── LLM 사용량 ───────────
@router.get("/usage")
async def usage(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    six_ago = (month_start - timedelta(days=170)).replace(day=1)

    # 월별 토큰(최근 6개월). cast 를 GROUP BY 에 직접 쓰면 바인드 파라미터 불일치로
    # Postgres 가 거부하므로 라벨로 그룹/정렬.
    mcol = cast(func.date_trunc("month", LLMJob.created_at), Date).label("m")
    monthly = (await db.execute(
        select(mcol, func.coalesce(func.sum(LLMJob.tokens_in + LLMJob.tokens_out), 0), func.count())
        .where(LLMJob.created_at >= six_ago)
        .group_by("m").order_by("m")
    )).all()

    # 이번 달 사용자별(에이전트 소유자 기준)
    by_user = (await db.execute(
        select(User.display_name, User.email, func.coalesce(func.sum(LLMJob.tokens_in + LLMJob.tokens_out), 0), func.count())
        .select_from(LLMJob).join(Agent, Agent.id == LLMJob.agent_id).join(User, User.id == Agent.owner_user_id)
        .where(LLMJob.created_at >= month_start)
        .group_by(User.id, User.display_name, User.email)
        .order_by(func.sum(LLMJob.tokens_in + LLMJob.tokens_out).desc()).limit(10)
    )).all()

    total = (await db.execute(
        select(func.coalesce(func.sum(LLMJob.tokens_in + LLMJob.tokens_out), 0), func.count())
        .where(LLMJob.created_at >= month_start)
    )).one()

    return {
        "monthly": [{"month": str(m), "tokens": int(t), "count": int(c)} for m, t, c in monthly],
        "by_user": [{"name": n or e, "tokens": int(t), "count": int(c)} for n, e, t, c in by_user],
        "month_total_tokens": int(total[0]), "month_total_count": int(total[1]),
    }


# ─────────── 운영 상태 ───────────
@router.get("/ops")
async def ops(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    from arq import create_pool

    from app.services.queue import redis_settings

    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_24h = (await db.execute(
        select(func.count()).where(AgentRun.status == "error", AgentRun.started_at >= day_ago)
    )).scalar() or 0
    recent_fail = (await db.execute(
        select(AgentRun.trigger_source, AgentRun.error, AgentRun.started_at, Agent.name)
        .join(Agent, Agent.id == AgentRun.agent_id)
        .where(AgentRun.status == "error").order_by(AgentRun.started_at.desc()).limit(8)
    )).all()

    mode = "webhook" if (settings.graph_configured and settings.graph_webhook_base_url) else (
        "polling" if settings.graph_configured else "disabled")

    heartbeat = None
    queued = None
    try:
        pool = await create_pool(redis_settings())
        try:
            hb = await pool.get("worker:heartbeat")
            heartbeat = hb.decode() if hb else None
            queued = await pool.zcard("arq:queue")
        finally:
            await pool.close()
    except Exception:  # noqa: BLE001
        pass

    return {
        "collect_mode": mode,
        "worker_heartbeat": heartbeat,
        "queued": queued,
        "failed_24h": failed_24h,
        "recent_failures": [
            {"agent": name, "trigger": trig, "error": (err or "")[:200], "at": at.isoformat() if at else None}
            for trig, err, at, name in recent_fail
        ],
    }


# ─────────── 데이터·용량 ───────────
_TABLES = ["mail_records", "agent_runs", "projects", "issues", "llm_jobs", "sent_records"]


@router.get("/capacity")
async def capacity(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    rows = []
    for t in _TABLES:
        # 행 수는 통계 추정치(reltuples)로 대량 테이블에서도 즉시 응답.
        est = (await db.execute(
            text("SELECT reltuples::bigint FROM pg_class WHERE relname = :t"), {"t": t}
        )).scalar()
        # reltuples 가 음수(ANALYZE 전)면 정확한 count 로 폴백(그런 테이블은 대개 작음).
        if est is None or est < 0:
            est = (await db.execute(text(f"SELECT count(*) FROM {t}"))).scalar()  # noqa: S608 (고정 화이트리스트)
        size = (await db.execute(
            text("SELECT pg_total_relation_size(:t)"), {"t": t}
        )).scalar()
        rows.append({"table": t, "rows": int(est or 0), "bytes": int(size or 0)})
    db_size = (await db.execute(text("SELECT pg_database_size(current_database())"))).scalar()
    return {
        "tables": rows,
        "db_bytes": int(db_size or 0),
        "settings": {
            "run_retention_days": settings.run_retention_days,
            "project_archive_days": settings.project_archive_days,
        },
    }


@router.post("/maintenance/prune-runs")
async def prune_runs(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.run_retention_days)
    res = await db.execute(delete(AgentRun).where(AgentRun.started_at < cutoff))
    await db.commit()
    return {"deleted": res.rowcount or 0}


@router.post("/maintenance/archive-projects")
async def archive_projects_now(_: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.project_archive_days)
    now = datetime.now(timezone.utc)
    res = await db.execute(
        update(Project).where(
            Project.status == "completed", Project.archived_at.is_(None), Project.last_activity_at < cutoff
        ).values(archived_at=now)
    )
    await db.commit()
    return {"archived": res.rowcount or 0}
