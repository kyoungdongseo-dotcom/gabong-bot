"""신천지 연도 + 월 + N째주 라벨 계산.

- 신1년 = 1984년 기준 (당해 연도 - 1984 + 1 = 신N년)
- 해당 월의 **첫 월요일**을 1째주의 시작점으로 사용
- target_date 가 어느 월요일 블록에 속하는지 계산 → 1째주 / 2째주 / ...
- target_date 가 첫 월요일 이전이면 "전월의 마지막 주" 가 아니라 안전하게 1째주로 표시
  (운영 정책: 사용자 혼동 최소화 — 매월 첫 주차로 시작)
"""

from datetime import date, timedelta

SINCHUNJI_BASE_YEAR = 1984  # 신1년 = 1984


def _first_monday(year: int, month: int) -> date:
    d = date(year, month, 1)
    # weekday(): 월=0 ... 일=6
    offset = (0 - d.weekday()) % 7
    return d + timedelta(days=offset)


def get_sinchunji_week_label(target_date: date | None = None) -> str:
    if target_date is None:
        target_date = date.today()

    sin_year = target_date.year - SINCHUNJI_BASE_YEAR + 1
    month = target_date.month
    first_mon = _first_monday(target_date.year, month)

    if target_date < first_mon:
        week = 1
    else:
        delta_days = (target_date - first_mon).days
        week = delta_days // 7 + 1

    return f"신{sin_year}년 {month}월 {week}째주"
