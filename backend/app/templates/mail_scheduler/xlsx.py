"""범용 xlsx 파서.

특정 양식에 종속되지 않도록, 첫 시트에서 '헤더 행'을 자동으로 찾아
(컬럼명 목록, 각 행을 {컬럼명: 값} 으로 담은 dict 목록)을 돌려준다.

헤더 추정: 상단 일부 행 중 '비어 있지 않은 셀이 가장 많은' 행을 헤더로 본다.
값은 사람이 읽는 문자열로 정규화(정수는 소수점 제거, 날짜는 YYYY-MM-DD)한다.
"""

from __future__ import annotations

import datetime as _dt
import io

from openpyxl import load_workbook

_HEADER_SCAN_ROWS = 15


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if isinstance(v, _dt.datetime):
        return v.date().isoformat() if v.time() == _dt.time(0, 0) else v.isoformat(sep=" ")
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    return str(v).strip()


def parse_table(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """(헤더 컬럼명 목록, 데이터 행 dict 목록) 반환."""
    wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]

    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    if not rows:
        return [], []

    # 상단 스캔 구간에서 비어있지 않은 셀이 가장 많은 행을 헤더로.
    best_idx, best_count = 0, -1
    for i, r in enumerate(rows[:_HEADER_SCAN_ROWS]):
        count = sum(1 for c in r if _fmt(c))
        if count > best_count:
            best_idx, best_count = i, count
    if best_count < 1:
        return [], []

    header_cells = [_fmt(c) for c in rows[best_idx]]
    # 빈 컬럼명은 건너뛰고, 중복은 접미사로 구분.
    columns: list[str] = []
    col_index: list[int] = []
    seen: dict[str, int] = {}
    for idx, name in enumerate(header_cells):
        if not name:
            continue
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        columns.append(name)
        col_index.append(idx)

    data_rows: list[dict[str, str]] = []
    for r in rows[best_idx + 1:]:
        cells = [_fmt(c) for c in r]
        row = {columns[j]: (cells[idx] if idx < len(cells) else "") for j, idx in enumerate(col_index)}
        if any(v for v in row.values()):  # 완전 빈 행 제외
            data_rows.append(row)
    return columns, data_rows
