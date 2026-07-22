"""발송기준일 매칭.

발송기준일 컬럼의 셀 값이 '오늘' 발송 대상인지 판정한다. 지원 형식:
  "월/20일", "20일", "20"         -> 매월 20일
  "3,6,9,12월 말"                 -> 해당 월들의 말일
  "2026-07-22", "2026.7.22"       -> 그 날짜에 1회
그 외/빈 값은 매칭하지 않는다(=오늘 발송 안 함).
"""

from __future__ import annotations

import calendar
import re
from datetime import date

_MONTHLY_DAY_RE = re.compile(r"^(?:월/)?(\d{1,2})일?$")
_MONTH_END_RE = re.compile(r"^([\d,\s]+)월\s*말$")
_DATE_RE = re.compile(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})$")


def is_scheduled_today(pattern: str | None, today: date) -> bool:
    if not pattern:
        return False
    p = pattern.strip()

    m = _DATE_RE.match(p)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            return date(y, mo, d) == today
        except ValueError:
            return False

    m = _MONTH_END_RE.match(p)
    if m:
        months = [int(x.strip()) for x in m.group(1).split(",") if x.strip().isdigit()]
        if today.month not in months:
            return False
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == last_day

    m = _MONTHLY_DAY_RE.match(p)
    if m:
        return today.day == int(m.group(1))

    return False
