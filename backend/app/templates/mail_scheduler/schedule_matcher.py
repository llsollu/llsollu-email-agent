"""발행예정일 패턴 매칭. 기존 mailing/src/scheduleMatcher.ts 이식.

지원 패턴 2가지:
  "월/20일"        -> 매월 20일
  "3,6,9,12월 말"  -> 3/6/9/12월의 말일
그 외는 매칭하지 않는다.
"""

import calendar
import re
from datetime import date

_MONTHLY_DAY_RE = re.compile(r"^월/(\d{1,2})일$")
_MONTH_END_RE = re.compile(r"^([\d,\s]+)월\s*말$")


def is_scheduled_today(pattern: str | None, today: date) -> bool:
    if not pattern:
        return False
    p = pattern.strip()

    m = _MONTHLY_DAY_RE.match(p)
    if m:
        return today.day == int(m.group(1))

    m = _MONTH_END_RE.match(p)
    if m:
        months = [int(x.strip()) for x in m.group(1).split(",") if x.strip().isdigit()]
        if today.month not in months:
            return False
        last_day = calendar.monthrange(today.year, today.month)[1]
        return today.day == last_day

    return False
