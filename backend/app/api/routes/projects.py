"""T1(project_tracker) 뷰용 데이터 API — 칸반."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.agents import _get_owned_agent
from app.auth.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Issue, Project, User
from app.models.project import PROJECT_STATUSES
from app.schemas.models import IssueOut, ProjectOut

router = APIRouter()


class ProjectWithIssues(ProjectOut):
    issues: list[IssueOut] = []


class StatusPatch(BaseModel):
    status: str


@router.get("/{agent_id}/projects", response_model=list[ProjectWithIssues])
async def list_projects(
    agent_id: uuid.UUID,
    include_archived: bool = False,
    limit: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """칸반 카드 목록. 기본은 아카이브 제외 + 상한(장기 누적 대비).
    이슈는 단일 IN 쿼리로 일괄 조회(N+1 제거)."""
    await _get_owned_agent(agent_id, user, db)
    cap = min(limit or settings.projects_page_limit, 2000)

    stmt = select(Project).where(Project.agent_id == agent_id)
    if not include_archived:
        stmt = stmt.where(Project.archived_at.is_(None))
    stmt = stmt.order_by(Project.updated_at.desc()).limit(cap)
    projects = (await db.execute(stmt)).scalars().all()

    # 이슈 일괄 조회 후 project_id 로 그룹 → 카드당 쿼리(N+1) 제거.
    issues_by_pid: dict[uuid.UUID, list[Issue]] = defaultdict(list)
    if projects:
        pids = [p.id for p in projects]
        ires = await db.execute(select(Issue).where(Issue.project_id.in_(pids)))
        for i in ires.scalars().all():
            issues_by_pid[i.project_id].append(i)

    out: list[ProjectWithIssues] = []
    for p in projects:
        pw = ProjectWithIssues.model_validate(p)
        pw.issues = [IssueOut.model_validate(i) for i in issues_by_pid.get(p.id, [])]
        out.append(pw)
    return out


@router.patch("/{agent_id}/projects/{project_id}/status", response_model=ProjectOut)
async def update_project_status(
    agent_id: uuid.UUID, project_id: uuid.UUID, body: StatusPatch,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """칸반 드래그앤드롭. completed/cancelled 로 옮기면 하위 이슈를 resolved 처리(기존 규칙 계승)."""
    if body.status not in PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"status 는 {PROJECT_STATUSES} 중 하나여야 합니다")
    await _get_owned_agent(agent_id, user, db)
    res = await db.execute(select(Project).where(Project.id == project_id, Project.agent_id == agent_id))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    project.status = body.status
    if body.status in ("completed", "cancelled"):
        now = datetime.now(timezone.utc)
        ires = await db.execute(select(Issue).where(Issue.project_id == project.id, Issue.status != "resolved"))
        for issue in ires.scalars().all():
            issue.status = "resolved"
            issue.resolved_at = now
    await db.commit()
    await db.refresh(project)
    return ProjectOut.model_validate(project)
