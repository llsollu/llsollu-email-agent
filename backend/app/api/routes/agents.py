from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db import get_db
from app.framework.registry import get_template
from app.models import Agent, User
from app.schemas.models import AgentCreate, AgentOut, AgentUpdate
from app.services.crypto import decrypt_secrets, encrypt_secrets
from app.services.queue import enqueue_run, enqueue_setup, enqueue_teardown

router = APIRouter()


async def _get_owned_agent(agent_id: uuid.UUID, user: User, db: AsyncSession) -> Agent:
    res = await db.execute(
        select(Agent).where(
            Agent.id == agent_id, Agent.owner_user_id == user.id, Agent.deleted_at.is_(None)
        )
    )
    agent = res.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="에이전트를 찾을 수 없습니다")
    return agent


def _to_out(agent: Agent) -> AgentOut:
    view_type = None
    try:
        view_type = get_template(agent.template_key).view.view_type
    except KeyError:
        pass
    return AgentOut(
        id=agent.id, template_key=agent.template_key, name=agent.name, status=agent.status,
        error_detail=agent.error_detail, config=agent.config, view_type=view_type,
        created_at=agent.created_at, updated_at=agent.updated_at,
    )


@router.get("", response_model=list[AgentOut])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Agent).where(Agent.owner_user_id == user.id, Agent.deleted_at.is_(None))
        .order_by(Agent.created_at)
    )
    return [_to_out(a) for a in res.scalars().all()]


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    body: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    try:
        get_template(body.template_key)
    except KeyError:
        raise HTTPException(status_code=400, detail="알 수 없는 템플릿")

    agent = Agent(
        owner_user_id=user.id, template_key=body.template_key, name=body.name,
        status="configuring", config=body.config or {},
        secrets_enc=encrypt_secrets(body.secrets) if body.secrets else None,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # 프로비저닝(on_setup)은 워커에서 비동기로 → 프론트는 status 폴링
    await enqueue_setup(str(agent.id))
    return _to_out(agent)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return _to_out(await _get_owned_agent(agent_id, user, db))


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID, body: AgentUpdate,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """⚙️ 설정 화면에서 호출. secret 은 전달된 키만 병합(미입력 시 기존값 유지)."""
    agent = await _get_owned_agent(agent_id, user, db)
    if body.name is not None:
        agent.name = body.name
    if body.config is not None:
        agent.config = {**agent.config, **body.config}
    if body.secrets:
        merged = {**decrypt_secrets(agent.secrets_enc), **body.secrets}
        agent.secrets_enc = encrypt_secrets(merged)
    await db.commit()
    await db.refresh(agent)

    # 설정이 바뀌면 재프로비저닝(구독/스케줄 갱신)
    await enqueue_setup(str(agent.id))
    return _to_out(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = await _get_owned_agent(agent_id, user, db)
    config_snapshot = dict(agent.config or {})
    agent.deleted_at = datetime.now(timezone.utc)
    agent.status = "paused"
    await db.commit()
    # Graph 구독 등 외부 리소스 정리
    await enqueue_teardown(str(agent_id), config_snapshot)


@router.post("/{agent_id}/run")
async def run_now(
    agent_id: uuid.UUID, dry_run: bool = False,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """수동 실행 / 드라이런."""
    agent = await _get_owned_agent(agent_id, user, db)
    await enqueue_run(str(agent.id), "manual", {"dry_run": dry_run})
    return {"status": "enqueued"}
