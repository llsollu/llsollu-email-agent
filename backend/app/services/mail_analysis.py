"""메일함 단위 공유 분석 파이프라인.

수신형 에이전트(이슈 관리·타임라인)가 공통으로 호출한다.
(mailbox, message_id) 기준으로 분석을 1회만 수행·캐시하며, 카테고리도 여기서 정해져
에이전트 간 공유된다. 분석은 인용된 thread 를 제거한 '현재 메일 내용'만 대상으로 한다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, MailRecord
from app.services.mailtext import strip_quoted

ANALYZER_VERSION = "2"
DEFAULT_CATEGORIES = ["제안", "계약", "개발", "납품", "유지보수", "문의", "기타"]

SYSTEM = """너는 B2B 소프트웨어 회사의 이메일 분석 어시스턴트다.
수신한 고객 이메일을 읽고 어느 고객사/프로젝트에 관한 것인지 분류하고 핵심을 한국어로 요약한다.
반드시 '지금 이 메일에서 새로 쓴 내용'만 분석하라. 인용되어 딸려온 이전 메일/원문(하단 인용부)은 무시한다.
분류(category)는 주어진 카테고리 중 하나로만 정한다."""

USER_TMPL = """다음 이메일(현재 메시지 본문)만 분석하라. 인용된 이전 내용은 이미 제거되어 있다.

제목: {subject}
발신: {from_address}
본문:
{body}

분류 카테고리 후보: {categories}

아래 JSON 스키마로만 답하라(설명 금지):
{{
  "client_name": "고객사명 또는 null",
  "project_title": "프로젝트/건명 또는 null",
  "category": "위 후보 중 하나 또는 null",
  "summary": "이 메일 한 줄 요약",
  "action_required": true/false,
  "issue": {{"type": "bug|request|delay|question|complaint|general", "summary": "이슈 요약", "severity": "low|medium|high|critical"}} 또는 null,
  "points": ["핵심 포인트 1", "핵심 포인트 2"]
}}"""


async def resolve_categories(db: AsyncSession, mailbox: str) -> list[str]:
    """메일함을 보는 활성 수신형 에이전트들의 categories 설정을 합집합으로 → 공유 taxonomy."""
    res = await db.execute(
        select(Agent).where(
            Agent.template_key == "project_tracker",
            Agent.status == "active",
            Agent.deleted_at.is_(None),
        )
    )
    cats: list[str] = []
    for a in res.scalars().all():
        if (a.config or {}).get("mailbox") != mailbox:
            continue
        raw = str((a.config or {}).get("categories") or "")
        for c in raw.split(","):
            c = c.strip()
            if c and c not in cats:
                cats.append(c)
    return cats or DEFAULT_CATEGORIES


def _extract(email: dict) -> dict:
    """Graph/webhook payload → 표준 필드."""
    frm = (email.get("from") or {}).get("emailAddress", {})
    return {
        "message_id": email.get("id") or email.get("message_id") or "",
        "subject": email.get("subject") or "",
        "from_address": frm.get("address") or email.get("from_address") or "",
        "from_name": frm.get("name") or "",
        "received_at": email.get("receivedDateTime"),
        "body": (email.get("body") or {}).get("content")
        or email.get("bodyText") or email.get("bodyPreview") or "",
    }


async def analyze_email(llm, email: dict, categories: list[str]) -> dict:
    """순수 분석(DB 미접근). 현재 메일 내용만 대상으로 LLM 호출."""
    f = _extract(email)
    body = strip_quoted(f["body"])[:8000]
    return await llm.complete_json(
        SYSTEM,
        USER_TMPL.format(
            subject=f["subject"], from_address=f["from_address"],
            body=body, categories=", ".join(categories),
        ),
    )


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def resolve_email(graph, trigger_payload: dict | None, trigger_source: str, mailbox: str | None) -> dict | None:
    """트리거 payload → 실제 이메일 dict. 수동 실행 시 최신 1건, webhook(id만) 시 Graph 조회."""
    email = {k: v for k, v in (trigger_payload or {}).items() if k != "dry_run"}
    if not email and trigger_source == "manual" and mailbox:
        msgs = await graph.list_messages(mailbox, top=1)
        if msgs:
            email = msgs[0]
    if email.get("message_id") and not email.get("subject"):
        mb = email.get("mailbox") or mailbox
        if mb:
            email = await graph.get_message(mb, email["message_id"])
    return email or None


async def get_or_analyze(db: AsyncSession, llm, mailbox: str, email: dict) -> MailRecord:
    """(mailbox, message_id) 캐시. 없으면 분석·저장 후 MailRecord 반환."""
    f = _extract(email)
    mid = f["message_id"]
    rec = None
    if mid:
        res = await db.execute(
            select(MailRecord).where(MailRecord.mailbox == mailbox, MailRecord.message_id == mid)
        )
        rec = res.scalar_one_or_none()
    if rec and rec.analyzed:
        return rec

    categories = await resolve_categories(db, mailbox)
    cls = await analyze_email(llm, email, categories)

    if rec is None:
        rec = MailRecord(mailbox=mailbox, message_id=mid or f"noid-{datetime.now(timezone.utc).timestamp()}")
        db.add(rec)
    rec.subject = f["subject"]
    rec.from_address = f["from_address"]
    rec.from_name = f["from_name"]
    rec.received_at = _parse_dt(f["received_at"])
    rec.body_text = strip_quoted(f["body"])
    rec.client_name = cls.get("client_name")
    rec.project_title = cls.get("project_title")
    rec.category = cls.get("category")
    rec.summary = cls.get("summary") or ""
    rec.action_required = bool(cls.get("action_required"))
    rec.issue = cls.get("issue")
    rec.points = cls.get("points") or []
    rec.analyzed = True
    rec.analyzer_version = ANALYZER_VERSION
    await db.flush()
    return rec
