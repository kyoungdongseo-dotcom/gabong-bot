"""양력 기준 'YYYY년 M월 N째주' 라벨.

- 해당 월의 첫 월요일을 1째주의 시작점으로 사용
- 첫 월요일 이전 날짜는 1째주로 처리 (운영 정책: 사용자 혼동 최소화)
"""

from datetime import date, timedelta


def get_week_label(target_date: date | None = None) -> str:
    if target_date is None:
        target_date = date.today()

    first_day = target_date.replace(day=1)
    days_until_monday = (7 - first_day.weekday()) % 7
    first_monday = first_day + timedelta(days=days_until_monday)

    if target_date < first_monday:
        week_num = 1
    else:
        week_num = ((target_date - first_monday).days // 7) + 1

    return f"{target_date.year}년 {target_date.month}월 {week_num}째주"
