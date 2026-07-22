"""T2: 메일 자동 발송 스케줄링. 기존 mailing 프로젝트를 프레임워크로 이식.

트리거는 schedule — scheduler 디스패처가 cron 도래 시 run 을 투입.
handle()은 참조 xlsx를 Graph로 내려받아 오늘 발행 대상 행을 선별, 본문을 만들어 발송하거나
필수 데이터 누락 시 관리자에게 알림 발송.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.framework.base import BaseTemplate, ConfigField, TriggerSpec, ViewSpec
from app.framework.context import RunContext, RunResult, SetupContext
from app.models import SentRecord
from app.templates.mail_scheduler import email_builder as eb
from app.templates.mail_scheduler.schedule_matcher import is_scheduled_today
from app.templates.mail_scheduler.xlsx import parse_invoice_rows


class MailSchedulerTemplate(BaseTemplate):
    key = "mail_scheduler"
    name = "메일 자동 발송 스케줄링"
    version = "0.1.0"
    description = "참조 파일과 규칙 기반으로 정해진 시각에 메일을 자동 발송하고 로그/온오프로 관리"
    trigger = TriggerSpec(kind="schedule", detail={"default_cron": "0 9 * * *"})
    view = ViewSpec(view_type="scheduler_panel",
                    data_endpoints=["/agents/{id}", "/agents/{id}/runs", "/agents/{id}/schedule"])

    def config_schema(self) -> list[ConfigField]:
        return [
            ConfigField("sharepoint_file_url", "참조 파일 URL", "url", required=True,
                        help="발행 일정표 xlsx 의 SharePoint 공유 링크"),
            ConfigField("mail_sender", "발신 계정", "email", required=True,
                        help="Graph sendMail 로 보낼 발신 메일박스"),
            ConfigField("recipient_email", "수신자 이메일", "email", required=True),
            ConfigField("recipient_name", "수신자 표시명", "string", required=False, default="담당자님"),
            ConfigField("alert_email", "누락 알림 수신 이메일", "email", required=False,
                        help="필수 데이터 누락 시 알림을 받을 주소"),
            ConfigField("cron", "실행 스케줄(cron)", "cron", required=False, default="0 9 * * *",
                        help="매일 09시 = '0 9 * * *'"),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        for req in ("sharepoint_file_url", "mail_sender", "recipient_email"):
            if not ctx.config.get(req):
                raise ValueError(f"{req} 설정이 필요합니다")

    async def handle(self, ctx: RunContext) -> RunResult:
        cfg = ctx.config
        recipient_name = cfg.get("recipient_name") or "담당자님"
        alert_email = cfg.get("alert_email") or cfg["recipient_email"]

        today = datetime.now(ZoneInfo(settings.scheduler_tz)).date()

        data = await ctx.graph.download_shared_file(cfg["sharepoint_file_url"])
        rows = parse_invoice_rows(data, today.month)
        targets = [r for r in rows if is_scheduled_today(r.schedule_pattern, today)]
        ctx.log("parsed", total=len(rows), targets=len(targets))

        sent = skipped = failed = 0
        for row in targets:
            missing = eb.missing_fields(row)
            has_missing = bool(missing)
            to = alert_email if has_missing else cfg["recipient_email"]
            subject = eb.build_subject(row, today, has_missing)
            body = eb.build_body(row, today, recipient_name)
            if has_missing:
                body = f"{eb.build_missing_notice(recipient_name)}\n\n{body}"

            if ctx.dry_run:
                ctx.log("dry_run", to=to, subject=subject, missing=missing)
                skipped += 1
                continue

            try:
                await ctx.graph.send_mail(cfg["mail_sender"], to, subject, body)
                status = "skipped" if has_missing else "sent"
                if has_missing:
                    skipped += 1
                else:
                    sent += 1
                ctx.db.add(SentRecord(
                    agent_id=ctx.agent_id, target=to, subject=subject, status=status,
                    detail=("누락: " + ", ".join(missing)) if has_missing else None,
                ))
            except Exception as e:  # noqa: BLE001
                failed += 1
                ctx.db.add(SentRecord(
                    agent_id=ctx.agent_id, target=to, subject=subject, status="failed", detail=str(e)))
                ctx.log("send_failed", to=to, error=str(e))

        await ctx.db.commit()
        return RunResult(ok=failed == 0, stats={
            "total": len(rows), "targets": len(targets),
            "sent": sent, "skipped": skipped, "failed": failed,
        })
