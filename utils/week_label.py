"""양력 + 일요일 시작 컨벤션 'YYYY년 M월 N째주' 라벨 (한국 관행).

규칙:
- 1주 = 일요일 ~ 토요일
- 한 달의 첫 일요일이 1~3일이면 → 1째주는 그 일요일이 속한 주 전체
  (이전 1~2일의 부분주를 1째주에 통합)
- 첫 일요일이 4일 이후면 → 1일 ~ (첫일요일 - 1) 까지 부분주가 1째주,
  첫 일요일부터 2째주

예시:
- 5월(1=금, 첫 일요일=3): 5/1~5/9 모두 1째주
- 6월(1=월, 첫 일요일=7): 6/1~6/6 = 1째주, 6/7~ = 2째주
- 11월(1=일, 첫 일요일=1): 11/1~11/7 = 1째주
"""

from __future__ import annotations

from datetime import date, timedelta


def get_week_label(target_date: date | None = None) -> str:
    if target_date is None:
        target_date = date.today()

    # weekday(): 월=0..일=6
    first_day = target_date.replace(day=1)
    days_until_sunday = (6 - first_day.weekday()) % 7
    first_sunday = first_day + timedelta(days=days_until_sunday)

    # 첫 일요일이 1~3일이면 1째주에 통합, 4일 이후면 첫 일요일이 2째주 시작
    base_offset = 1 if first_sunday.day <= 3 else 2

    if target_date < first_sunday:
        week_num = 1
    else:
        week_num = ((target_date - first_sunday).days // 7) + base_offset

    return f"{target_date.year}년 {target_date.month}월 {week_num}째주"
