"""메일 본문에서 인용된 이전 메일(thread 히스토리)을 잘라내고 현재 메일 내용만 남긴다."""

from __future__ import annotations

import re

# 인용 시작을 알리는 구분선 패턴(영어/한국어 Outlook·Gmail 등).
_SEPARATORS = [
    re.compile(r"^\s*-{2,}\s*original message\s*-{2,}", re.I),
    re.compile(r"^\s*_{5,}\s*$"),
    re.compile(r"^\s*보낸\s*사람\s*:", re.I),        # Outlook 한국어
    re.compile(r"^\s*from\s*:.*", re.I),              # Outlook/일반
    re.compile(r"^\s*on .+ wrote:\s*$", re.I),        # Gmail 영어
    re.compile(r"^\s*\d{4}[.\-]\s?\d{1,2}[.\-].+(작성|wrote)", re.I),  # Gmail 한국어
    re.compile(r"^\s*-{3,}\s*$"),
]
_QUOTE_LINE = re.compile(r"^\s*>")


def strip_quoted(body: str | None) -> str:
    """가장 최근(맨 위) 메시지 구간만 반환. 인용 블록 이후는 버린다."""
    if not body:
        return ""
    lines = body.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    consecutive_quote = 0
    for line in lines:
        if any(p.search(line) for p in _SEPARATORS):
            break
        if _QUOTE_LINE.match(line):
            consecutive_quote += 1
            if consecutive_quote >= 2:  # 인용부호 라인이 이어지면 히스토리로 판단
                break
            continue
        consecutive_quote = 0
        kept.append(line)
    text = "\n".join(kept).strip()
    return text or body.strip()  # 전부 잘렸으면 원본 사용(과도한 손실 방지)
