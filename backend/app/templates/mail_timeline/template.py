"""T3: 메일 타임라인.

수신 메일을 고객사/프로젝트별로 시간순 히스토리로 보여준다. 분석은 이슈 관리 에이전트와
동일한 공유 분석(mail_analysis)을 재사용하므로 같은 메일함이면 중복 분석하지 않는다.
별도 프로젝션 테이블 없이 mail_records 를 조회해 타임라인을 렌더한다.
"""

from __future__ import annotations

from app.framework.base import BaseTemplate, ConfigField, TriggerSpec, ViewSpec
from app.framework.context import RunContext, RunResult, SetupContext
from app.services.mail_analysis import analyze_email, get_or_analyze, resolve_categories, resolve_email


class MailTimelineTemplate(BaseTemplate):
    key = "mail_timeline"
    name = "메일 타임라인"
    version = "0.1.0"
    description = "수신 메일을 고객사·프로젝트별 시간순 히스토리로 열람 (분석은 이슈 관리와 공유)"
    trigger = TriggerSpec(kind="event", detail={"mailbox_field": "mailbox"})
    view = ViewSpec(view_type="timeline", data_endpoints=["/agents/{id}/timeline"])

    def config_schema(self) -> list[ConfigField]:
        return [
            ConfigField("mailbox", "대상 메일함", "email", required=True,
                        help="타임라인으로 볼 메일을 수신하는 회사 메일 주소"),
            ConfigField("categories", "메일 분류 카테고리", "string", required=False,
                        help="쉼표로 구분. 같은 메일함의 에이전트들과 공유됩니다."),
            ConfigField("default_group", "기본 그룹", "select", required=False,
                        default="client", options=["client", "project"],
                        help="타임라인 기본 그룹: 고객사/프로젝트"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        if not ctx.config.get("mailbox"):
            raise ValueError("mailbox 설정이 필요합니다")

    async def handle(self, ctx: RunContext) -> RunResult:
        mailbox = ctx.config.get("mailbox")
        email = await resolve_email(ctx.graph, ctx.trigger_payload, ctx.trigger_source, mailbox)
        if not email:
            return RunResult(ok=True, message="처리할 메일 없음", stats={"processed": 0})

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

        # 공유 분석만 보장하면 타임라인은 조회로 렌더됨(별도 프로젝션 없음).
        rec = await get_or_analyze(ctx.db, ctx.llm, mailbox, email)
        await ctx.db.commit()
        ctx.log("timelined", client=rec.client_name, project=rec.project_title, category=rec.category)
        return RunResult(ok=True, stats={
            "processed": 1, "client": rec.client_name, "project": rec.project_title, "category": rec.category,
        })
