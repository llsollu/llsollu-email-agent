"""세금계산서 발행요청 메일 본문 생성. 기존 mailing/src/emailBuilder.ts 이식.

필수 항목 누락 시 발송을 건너뛰고 관리자에게 알림을 보내되, 본문은 원래 형식 그대로에
누락 자리를 <누락> 으로 채우고 상단에 안내 문구를 붙인다.
"""

from __future__ import annotations

from datetime import date

from app.templates.mail_scheduler.xlsx import InvoiceRow

MISSING = "<누락>"

REQUIRED_FIELDS = [
    ("ceo_name", "대표자"),
    ("contact_name", "발행담당자명"),
    ("contact_email", "발행담당자이메일"),
    ("contact_phone", "발행담당자연락처"),
    ("sales_type", "매출형태"),
]


def _v(value: str) -> str:
    return value or MISSING


def missing_fields(row: InvoiceRow) -> list[str]:
    return [label for attr, label in REQUIRED_FIELDS if not getattr(row, attr)]


def _date_dot(d: date) -> str:
    return f"{d.year}.{d.month}.{d.day}"


def _date_short(d: date) -> str:
    return f"{d.month}/{d.day}"


def build_body(row: InvoiceRow, issue_date: date, recipient_name: str) -> str:
    amount = f"{row.monthly_amount:,}(vat 별도)" if row.monthly_amount is not None else "(금액 미확인 - 확인 필요)"
    contact = f"{_v(row.contact_name)} {_v(row.contact_email)} / {_v(row.contact_phone)}"
    return (
        f"안녕하세요, {recipient_name}\n\n"
        f"첨부 발주 및 하기 내용 참고하셔서 세금계산서 발행({_date_short(issue_date)}일) 요청 드립니다.\n\n"
        f"◇ 공급받는 자 : {row.client_name}\n"
        f"◇ 대표자 : {_v(row.ceo_name)}\n"
        f"◇ 건  명  : {row.maintenance_detail}\n"
        f"◇ 발행 이메일 : {contact}\n"
        f"◇ 세금계산서 발행일 : {_date_dot(issue_date)}\n"
        f"◇ 발행금액 : {amount}\n"
        f"◇ 매출형태 : {_v(row.sales_type)}"
    )


def build_subject(row: InvoiceRow, issue_date: date, missing: bool) -> str:
    tag = "세금계산서 발행정보 누락" if missing else "세금계산서 발행요청"
    return f"[{tag}] {row.client_name} - {row.maintenance_detail} ({_date_short(issue_date)})"


def build_missing_notice(recipient_name: str) -> str:
    return f"세금계산서 발행 예정 건에 필요한 정보가 엑셀에 누락되어 {recipient_name}께 자동 발송을 건너뛰었습니다."
