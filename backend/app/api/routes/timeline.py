"""타임라인 뷰 데이터 + 원문 메일 조회 API. 공유 mail_records 를 메일함 기준으로 읽는다."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.agents import _get_owned_agent
from app.auth.deps import get_current_user
from app.db import get_db
from app.models import MailRecord, User
from app.schemas.models import MailRecordOut, TimelineEntry

router = APIRouter()


async def _agent_mailbox(agent_id: uuid.UUID, user: User, db: AsyncSession) -> str:
    agent = await _get_owned_agent(agent_id, user, db)
    mailbox = (agent.config or {}).get("mailbox")
    if not mailbox:
        raise HTTPException(status_code=400, detail="mailbox 설정이 없는 에이전트입니다")
    return mailbox


@router.get("/{agent_id}/timeline", response_model=list[TimelineEntry])
async def timeline(
    agent_id: uuid.UUID, limit: int = 100, before: datetime | None = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """received_at 내림차순 페이지네이션. before(커서)보다 과거 건을 limit 만큼 반환."""
    mailbox = await _agent_mailbox(agent_id, user, db)
    stmt = (
        select(MailRecord)
        .where(MailRecord.mailbox == mailbox, MailRecord.analyzed.is_(True))
        .order_by(MailRecord.received_at.desc().nullslast())
        .limit(min(limit, 300))
    )
    if before is not None:
        stmt = stmt.where(MailRecord.received_at < before)
    res = await db.execute(stmt)
    return [TimelineEntry.model_validate(r) for r in res.scalars().all()]


@router.get("/{agent_id}/messages/{message_id}", response_model=MailRecordOut)
async def get_message(
    agent_id: uuid.UUID, message_id: uuid.UUID,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """원문 모달용. 에이전트 메일함에 속한 메일만 반환."""
    mailbox = await _agent_mailbox(agent_id, user, db)
    rec = await db.get(MailRecord, message_id)
    if not rec or rec.mailbox != mailbox:
        raise HTTPException(status_code=404, detail="메일을 찾을 수 없습니다")
    return MailRecordOut.model_validate(rec)
