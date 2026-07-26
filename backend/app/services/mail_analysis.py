"""메일함 단위 공유 분석 파이프라인.

수신형 에이전트(이슈 관리·타임라인)가 공통으로 호출한다.
(mailbox, message_id) 기준으로 분석을 1회만 수행·캐시하며, 카테고리도 여기서 정해져
에이전트 간 공유된다. 분석은 인용된 thread 를 제거한 '현재 메일 내용'만 대상으로 한다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, LLMJob, MailRecord
from app.services.mailtext import strip_quoted

ANALYZER_VERSION = "3"
# 사용자 지정 자동 태그가 없을 때의 기본 태그(항상 후보에 포함).
UNCLASSIFIED = "미지정"
# 이슈 유형 기본값 = 개발 분야(설정 없을 때). 프론트 issueTypes.ts 와 동일하게 유지.
DEFAULT_ISSUE_TYPES = [
    {"key": "bug", "label": "버그"},
    {"key": "request", "label": "요청"},
    {"key": "question", "label": "문의"},
    {"key": "general", "label": "기타"},
]

SYSTEM = """너는 llsollu(엘솔루)라고 하는 음성인식 솔루션 회사의 이메일 분석 어시스턴트다.
수신한 고객 이메일을 읽고 어느 고객사/프로젝트에 관한 것인지 분류하고 핵심을 한국어로 요약한다.
반드시 '지금 이 메일에서 새로 쓴 내용'만 분석하라. 인용되어 딸려온 이전 메일/원문(하단 인용부)은 무시한다.
고객사·프로젝트를 판별할 때는 발신자뿐 아니라 수신자·참조자의 이메일 도메인/이름도 함께 참고해
누가 우리(llsollu)이고 누가 상대 고객사인지 명확히 구분한다(llsollu.com 도메인은 우리 회사다).
분류(category)는 주어진 카테고리 중 하나로만 정한다.
검색 편의를 위해 핵심 키워드는 물론 '유사 키워드'(동의어·약어·풀네임·영문/한글 표기)까지 함께 뽑는다.
예: 본문에 "음성인식"이 있으면 keywords 에 "음성인식"뿐 아니라 "STT", "Speech-to-Text" 도 넣어
'STT'로 검색해도 이 메일이 걸리도록 한다."""

USER_TMPL = """다음 이메일(현재 메시지 본문)만 분석하라. 인용된 이전 내용은 이미 제거되어 있다.

제목: {subject}
발신: {from_address}
수신: {to_addresses}
참조: {cc_addresses}
본문:
{body}

분류 카테고리 후보: {categories}
이슈 유형 후보(issue.type 은 아래 key 중 하나만 사용): {issue_type_legend}

아래 JSON 스키마로만 답하라(설명 금지):
{{
  "client_name": "고객사명 또는 null",
  "project_title": "프로젝트/건명 또는 null",
  "category": "위 후보 중 하나 또는 null",
  "summary": "이 메일 한 줄 요약",
  "action_required": true/false,
  "issue": {{"type": "{issue_type_keys} 중 하나", "summary": "이슈 요약", "severity": "low|medium|high|critical"}} 또는 null,
  "points": ["핵심 포인트 1", "핵심 포인트 2"],
  "keywords": ["핵심 키워드와 유사 키워드(동의어·약어·풀네임 포함). 예: 음성인식, STT, Speech-to-Text"]
}}"""


async def resolve_categories(db: AsyncSession, mailbox: str) -> list[str]:
    """사용자 지정 자동 태그(합집합) + '미지정'. 아무것도 없으면 ['미지정']만."""
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
    if UNCLASSIFIED not in cats:
        cats.append(UNCLASSIFIED)
    return cats


async def resolve_issue_types(db: AsyncSession, mailbox: str) -> list[dict]:
    """메일함을 보는 활성 project_tracker 에이전트들의 issue_types 설정을 합집합(key 기준 dedup)으로."""
    res = await db.execute(
        select(Agent).where(
            Agent.template_key == "project_tracker",
            Agent.status == "active",
            Agent.deleted_at.is_(None),
        )
    )
    out: list[dict] = []
    seen: set[str] = set()
    for a in res.scalars().all():
        if (a.config or {}).get("mailbox") != mailbox:
            continue
        for t in (a.config or {}).get("issue_types") or []:
            key = str((t or {}).get("key") or "").strip()
            label = str((t or {}).get("label") or "").strip() or key
            if key and key not in seen:
                seen.add(key)
                out.append({"key": key, "label": label})
    return out or DEFAULT_ISSUE_TYPES


def _issue_type_prompt(issue_types: list[dict]) -> tuple[str, str]:
    """(keys 파이프 목록, key(label) 범례) 반환. 프롬프트 주입용."""
    types = issue_types or DEFAULT_ISSUE_TYPES
    keys = "|".join(str(t.get("key")) for t in types if t.get("key"))
    legend = ", ".join(f"{t.get('key')}({t.get('label')})" for t in types if t.get("key"))
    return keys, legend


def _recipients(email: dict, graph_key: str, flat_key: str) -> str:
    """Graph(toRecipients/ccRecipients) 또는 평문(to_addresses/cc_addresses) → "이름 <주소>" 목록."""
    people = email.get(graph_key)
    if isinstance(people, list) and people:
        parts = []
        for p in people:
            ea = (p or {}).get("emailAddress", {}) if isinstance(p, dict) else {}
            addr = ea.get("address") or ""
            name = ea.get("name") or ""
            if addr or name:
                parts.append(f"{name} <{addr}>".strip())
        return ", ".join(parts)
    flat = email.get(flat_key)
    if isinstance(flat, list):
        return ", ".join(str(x) for x in flat if x)
    return str(flat or "")


def _addresses(email: dict, graph_key: str, flat_key: str) -> set[str]:
    """수신/참조 이메일 주소 집합(소문자). role 판별용."""
    out: set[str] = set()
    people = email.get(graph_key)
    if isinstance(people, list):
        for p in people:
            ea = (p or {}).get("emailAddress", {}) if isinstance(p, dict) else {}
            addr = (ea.get("address") or "").strip().lower()
            if addr:
                out.add(addr)
    flat = email.get(flat_key)
    if isinstance(flat, list):
        for x in flat:
            addr = str(x or "").strip().lower()
            if addr:
                out.add(addr)
    elif isinstance(flat, str) and flat:
        for x in flat.split(","):
            addr = x.strip().lower()
            if addr:
                out.add(addr)
    return out


def _recipient_role(email: dict, mailbox: str | None) -> str:
    """내(=메일함) 주소가 수신자면 'to'(직접수신), 참조면 'cc'(참조), 아니면 'other'."""
    me = (mailbox or "").strip().lower()
    if not me:
        return "other"
    if me in _addresses(email, "toRecipients", "to_addresses"):
        return "to"
    if me in _addresses(email, "ccRecipients", "cc_addresses"):
        return "cc"
    return "other"


def _extract(email: dict) -> dict:
    """Graph/webhook payload → 표준 필드."""
    frm = (email.get("from") or {}).get("emailAddress", {})
    return {
        "message_id": email.get("id") or email.get("message_id") or "",
        "subject": email.get("subject") or "",
        "from_address": frm.get("address") or email.get("from_address") or "",
        "from_name": frm.get("name") or "",
        "to_addresses": _recipients(email, "toRecipients", "to_addresses"),
        "cc_addresses": _recipients(email, "ccRecipients", "cc_addresses"),
        "received_at": email.get("receivedDateTime"),
        "body": (email.get("body") or {}).get("content")
        or email.get("bodyText") or email.get("bodyPreview") or "",
    }


async def analyze_email(llm, email: dict, categories: list[str], issue_types: list[dict] | None = None):
    """순수 분석(DB 미접근). (분석결과 dict, LLMResult 사용량) 반환."""
    f = _extract(email)
    body = strip_quoted(f["body"])[:8000]
    keys, legend = _issue_type_prompt(issue_types or DEFAULT_ISSUE_TYPES)
    return await llm.complete_json(
        SYSTEM,
        USER_TMPL.format(
            subject=f["subject"], from_address=f["from_address"],
            to_addresses=f["to_addresses"] or "(없음)",
            cc_addresses=f["cc_addresses"] or "(없음)",
            body=body, categories=", ".join(categories),
            issue_type_keys=keys, issue_type_legend=legend,
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


async def get_or_analyze(
    db: AsyncSession, llm, mailbox: str, email: dict,
    agent_id=None, run_id=None,
) -> MailRecord:
    """(mailbox, message_id) 캐시. 없으면 분석·저장 후 MailRecord 반환.
    실제 LLM 호출이 일어난 경우에만 LLMJob(토큰/사용량)을 적재한다."""
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
    issue_types = await resolve_issue_types(db, mailbox)
    cls, usage = await analyze_email(llm, email, categories, issue_types)

    if agent_id is not None:
        db.add(LLMJob(
            agent_id=agent_id, run_id=run_id, model=usage.model,
            tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, status="ok",
        ))

    if rec is None:
        rec = MailRecord(mailbox=mailbox, message_id=mid or f"noid-{datetime.now(timezone.utc).timestamp()}")
        db.add(rec)
    rec.subject = f["subject"]
    rec.from_address = f["from_address"]
    rec.from_name = f["from_name"]
    rec.to_recipients = f["to_addresses"]
    rec.cc_recipients = f["cc_addresses"]
    rec.recipient_role = _recipient_role(email, mailbox)
    rec.received_at = _parse_dt(f["received_at"])
    rec.body_text = strip_quoted(f["body"])
    rec.client_name = cls.get("client_name")
    rec.project_title = cls.get("project_title")
    rec.category = cls.get("category")
    rec.summary = cls.get("summary") or ""
    rec.action_required = bool(cls.get("action_required"))
    rec.issue = cls.get("issue")
    rec.points = cls.get("points") or []
    rec.keywords = cls.get("keywords") or []
    rec.analyzed = True
    rec.analyzer_version = ANALYZER_VERSION
    await db.flush()
    return rec
