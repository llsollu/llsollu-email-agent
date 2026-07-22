"""T2(mail_scheduler) 뷰용 데이터 API — 실행 로그 + 스케줄 on/off."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.agents import _get_owned_agent
from app.auth.deps import get_current_user
from app.db import get_db
from app.models import AgentRun, Schedule, User
from app.schemas.models import RunOut, ScheduleOut, ScheduleToggle

router = APIRouter()


@router.get("/{agent_id}/runs", response_model=list[RunOut])
async def list_runs(
    agent_id: uuid.UUID, limit: int = 50,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    await _get_owned_agent(agent_id, user, db)
    res = await db.execute(
        select(AgentRun).where(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.started_at.desc()).limit(min(limit, 200))
    )
    return [RunOut.model_validate(r) for r in res.scalars().all()]


@router.get("/{agent_id}/schedule", response_model=ScheduleOut | None)
async def get_schedule(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_owned_agent(agent_id, user, db)
    res = await db.execute(select(Schedule).where(Schedule.agent_id == agent_id))
    sched = res.scalar_one_or_none()
    return ScheduleOut.model_validate(sched) if sched else None


@router.patch("/{agent_id}/schedule", response_model=ScheduleOut)
async def toggle_schedule(
    agent_id: uuid.UUID, body: ScheduleToggle,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """스케줄 on/off 토글."""
    await _get_owned_agent(agent_id, user, db)
    res = await db.execute(select(Schedule).where(Schedule.agent_id == agent_id))
    sched = res.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="스케줄이 없습니다(스케줄형 에이전트가 아님)")
    sched.enabled = body.enabled
    await db.commit()
    await db.refresh(sched)
    return ScheduleOut.model_validate(sched)
