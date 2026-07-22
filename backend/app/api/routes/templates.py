from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import get_current_user
from app.framework.registry import all_templates, get_template
from app.models import User
from app.schemas.models import (
    ColumnsPreviewRequest,
    ColumnsPreviewResponse,
    ConfigFieldOut,
    TemplateOut,
)
from app.services.graph import graph_client
from app.templates.mail_scheduler.xlsx import parse_table

router = APIRouter()


@router.post("/mail_scheduler/columns", response_model=ColumnsPreviewResponse)
async def preview_columns(
    body: ColumnsPreviewRequest, _: User = Depends(get_current_user)
) -> ColumnsPreviewResponse:
    """참조 파일(xlsx)을 내려받아 컬럼명과 첫 행 샘플을 반환. 2단계 마법사에서 사용."""
    if not body.file_url.strip():
        raise HTTPException(status_code=400, detail="참조 파일 URL이 필요합니다")
    try:
        data = await graph_client.download_shared_file(body.file_url.strip())
        columns, rows = parse_table(data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"파일을 읽을 수 없습니다: {e}") from e
    if not columns:
        raise HTTPException(status_code=422, detail="파일에서 컬럼(헤더)을 찾지 못했습니다")
    return ColumnsPreviewResponse(columns=columns, sample=rows[0] if rows else {}, row_count=len(rows))


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
