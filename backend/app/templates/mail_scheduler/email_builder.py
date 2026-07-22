"""제목/본문 템플릿 렌더링.

사용자가 작성한 템플릿 안의 {{컬럼명}} 토큰을 해당 행의 값으로 치환한다.
특수 토큰 {{오늘}} 은 실행일 날짜로 치환.
"""

from __future__ import annotations

import re
from datetime import date

_TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def _date_dot(d: date) -> str:
    return f"{d.year}.{d.month}.{d.day}"


def render(template: str | None, row: dict[str, str], today: date) -> str:
    if not template:
        return ""

    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        if key in ("오늘", "today", "날짜"):
            return _date_dot(today)
        return row.get(key, "")

    return _TOKEN.sub(repl, template)


def used_columns(template: str | None) -> list[str]:
    """템플릿에서 참조하는 컬럼명 목록(특수 토큰 제외)."""
    if not template:
        return []
    specials = {"오늘", "today", "날짜"}
    return [m.strip() for m in _TOKEN.findall(template) if m.strip() not in specials]
