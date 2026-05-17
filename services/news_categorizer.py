"""뉴스 카테고리 분류 (봉사 효과성 기준 7개).

우선순위: 봉사기회 → 협업가능 → 긴급이슈 → 협업키맨 → 정책 → 행사 → 기타.
"""

SERVICE_OPPORTUNITY_KW = ["축제", "박람회", "체험", "마라톤", "행진", "시민참여", "어울림", "걷기대회"]
COOPERATION_KW = ["봉사", "캠페인", "후원", "협약", "MOU", "지원사업", "보조금", "공모", "모집"]
URGENT_KW = ["재난", "이재민", "수해", "산불", "한파", "폭염", "사고", "화재", "사망", "긴급"]
KEYMAN_KW = ["시장", "구청장", "군수", "기관장", "임명", "취임", "방문"]
POLICY_KW = ["정책", "조례", "예산", "발표", "추진"]
EVENT_KW = ["행사", "개최", "전시", "공연"]


def categorize(title: str, summary: str) -> str:
    text = (title or "") + " " + (summary or "")
    if any(kw in text for kw in SERVICE_OPPORTUNITY_KW):
        return "봉사기회"
    if any(kw in text for kw in COOPERATION_KW):
        return "협업가능"
    if any(kw in text for kw in URGENT_KW):
        return "긴급이슈"
    if any(kw in text for kw in KEYMAN_KW):
        return "협업키맨"
    if any(kw in text for kw in POLICY_KW):
        return "정책"
    if any(kw in text for kw in EVENT_KW):
        return "행사"
    return "기타"
