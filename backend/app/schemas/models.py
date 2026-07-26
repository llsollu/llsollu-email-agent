from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = True


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = True


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    # existing: DB에 있음(비번 확인 필요) / needs_setup: 사내 계정이나 미가입(비번 설정) / not_company: 회사 계정 아님
    status: str
    display_name: str | None = None


class ColumnsPreviewRequest(BaseModel):
    file_url: str


class ColumnsPreviewResponse(BaseModel):
    columns: list[str]
    sample: dict[str, str] = {}
    row_count: int = 0


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    department: str | None = None
    # 데스크톱(Tauri)용 Bearer 토큰. 로그인/가입 응답에만 채워지고 웹은 무시(쿠키 사용).
    access_token: str | None = None

    class Config:
        from_attributes = True


class ConfigFieldOut(BaseModel):
    key: str
    label: str
    type: str
    required: bool
    help: str | None = None
    options: list[str] | None = None
    default: object | None = None
    secret: bool = False


class TemplateOut(BaseModel):
    key: str
    name: str
    version: str
    description: str
    trigger_kind: str
    view_type: str


class AgentCreate(BaseModel):
    template_key: str
    name: str
    config: dict = {}
    secrets: dict = {}


class AgentUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    secrets: dict | None = None  # 미입력 필드는 기존값 유지(라우트에서 병합)


class AgentOut(BaseModel):
    id: uuid.UUID
    template_key: str
    name: str
    status: str
    error_detail: str | None = None
    config: dict
    view_type: str | None = None
    views: list[dict] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: uuid.UUID
    trigger_source: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None
    stats: dict

    class Config:
        from_attributes = True


class ScheduleOut(BaseModel):
    id: uuid.UUID
    cron: str
    timezone: str
    enabled: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None

    class Config:
        from_attributes = True


class ScheduleToggle(BaseModel):
    enabled: bool


class ProjectOut(BaseModel):
    id: uuid.UUID
    client_name: str
    title: str
    status: str
    category: str | None = None
    priority: str
    latest_update: str | None = None
    keywords: list | None = None
    from_name: str | None = None
    from_address: str | None = None
    recipient_role: str | None = None
    updated_at: datetime | None = None
    source_message_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class TimelineEntry(BaseModel):
    id: uuid.UUID
    client_name: str | None = None
    project_title: str | None = None
    category: str | None = None
    subject: str | None = None
    from_address: str | None = None
    from_name: str | None = None
    direction: str = "in"
    received_at: datetime | None = None
    summary: str | None = None
    action_required: bool = False
    issue: dict | None = None
    points: list | None = None
    keywords: list | None = None
    recipient_role: str | None = None

    class Config:
        from_attributes = True


class MailRecordOut(TimelineEntry):
    """원문 모달용 — 기본 정보 + 본문 + 수신/참조 전체."""
    mailbox: str
    body_text: str | None = None
    to_recipients: str | None = None
    cc_recipients: str | None = None


class IssueOut(BaseModel):
    id: uuid.UUID
    type: str
    summary: str
    severity: str
    status: str

    class Config:
        from_attributes = True
