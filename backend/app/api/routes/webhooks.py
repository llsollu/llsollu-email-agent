"""Microsoft Graph 메일 구독(webhook) 수신.

주의: Graph 알림은 외부(Microsoft) IP에서 오므로 IP 화이트리스트를 우회한다(security 미들웨어에서
/webhooks/graph 경로 예외). 대신 clientState 로 진위를 검증한다.
사내망에 외부 콜백이 불가한 환경에서는 이 엔드포인트 대신 폴링(ingestion) 을 사용한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Agent
from app.services.queue import enqueue_run

router = APIRouter()


@router.api_route("/graph", methods=["GET", "POST"])
async def graph_notifications(request: Request):
    # 구독 생성 시 검증 핸드셰이크
    token = request.query_params.get("validationToken")
    if token:
        return Response(content=token, media_type="text/plain")

    body = await request.json()
    for note in body.get("value", []):
        if note.get("clientState") != settings.graph_webhook_client_state:
            continue
        resource = note.get("resource", "")
        # resource 예: users/{mailbox}/mailFolders('Inbox')/messages/{id}
        mailbox = _extract_mailbox(resource)
        message_id = _extract_message_id(resource)
        if not mailbox:
            continue
        # 이 mailbox 를 구독하는 project_tracker 에이전트들에게 run 투입
        async with SessionLocal() as db:
            res = await db.execute(
                select(Agent).where(
                    Agent.template_key == "project_tracker",
                    Agent.status == "active",
                    Agent.deleted_at.is_(None),
                )
            )
            for agent in res.scalars().all():
                if (agent.config or {}).get("mailbox", "").lower() == mailbox.lower():
                    await enqueue_run(str(agent.id), "email", {"mailbox": mailbox, "message_id": message_id})

    return Response(status_code=202)


def _extract_mailbox(resource: str) -> str | None:
    parts = resource.split("/")
    if len(parts) >= 2 and parts[0].lower() == "users":
        return parts[1]
    return None


def _extract_message_id(resource: str) -> str | None:
    return resource.rstrip("/").split("/")[-1] if resource else None
