from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None = None
    department: str | None = None

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
    phase: str | None = None
    priority: str
    latest_update: str | None = None

    class Config:
        from_attributes = True


class IssueOut(BaseModel):
    id: uuid.UUID
    type: str
    summary: str
    severity: str
    status: str

    class Config:
        from_attributes = True
