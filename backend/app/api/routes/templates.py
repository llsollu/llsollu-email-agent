from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_current_user
from app.framework.registry import all_templates, get_template
from app.models import User
from app.schemas.models import ConfigFieldOut, TemplateOut

router = APIRouter()


@router.get("", response_model=list[TemplateOut])
async def list_templates(_: User = Depends(get_current_user)) -> list[TemplateOut]:
    return [
        TemplateOut(
            key=t.key, name=t.name, version=t.version, description=t.description,
            trigger_kind=t.trigger.kind, view_type=t.view.view_type,
        )
        for t in all_templates()
    ]


@router.get("/{key}/config-schema", response_model=list[ConfigFieldOut])
async def config_schema(key: str, _: User = Depends(get_current_user)) -> list[ConfigFieldOut]:
    try:
        t = get_template(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")
    return [ConfigFieldOut(**f.__dict__) for f in t.config_schema()]
