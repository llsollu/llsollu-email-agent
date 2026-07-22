"""T1(project_tracker) 뷰용 데이터 API — 칸반."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.agents import _get_owned_agent
from app.auth.deps import get_current_user
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
async def list_projects(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_owned_agent(agent_id, user, db)
    res = await db.execute(select(Project).where(Project.agent_id == agent_id).order_by(Project.updated_at.desc()))
    projects = res.scalars().all()

    out: list[ProjectWithIssues] = []
    for p in projects:
        ires = await db.execute(select(Issue).where(Issue.project_id == p.id))
        issues = ires.scalars().all()
        pw = ProjectWithIssues.model_validate(p)
        pw.issues = [IssueOut.model_validate(i) for i in issues]
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
