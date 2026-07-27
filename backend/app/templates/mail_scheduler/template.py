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
            ConfigField("sharepoint_file_url", "참조 파일 URL", "url", required=False,
                        help="비우면 데이터 없이 템플릿만으로 발송"),
            ConfigField("mail_sender", "발신자 이메일", "email", required=True),
            ConfigField("recipient_email", "수신자 이메일", "string", required=True,
                        help="쉼표로 여러 명 지정 가능"),
            ConfigField("cc_email", "참조 이메일", "string", required=False,
                        help="쉼표로 여러 명 지정 가능(선택)"),
            ConfigField("alert_email", "오류 알림 이메일", "email", required=False,
                        help="발송 실패 시 알림을 받을 주소(비우면 발신자 본인)"),
            ConfigField("date_column", "발송기준일(컬럼명)", "string", required=False,
                        help="비우면 확인 주기마다 전체 발송"),
            ConfigField("cron", "확인 주기(cron)", "cron", required=False, default="0 9 * * *"),
            ConfigField("subject_template", "메일 제목", "string", required=False),
            ConfigField("body_template", "메일 작성 내용", "text", required=False),
        ]

    async def on_setup(self, ctx: SetupContext) -> None:
        # 참조 파일 URL 은 선택(없으면 데이터 없이 발송). 발신·수신만 필수.
        for req in ("mail_sender", "recipient_email"):
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

        file_url = (cfg.get("sharepoint_file_url") or "").strip()
        if file_url:
            # (1) 참조 파일 자체를 가져오지 못함(파일 삭제/이동/권한/네트워크 등) → run-level 오류 알림.
            try:
                data = await ctx.graph.download_shared_file(file_url)
                columns, rows = parse_table(data)
            except Exception as e:  # noqa: BLE001
                ctx.log("collect_failed", url=file_url, error=str(e))
                if not ctx.dry_run:
                    await self._send_run_alert(
                        ctx, sender, cfg.get("alert_email"), recipient, cc, subject_tmpl, body_tmpl, today, {},
                        reason=f"참조 파일을 가져오지 못했습니다: {file_url}", detail=str(e),
                    )
                return RunResult(ok=False, message="참조 파일 수집 실패",
                                 stats={"error": str(e), "sent": 0, "failed": 0, "dry_run": ctx.dry_run})

            # (2) 템플릿이 참조하는 데이터 필드(컬럼)가 파일에서 사라짐 → 발송 중단 + 알림.
            used = set(eb.used_columns(subject_tmpl)) | set(eb.used_columns(body_tmpl))
            if date_column:
                used.add(date_column)
            missing = sorted(c for c in used if c not in columns)
            if missing:
                ctx.log("missing_columns", missing=missing)
                if not ctx.dry_run:
                    await self._send_run_alert(
                        ctx, sender, cfg.get("alert_email"), recipient, cc, subject_tmpl, body_tmpl, today,
                        rows[0] if rows else {},
                        reason="참조 파일에 필요한 데이터 필드가 없습니다: " + ", ".join(missing),
                        detail=f"파일의 현재 컬럼: {', '.join(columns) or '(없음)'}",
                    )
                return RunResult(ok=False, message="필요한 데이터 필드 없음",
                                 stats={"error": "missing_columns", "missing_columns": missing,
                                        "sent": 0, "failed": 0, "dry_run": ctx.dry_run})
        else:
            # 참조 파일 없음: 데이터가 없어도 템플릿만으로 1건 발송(발송기준일은 무시).
            columns, rows = [], [{}]
            date_column = ""

        if date_column:
            targets = [r for r in rows if is_scheduled_today(r.get(date_column), today)]
        else:
            targets = rows
        ctx.log("parsed", total=len(rows), targets=len(targets), by_date=bool(date_column))

        sent = failed = 0
        failures: list[dict] = []
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
                # 오류 알림용: 원래 보내려던 메일 원문(미수집 데이터는 <데이터 미수집> 표시).
                failures.append({
                    "error": str(e), "to": recipient, "cc": cc,
                    "subject": eb.render(subject_tmpl, row, today, mark_missing=True).strip() or "(제목 없음)",
                    "body": eb.render(body_tmpl, row, today, mark_missing=True),
                })

        await ctx.db.commit()

        # 발송 실패가 있으면 오류 알림 메일 발송(기본 수신: 발신자 본인).
        if failures and not ctx.dry_run:
            await self._send_alert(ctx, sender, cfg.get("alert_email"), failures)

        return RunResult(ok=failed == 0, stats={
            "total": len(rows), "targets": len(targets),
            "sent": sent, "failed": failed, "dry_run": ctx.dry_run,
        })

    @staticmethod
    def _alert_to(alert_email, sender: str) -> str:
        return (alert_email or "").strip() or sender

    async def _deliver_alert(self, ctx: RunContext, sender: str, to: str, subject: str, body: str) -> None:
        """알림 메일 전송(전송 실패해도 실행이 죽지 않도록 로깅만)."""
        if not to:
            return
        try:
            await ctx.graph.send_mail(sender, to, subject, body)
            ctx.log("alert_sent", to=to)
        except Exception as e:  # noqa: BLE001
            ctx.log("alert_failed", to=to, error=str(e))

    async def _send_alert(self, ctx: RunContext, sender: str, alert_email, failures: list[dict]) -> None:
        """개별 발송 실패 요약(오류 메시지 + 보내려던 메일 원문)."""
        parts = [f"메일 자동 발송 중 {len(failures)}건이 실패했습니다.", ""]
        for i, f in enumerate(failures, 1):
            cc_line = f" / 참조: {f['cc']}" if f.get("cc") else ""
            parts += [
                f"[{i}] 수신자: {f['to']}{cc_line}",
                f"오류: {f['error']}",
                "── 보내려던 메일 ──",
                f"제목: {f['subject']}",
                "본문:",
                f["body"],
                "",
                "─" * 20,
                "",
            ]
        await self._deliver_alert(ctx, sender, self._alert_to(alert_email, sender),
                                  "[자동 발송 오류] 발송 실패 알림", "\n".join(parts))

    async def _send_run_alert(
        self, ctx: RunContext, sender: str, alert_email, recipient: str, cc: str,
        subject_tmpl: str, body_tmpl: str, today, preview_row: dict, *, reason: str, detail: str,
    ) -> None:
        """run-level 오류(파일 수집 실패·데이터 필드 소실 등) 알림.
        보내려던 메일 원문을 함께 싣고, 수집 안 된 데이터는 '<데이터 미수집>'으로 표시."""
        subj = eb.render(subject_tmpl, preview_row, today, mark_missing=True).strip() or "(제목 없음)"
        bod = eb.render(body_tmpl, preview_row, today, mark_missing=True)
        cc_line = f" / 참조: {cc}" if cc else ""
        parts = [
            "메일 자동 발송을 실행하지 못했습니다.",
            "",
            f"사유: {reason}",
            f"상세: {detail}",
            "",
            "── 보내려던 메일(미리보기) ──",
            f"수신자: {recipient}{cc_line}",
            f"제목: {subj}",
            "본문:",
            bod,
        ]
        await self._deliver_alert(ctx, sender, self._alert_to(alert_email, sender),
                                  "[자동 발송 오류] 실행 실패 알림", "\n".join(parts))
