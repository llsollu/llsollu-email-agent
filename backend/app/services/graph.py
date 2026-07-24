"""Microsoft Graph 클라이언트: 앱 전용(client credentials) 토큰, 메일 읽기/발송,
공유 파일 다운로드, 메일 구독(webhook) 관리."""

import base64
import time

import httpx

from app.config import settings

_GRAPH = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._exp: float = 0.0

    async def _get_token(self) -> str:
        if self._token and self._exp > time.time() + 60:
            return self._token
        url = f"https://login.microsoftonline.com/{settings.graph_tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": settings.graph_client_id,
            "client_secret": settings.graph_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, data=data)
            r.raise_for_status()
            j = r.json()
        self._token = j["access_token"]
        self._exp = time.time() + int(j.get("expires_in", 3600))
        return self._token

    async def _headers(self) -> dict:
        return {"Authorization": f"Bearer {await self._get_token()}"}

    async def find_user(self, email: str) -> dict | None:
        """사내 사용자(Teams/Entra 계정) 존재 확인.

        이 앱 자격증명은 디렉터리 읽기(User.Read.All)가 없고 전 사서함 Mail 권한만 있으므로,
        사서함(Inbox) 접근 가능 여부로 실제 계정을 판별한다.
        존재하면 200(→dict 반환), 없으면 404/ErrorInvalidUser(→None)."""
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{_GRAPH}/users/{email}/mailFolders/Inbox",
                headers=await self._headers(),
            )
            if r.status_code == 200:
                return {"mail": email}
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return None

    async def list_messages(self, mailbox: str, since_iso: str | None = None, top: int = 25) -> list[dict]:
        params = {"$top": str(top), "$orderby": "receivedDateTime desc",
                  "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,hasAttachments,importance"}
        if since_iso:
            params["$filter"] = f"receivedDateTime ge {since_iso}"
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{_GRAPH}/users/{mailbox}/mailFolders/Inbox/messages",
                            headers=await self._headers(), params=params)
            r.raise_for_status()
            return r.json().get("value", [])

    async def get_message(self, mailbox: str, message_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{_GRAPH}/users/{mailbox}/messages/{message_id}", headers=await self._headers())
            r.raise_for_status()
            return r.json()

    @staticmethod
    def _recipients(value: str | list[str] | None) -> list[dict]:
        """쉼표 구분 문자열 또는 리스트 → Graph recipients 배열."""
        if not value:
            return []
        items = value if isinstance(value, list) else str(value).split(",")
        return [{"emailAddress": {"address": a.strip()}} for a in items if a.strip()]

    async def send_mail(
        self, sender: str, to: str | list[str], subject: str, body_text: str,
        cc: str | list[str] | None = None,
    ) -> None:
        message: dict = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": self._recipients(to),
        }
        cc_list = self._recipients(cc)
        if cc_list:
            message["ccRecipients"] = cc_list
        payload = {"message": message, "saveToSentItems": True}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{_GRAPH}/users/{sender}/sendMail", headers=await self._headers(), json=payload)
            if r.status_code >= 400:
                raise RuntimeError(f"send_mail 실패 {r.status_code}: {r.text}")

    async def download_shared_file(self, share_url: str) -> bytes:
        b64 = base64.b64encode(share_url.encode()).decode().rstrip("=").replace("/", "_").replace("+", "-")
        share_id = f"u!{b64}"
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            r = await c.get(f"{_GRAPH}/shares/{share_id}/driveItem/content", headers=await self._headers())
            r.raise_for_status()
            return r.content

    @staticmethod
    def _expiry(minutes: int) -> str:
        from datetime import datetime, timedelta, timezone

        return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    async def create_subscription(self, mailbox: str, notification_url: str, minutes: int = 120) -> dict:
        """수신 메일 구독(webhook). notification_url 은 Graph(외부)가 HTTPS로 도달 가능해야 함.
        메시지 리소스 구독의 최대 만료는 약 4230분(~3일)이라 주기적 갱신 필요."""
        payload = {
            "changeType": "created",
            "notificationUrl": notification_url,
            "resource": f"/users/{mailbox}/mailFolders('Inbox')/messages",
            "expirationDateTime": self._expiry(minutes),
            "clientState": settings.graph_webhook_client_state,
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{_GRAPH}/subscriptions", headers=await self._headers(), json=payload)
            if r.status_code >= 400:
                raise RuntimeError(f"구독 생성 실패 {r.status_code}: {r.text}")
            return r.json()

    async def renew_subscription(self, subscription_id: str, minutes: int = 120) -> dict:
        payload = {"expirationDateTime": self._expiry(minutes)}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.patch(f"{_GRAPH}/subscriptions/{subscription_id}",
                              headers=await self._headers(), json=payload)
            if r.status_code >= 400:
                raise RuntimeError(f"구독 갱신 실패 {r.status_code}: {r.text}")
            return r.json()

    async def delete_subscription(self, subscription_id: str) -> None:
        async with httpx.AsyncClient(timeout=30) as c:
            await c.delete(f"{_GRAPH}/subscriptions/{subscription_id}", headers=await self._headers())


graph_client = GraphClient()
