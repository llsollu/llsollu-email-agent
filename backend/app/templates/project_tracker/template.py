"""T1: 메일 분류·요약 기반 이슈 관리 (칸반).

수신 메일을 공유 분석(mail_analysis)으로 분류·요약하고 고객사/프로젝트/이슈를 갱신한다.
분석은 메일함 단위로 공유·캐시되므로 같은 메일함의 타임라인 에이전트와 중복 분석하지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.framework.base import BaseTemplate, ConfigField, TriggerSpec, ViewSpec
from app.framework.context import RunContext, RunResult, SetupContext
from app.models import Issue, MailRecord, Project
from app.services.mail_analysis import analyze_email, get_or_analyze, resolve_categories, resolve_email


class ProjectTrackerTemplate(BaseTemplate):
    key = "project_tracker"
    name = "메일 분류·요약 기반 이슈 관리"
    version = "0.2.0"
    description = "수신 메일을 LLM으로 분류·요약해 고객사/프로젝트/이슈를 자동 갱신하고 칸반으로 시각화"
    trigger = TriggerSpec(kind="event", detail={"mailbox_field": "mailbox"})
    view = ViewSpec(view_type="kanban", data_endpoints=["/agents/{id}/projects"])

    def config_schema(self) -> list[ConfigField]:
        return [
            ConfigField("mailbox", "대상 메일함", "email", required=True,
                        help="분류할 메일을 수신하는 회사 메일 주소"),
            ConfigField("categories", "메일 분류 카테고리", "string", required=False,
                        help="쉼표로 구분. 같은 메일함의 에이전트들과 공유됩니다."),
            ConfigField("card_title_field", "요약 카드 타이틀", "select", required=False,
                        default="client", options=["client", "category", "title"],
                        help="카드에 표시할 제목: 고객사/분류/요약 제목"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        if not ctx.config.get("mailbox"):
            raise ValueError("mailbox 설정이 필요합니다")

    async def handle(self, ctx: RunContext) -> RunResult:
        mailbox = ctx.config.get("mailbox")
        email = await resolve_email(ctx.graph, ctx.trigger_payload, ctx.trigger_source, mailbox)
        if not email:
            return RunResult(ok=True, message="처리할 메일 없음", stats={"processed": 0})

        # 드라이런: 저장 없이 분석 미리보기.
        if ctx.dry_run:
            cats = await resolve_categories(ctx.db, mailbox)
            cls = await analyze_email(ctx.llm, email, cats)
            ctx.log("dry_run", client=cls.get("client_name"), project=cls.get("project_title"),
                    category=cls.get("category"), summary=cls.get("summary"))
            return RunResult(ok=True, stats={
                "processed": 1, "dry_run": True,
                "client": cls.get("client_name"), "project": cls.get("project_title"),
                "category": cls.get("category"), "summary": cls.get("summary"),
            })

        rec = await get_or_analyze(ctx.db, ctx.llm, mailbox, email)
        ctx.log("classified", client=rec.client_name, project=rec.project_title, category=rec.category)

        processed_project = None
        if rec.client_name and rec.project_title:
            processed_project = await self._upsert_project(ctx, rec)

        await ctx.db.commit()
        return RunResult(ok=True, stats={
            "processed": 1, "client": rec.client_name, "project": rec.project_title,
            "category": rec.category,
            "project_id": str(processed_project) if processed_project else None,
        })

    async def _upsert_project(self, ctx: RunContext, rec: MailRecord):
        res = await ctx.db.execute(
            select(Project).where(
                Project.agent_id == ctx.agent_id,
                Project.client_name == rec.client_name,
                Project.title == rec.project_title,
            )
        )
        project = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if project is None:
            project = Project(
                agent_id=ctx.agent_id, client_name=rec.client_name, title=rec.project_title,
                status="active", category=rec.category,
                latest_update=rec.summary, last_activity_at=now, source_message_id=rec.id,
            )
            ctx.db.add(project)
            await ctx.db.flush()
        else:
            if rec.category:
                project.category = rec.category
            project.latest_update = rec.summary
            project.last_activity_at = now
            project.source_message_id = rec.id

        issue = rec.issue
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
