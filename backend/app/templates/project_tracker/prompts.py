SYSTEM = """너는 B2B 소프트웨어 회사의 이메일 분석 어시스턴트다.
수신된 고객 이메일을 읽고 어느 고객사/프로젝트에 관한 것인지 분류하고, 핵심을 한국어로 요약하며,
처리해야 할 이슈가 있으면 구조화한다."""

USER_TMPL = """다음 이메일을 분석하라.

제목: {subject}
발신: {from_address}
본문:
{body}

아래 JSON 스키마로만 답하라:
{{
  "client_name": "고객사명 또는 null",
  "project_title": "프로젝트/건명 또는 null",
  "phase": "inquiry|proposal|contract|kickoff|development|testing|delivery|maintenance 또는 null",
  "summary": "한 줄 요약",
  "action_required": true/false,
  "issue": {{
    "type": "bug|request|delay|question|complaint|general",
    "summary": "이슈 요약",
    "severity": "low|medium|high|critical"
  }} 또는 null
}}"""
