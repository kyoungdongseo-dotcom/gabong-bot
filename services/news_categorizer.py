"""뉴스 제목 + 요약 기반 5종 카테고리 분류 (정책/행사/이슈/인물/기타)."""

CATEGORY_KEYWORDS = {
    "정책": ["정책", "조례", "예산", "지원", "사업", "추진", "발표"],
    "행사": ["축제", "행사", "박람회", "공연", "체험", "개최", "참여"],
    "이슈": ["사고", "화재", "사망", "논란", "민원", "갈등", "고발"],
    "인물": ["시장", "도지사", "구청장", "임명", "취임", "당선"],
}

CATEGORY_ORDER = ["이슈", "인물", "정책", "행사"]


def categorize(title: str, summary: str = "") -> str:
    text = f"{title or ''} {summary or ''}"
    for cat in CATEGORY_ORDER:
        for kw in CATEGORY_KEYWORDS[cat]:
            if kw in text:
                return cat
    return "기타"
