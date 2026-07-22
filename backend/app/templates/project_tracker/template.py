"""T1: 메일 분류·요약 → 고객사 프로젝트 관리 (칸반).

기존 email-agent 의 emailProcessor 로직을 프레임워크로 이식.
트리거는 event(메일 수신) — ingestion 이 Graph 로부터 받은 메일을 payload 로 전달.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.framework.base import BaseTemplate, ConfigField, TriggerSpec, ViewSpec
from app.framework.context import RunContext, RunResult, SetupContext
from app.models import EmailLog, Issue, Project
from app.templates.project_tracker.prompts import SYSTEM, USER_TMPL


class ProjectTrackerTemplate(BaseTemplate):
    key = "project_tracker"
    name = "메일 분류·요약 → 고객사 프로젝트 관리"
    version = "0.1.0"
    description = "수신 메일을 LLM으로 분류·요약해 고객사/프로젝트/이슈를 자동 갱신하고 칸반으로 시각화"
    trigger = TriggerSpec(kind="event", detail={"mailbox_field": "mailbox"})
    view = ViewSpec(view_type="kanban", data_endpoints=["/agents/{id}/projects"])

    def config_schema(self) -> list[ConfigField]:
        return [
            ConfigField("mailbox", "대상 메일함", "email", required=True,
                        help="분류할 메일을 수신하는 회사 메일 주소"),
            ConfigField("client_hints", "고객사 힌트", "text", required=False,
                        help="분류를 도울 고객사명 목록(선택, 쉼표 구분)"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        # mailbox 접근 가능 여부 가벼운 검증
        mailbox = ctx.config.get("mailbox")
        if not mailbox:
            raise ValueError("mailbox 설정이 필요합니다")
        # Graph 미구성 환경에서는 검증 생략(폴링/webhook은 ingestion 담당)

    async def handle(self, ctx: RunContext) -> RunResult:
        email = ctx.trigger_payload
        if not email:
            return RunResult(ok=True, message="처리할 메일 없음", stats={"processed": 0})

        # webhook 경로: mailbox+message_id 만 온 경우 Graph 로 본문을 조회
        if email.get("message_id") and not email.get("subject"):
            mailbox = email.get("mailbox") or ctx.config.get("mailbox")
            if mailbox:
                email = await ctx.graph.get_message(mailbox, email["message_id"])

        subject = email.get("subject") or ""
        from_address = (email.get("from") or {}).get("emailAddress", {}).get("address") \
            or email.get("from_address") or ""
        body = (email.get("body") or {}).get("content") or email.get("bodyText") or email.get("bodyPreview") or ""

        cls = await ctx.llm.complete_json(SYSTEM, USER_TMPL.format(
            subject=subject, from_address=from_address, body=body[:8000]))

        client_name = cls.get("client_name")
        project_title = cls.get("project_title")
        summary = cls.get("summary") or ""
        ctx.log("classified", client=client_name, project=project_title)

        # 메일 로그 적재
        ctx.db.add(EmailLog(
            agent_id=ctx.agent_id,
            message_id=email.get("id"),
            subject=subject,
            from_address=from_address,
            client_name=client_name,
            summary=summary,
            action_required=bool(cls.get("action_required")),
            received_at=_parse_dt(email.get("receivedDateTime")),
        ))

        processed_project = None
        if client_name and project_title:
            processed_project = await self._upsert_project(ctx, client_name, project_title, cls)

        await ctx.db.commit()
        return RunResult(ok=True, stats={
            "processed": 1,
            "client": client_name,
            "project": project_title,
            "project_id": str(processed_project) if processed_project else None,
        })

    async def _upsert_project(self, ctx: RunContext, client_name: str, title: str, cls: dict):
        res = await ctx.db.execute(
            select(Project).where(
                Project.agent_id == ctx.agent_id,
                Project.client_name == client_name,
                Project.title == title,
            )
        )
        project = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if project is None:
            project = Project(
                agent_id=ctx.agent_id, client_name=client_name, title=title,
                status="active", phase=cls.get("phase"),
                latest_update=cls.get("summary"), last_activity_at=now,
            )
            ctx.db.add(project)
            await ctx.db.flush()
        else:
            if cls.get("phase"):
                project.phase = cls["phase"]
            project.latest_update = cls.get("summary")
            project.last_activity_at = now

        issue = cls.get("issue")
        if issue:
            ctx.db.add(Issue(
                project_id=project.id,
                type=issue.get("type", "general"),
                summary=issue.get("summary", ""),
                severity=issue.get("severity", "medium"),
                status="open",
                detected_at=now,
            ))
            ctx.log("issue_created", type=issue.get("type"))
        return project.id


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
