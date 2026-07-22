"""템플릿 레지스트리 — key → AgentTemplate 인스턴스."""

from __future__ import annotations

from app.framework.base import AgentTemplate

_REGISTRY: dict[str, AgentTemplate] = {}


def register(template: AgentTemplate) -> AgentTemplate:
    if template.key in _REGISTRY:
        raise ValueError(f"중복 템플릿 키: {template.key}")
    _REGISTRY[template.key] = template
    return template


def get_template(key: str) -> AgentTemplate:
    if key not in _REGISTRY:
        raise KeyError(f"알 수 없는 템플릿: {key}")
    return _REGISTRY[key]


def all_templates() -> list[AgentTemplate]:
    return list(_REGISTRY.values())


def load_builtin_templates() -> None:
    """내장 템플릿 등록. import 시 데코레이터/register 호출로 채워진다."""
    from app.templates import mail_scheduler, project_tracker  # noqa: F401
