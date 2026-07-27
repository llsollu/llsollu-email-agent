"""제목/본문 템플릿 렌더링.

사용자가 작성한 템플릿 안의 {{컬럼명}} 토큰을 해당 행의 값으로 치환한다.
특수 토큰:
  {{오늘}} / {{날짜}}        → 실행일 날짜(YYYY.M.D)
  {{월}} / {{이번달월}}      → 실행월 숫자(예: 7)
  {{이번달}} / {{현재월}} / {{이달}}
                            → 실행월에 해당하는 '월 컬럼' 값
                              (예: 7월이면 "7월" 또는 "07월" 컬럼의 값)
"""

from __future__ import annotations

import re
from datetime import date

_TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

DATE_TOKENS = {"오늘", "today", "날짜"}
MONTH_NUM_TOKENS = {"월", "이번달월", "현재월숫자"}
MONTH_COL_TOKENS = {"이번달", "현재월", "이달", "이번달데이터"}
SPECIAL_TOKENS = DATE_TOKENS | MONTH_NUM_TOKENS | MONTH_COL_TOKENS


def _date_dot(d: date) -> str:
    return f"{d.year}.{d.month}.{d.day}"


def _month_column_value(row: dict[str, str], month: int) -> str:
    """실행월에 해당하는 '월 컬럼' 값을 찾는다. 여러 표기를 순서대로 시도."""
    for key in (f"{month}월", f"{month:02d}월", f"{month}", f"{month:02d}"):
        if key in row and row[key] != "":
            return row[key]
    return ""


MISSING = "<데이터 미수집>"


def render(template: str | None, row: dict[str, str], today: date, mark_missing: bool = False) -> str:
    """{{토큰}} 치환. mark_missing=True 면 값이 없는 데이터 토큰을 '<데이터 미수집>'으로 표시.
    (실제 발송은 기본값=빈 문자열, 오류 알림 미리보기는 mark_missing=True 로 사용)"""
    if not template:
        return ""
    miss = MISSING if mark_missing else ""

    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        if key in DATE_TOKENS:
            return _date_dot(today)
        if key in MONTH_NUM_TOKENS:
            return str(today.month)
        if key in MONTH_COL_TOKENS:
            return _month_column_value(row, today.month) or miss
        val = row.get(key, "")
        return val if val != "" else miss

    return _TOKEN.sub(repl, template)


def used_columns(template: str | None) -> list[str]:
    """템플릿에서 참조하는 컬럼명 목록(특수 토큰 제외)."""
    if not template:
        return []
    return [m.strip() for m in _TOKEN.findall(template) if m.strip() not in SPECIAL_TOKENS]
