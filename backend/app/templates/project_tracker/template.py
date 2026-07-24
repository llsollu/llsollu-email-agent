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
            ConfigField("categories", "메일 분류 카테고리", "string", required=False,
                        help="쉼표로 구분. 예: 제안,계약,개발,납품,유지보수,문의"),
            ConfigField("card_title_field", "요약 카드 타이틀", "select", required=False,
                        default="client", options=["client", "category", "title"],
                        help="카드에 표시할 제목: 고객사/분류/요약 제목"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        # mailbox 접근 가능 여부 가벼운 검증
        mailbox = ctx.config.get("mailbox")
        if not mailbox:
            raise ValueError("mailbox 설정이 필요합니다")
        # Graph 미구성 환경에서는 검증 생략(폴링/webhook은 ingestion 담당)

    async def handle(self, ctx: RunContext) -> RunResult:
        email = {k: v for k, v in (ctx.trigger_payload or {}).items() if k != "dry_run"}

        # 수동 실행/드라이런: 트리거 메일이 없으면 대상 메일함의 최신 메일 1건을 가져와 미리 분류.
        if not email and ctx.trigger_source == "manual":
            mailbox = ctx.config.get("mailbox")
            if mailbox:
                msgs = await ctx.graph.list_messages(mailbox, top=1)
                if msgs:
                    email = msgs[0]
                    ctx.log("manual_fetch", mailbox=mailbox)
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

        categories = _categories(ctx.config)
        cls = await ctx.llm.complete_json(SYSTEM, USER_TMPL.format(
            subject=subject, from_address=from_address, body=body[:8000],
            categories=", ".join(categories)))

        client_name = cls.get("client_name")
        project_title = cls.get("project_title")
        summary = cls.get("summary") or ""
        category = cls.get("category")
        ctx.log("classified", client=client_name, project=project_title, category=category)

        # 드라이런: 분류 결과만 확인하고 DB에는 반영하지 않음.
        if ctx.dry_run:
            ctx.log("dry_run", subject=subject, client=client_name, project=project_title,
                    category=category, summary=summary)
            return RunResult(ok=True, stats={
                "processed": 1, "dry_run": True,
                "client": client_name, "project": project_title, "category": category, "summary": summary,
            })

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
                status="active", category=cls.get("category"),
                latest_update=cls.get("summary"), last_activity_at=now,
            )
            ctx.db.add(project)
            await ctx.db.flush()
        else:
            if cls.get("category"):
                project.category = cls["category"]
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


DEFAULT_CATEGORIES = ["제안", "계약", "개발", "납품", "유지보수", "문의", "기타"]


def _categories(config: dict) -> list[str]:
    raw = (config.get("categories") or "").strip()
    cats = [c.strip() for c in raw.split(",") if c.strip()]
    return cats or DEFAULT_CATEGORIES


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
