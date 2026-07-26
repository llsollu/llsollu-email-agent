"""T1: 메일 분류·요약 기반 이슈 관리 (칸반).

수신 메일을 공유 분석(mail_analysis)으로 분류·요약하고 고객사/프로젝트/이슈를 갱신한다.
분석은 메일함 단위로 공유·캐시되므로 같은 메일함의 타임라인 에이전트와 중복 분석하지 않는다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.framework.base import BaseTemplate, ConfigField, TriggerSpec, ViewSpec
from app.framework.context import RunContext, RunResult, SetupContext
from app.models import Issue, MailRecord, Project
from app.services.mail_analysis import (
    analyze_email,
    get_or_analyze,
    resolve_categories,
    resolve_email,
    resolve_issue_types,
)


class ProjectTrackerTemplate(BaseTemplate):
    key = "project_tracker"
    name = "메일 분석·요약 관리"
    version = "0.3.0"
    description = "수신 메일을 LLM으로 분석·요약해 이슈 보드(칸반)와 타임라인 두 뷰로 관리"
    trigger = TriggerSpec(kind="event", detail={"mailbox_field": "mailbox"})
    view = ViewSpec(
        view_type="kanban",
        views=[
            {"key": "board", "type": "kanban", "label": "이슈 보드"},
            {"key": "timeline", "type": "timeline", "label": "타임라인"},
        ],
        data_endpoints=["/agents/{id}/projects", "/agents/{id}/timeline"],
    )

    def config_schema(self) -> list[ConfigField]:
        # 대상 메일함은 항상 소유자 본인 메일로 고정(라우트에서 주입) → 설정 항목 없음.
        return [
            ConfigField("categories", "메일 분류 카테고리", "string", required=False,
                        help="쉼표로 구분. 분석·카테고리는 이 메일함에서 공유됩니다."),
            ConfigField("primary_axis", "기본 보기 설정", "select", required=False,
                        default="client", options=["client", "project"],
                        help="이슈 카드 제목·타임라인 그룹의 기본 기준: 고객사별/프로젝트별"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        if not ctx.config.get("mailbox"):
            raise ValueError("mailbox 설정이 필요합니다")

    # 수동 실행 시 한 번에 훑는 최근 메일 수(이미 분석된 건 캐시로 스킵).
    MANUAL_SCAN = 20

    async def handle(self, ctx: RunContext) -> RunResult:
        mailbox = ctx.config.get("mailbox")

        # 드라이런: 저장 없이 최신 1건 분석 미리보기.
        if ctx.dry_run:
            email = await resolve_email(ctx.graph, ctx.trigger_payload, ctx.trigger_source, mailbox)
            if not email:
                return RunResult(ok=True, message="처리할 메일 없음", stats={"processed": 0})
            cats = await resolve_categories(ctx.db, mailbox)
            itypes = await resolve_issue_types(ctx.db, mailbox)
            cls, _ = await analyze_email(ctx.llm, email, cats, itypes)
            ctx.log("dry_run", client=cls.get("client_name"), project=cls.get("project_title"),
                    category=cls.get("category"), summary=cls.get("summary"))
            return RunResult(ok=True, stats={
                "processed": 1, "dry_run": True,
                "client": cls.get("client_name"), "project": cls.get("project_title"),
                "category": cls.get("category"), "summary": cls.get("summary"),
            })

        emails = await self._collect_emails(ctx, mailbox)
        if not emails:
            return RunResult(ok=True, message="처리할 메일 없음", stats={"processed": 0, "analyzed": 0})

        # 이미 분석된 message_id 집합(→ 신규만 카운트, 캐시는 스킵).
        pre = await ctx.db.execute(
            select(MailRecord.message_id).where(
                MailRecord.mailbox == mailbox, MailRecord.analyzed.is_(True)
            )
        )
        existing = {mid for (mid,) in pre.all()}

        analyzed = 0
        last = None
        for email in emails:
            mid = email.get("id") or email.get("message_id") or ""
            was_new = bool(mid) and mid not in existing
            rec = await get_or_analyze(ctx.db, ctx.llm, mailbox, email,
                                       agent_id=ctx.agent_id, run_id=ctx.run_id)
            if was_new:
                analyzed += 1
            # 고객사만 잡혀도 카드 생성(프로젝트 미상이면 "(미지정)"으로 표기).
            if rec.client_name:
                await self._upsert_project(ctx, rec)
            last = rec

        await ctx.db.commit()
        ctx.log("scanned", scanned=len(emails), analyzed=analyzed)
        return RunResult(ok=True, stats={
            "processed": len(emails), "analyzed": analyzed,
            "client": last.client_name if last else None,
            "project": last.project_title if last else None,
            "category": last.category if last else None,
        })

    async def _collect_emails(self, ctx: RunContext, mailbox: str | None) -> list[dict]:
        """트리거에 특정 메일이 실려오면 그 1건, 수동 실행이면 최근 MANUAL_SCAN 건."""
        payload = {k: v for k, v in (ctx.trigger_payload or {}).items() if k != "dry_run"}
        if payload:
            email = await resolve_email(ctx.graph, ctx.trigger_payload, ctx.trigger_source, mailbox)
            return [email] if email else []
        if ctx.trigger_source == "manual" and mailbox:
            return await ctx.graph.list_messages(mailbox, top=self.MANUAL_SCAN)
        email = await resolve_email(ctx.graph, ctx.trigger_payload, ctx.trigger_source, mailbox)
        return [email] if email else []

    async def _upsert_project(self, ctx: RunContext, rec: MailRecord):
        """메일 1건 = 카드 1개. source_message_id 기준 멱등 업서트(같은 메일은 재실행해도 카드 1개)."""
        res = await ctx.db.execute(
            select(Project).where(
                Project.agent_id == ctx.agent_id,
                Project.source_message_id == rec.id,
            )
        )
        project = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if project is None:
            project = Project(
                agent_id=ctx.agent_id, client_name=rec.client_name, title=rec.project_title or "(미지정)",
                status="storyboard", category=rec.category,
                latest_update=rec.summary, keywords=rec.keywords or [],
                from_name=rec.from_name, from_address=rec.from_address,
                recipient_role=rec.recipient_role,
                last_activity_at=now, source_message_id=rec.id,
            )
            ctx.db.add(project)
            await ctx.db.flush()
        else:
            project.client_name = rec.client_name
            project.title = rec.project_title or "(미지정)"
            project.category = rec.category
            project.latest_update = rec.summary
            project.keywords = rec.keywords or []
            project.from_name = rec.from_name
            project.from_address = rec.from_address
            project.recipient_role = rec.recipient_role
            project.last_activity_at = now

        # 이 카드의 이슈는 해당 메일의 이슈 1건만 반영(재실행 시 교체 → 중복 방지).
        await ctx.db.execute(delete(Issue).where(Issue.project_id == project.id))
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
