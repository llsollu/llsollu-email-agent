"""T2: 메일 자동 발송 스케줄링 (범용).

사용자가 지정한 참조 파일(xlsx)의 각 행을, 사용자가 작성한 제목/본문 템플릿
({{컬럼명}} 치환)으로 만들어 수신자에게 발송한다.
- 발송기준일(date_column) 지정 시: 그 컬럼 값이 오늘과 매칭되는 행만 발송.
- 미지정 시: 확인 주기(cron)마다 모든 행 발송.
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
from app.templates.mail_scheduler.xlsx import parse_table


class MailSchedulerTemplate(BaseTemplate):
    key = "mail_scheduler"
    name = "메일 자동 발송 스케줄링"
    version = "0.2.0"
    description = "참조 파일의 데이터를 사용자가 만든 제목/본문 템플릿으로 정해진 주기에 자동 발송"
    trigger = TriggerSpec(kind="schedule", detail={"default_cron": "0 9 * * *"})
    view = ViewSpec(view_type="scheduler_panel",
                    data_endpoints=["/agents/{id}", "/agents/{id}/runs", "/agents/{id}/schedule"])

    def config_schema(self) -> list[ConfigField]:
        # 전용 2단계 마법사(프론트)에서 입력하지만, 설정 검증/폴백용으로 스키마도 유지.
        return [
            ConfigField("sharepoint_file_url", "참조 파일 URL", "url", required=True),
            ConfigField("mail_sender", "발신자 이메일", "email", required=True),
            ConfigField("recipient_email", "수신자 이메일", "string", required=True,
                        help="쉼표로 여러 명 지정 가능"),
            ConfigField("cc_email", "참조 이메일", "string", required=False,
                        help="쉼표로 여러 명 지정 가능(선택)"),
            ConfigField("date_column", "발송기준일(컬럼명)", "string", required=False,
                        help="비우면 확인 주기마다 전체 발송"),
            ConfigField("cron", "확인 주기(cron)", "cron", required=False, default="0 9 * * *"),
            ConfigField("subject_template", "메일 제목", "string", required=False),
            ConfigField("body_template", "메일 작성 내용", "text", required=False),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        for req in ("sharepoint_file_url", "mail_sender", "recipient_email"):
            if not ctx.config.get(req):
                raise ValueError(f"{req} 설정이 필요합니다")

    async def handle(self, ctx: RunContext) -> RunResult:
        cfg = ctx.config
        recipient = cfg["recipient_email"]
        cc = cfg.get("cc_email") or ""
        sender = cfg["mail_sender"]
        date_column = (cfg.get("date_column") or "").strip()
        subject_tmpl = cfg.get("subject_template") or ""
        body_tmpl = cfg.get("body_template") or ""

        today = datetime.now(ZoneInfo(settings.scheduler_tz)).date()

        data = await ctx.graph.download_shared_file(cfg["sharepoint_file_url"])
        columns, rows = parse_table(data)

        if date_column:
            targets = [r for r in rows if is_scheduled_today(r.get(date_column), today)]
        else:
            targets = rows
        ctx.log("parsed", total=len(rows), targets=len(targets), by_date=bool(date_column))

        sent = failed = 0
        for row in targets:
            subject = eb.render(subject_tmpl, row, today).strip() or "(제목 없음)"
            body = eb.render(body_tmpl, row, today)

            if ctx.dry_run:
                ctx.log("dry_run", to=recipient, cc=cc, subject=subject)
                continue

            try:
                await ctx.graph.send_mail(sender, recipient, subject, body, cc=cc)
                sent += 1
                ctx.db.add(SentRecord(agent_id=ctx.agent_id, target=recipient,
                                      subject=subject, status="sent"))
            except Exception as e:  # noqa: BLE001
                failed += 1
                ctx.db.add(SentRecord(agent_id=ctx.agent_id, target=recipient,
                                      subject=subject, status="failed", detail=str(e)))
                ctx.log("send_failed", to=recipient, error=str(e))

        await ctx.db.commit()
        return RunResult(ok=failed == 0, stats={
            "total": len(rows), "targets": len(targets),
            "sent": sent, "failed": failed, "dry_run": ctx.dry_run,
        })
