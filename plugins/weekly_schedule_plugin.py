"""
주간 봉사일정 플러그인

스케줄: 매주 일요일 08:00 KST 자동 발송
명령어: /weekly_report (관리자 즉시 발송)
        /schedule      (기존 명령어 유지, 동일 동작)
"""

import pytz
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler

from handlers.weekly_schedule_handler import (
    send_weekly_schedule_job,
    weekly_report_command,
    schedule_command,
)

KST = pytz.timezone('Asia/Seoul')


def register(app: Application, config):
    """주간 봉사일정 플러그인 등록"""
    job_queue = app.job_queue

    # ── 다음 일요일 08:00 KST 계산 ──
    now_kst = datetime.now(KST)
    # Python weekday: 0=월 … 6=일
    days_to_sunday = (6 - now_kst.weekday()) % 7
    # 오늘이 일요일이고 08:00 이후면 다음 주 일요일로
    if days_to_sunday == 0 and now_kst.hour >= 8:
        days_to_sunday = 7

    next_sunday_kst = (now_kst + timedelta(days=days_to_sunday)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )
    # job_queue 는 UTC 기준 → KST에서 변환
    next_sunday_utc = next_sunday_kst.astimezone(pytz.utc)

    job_queue.run_repeating(
        send_weekly_schedule_job,   # ← job 콜백: context 만 받음 (bug 수정)
        interval=604800,            # 1주일 = 7 × 24 × 60 × 60 초
        first=next_sunday_utc,
        name="weekly_schedule_auto",
    )
    print(
        f"✅ 주간 봉사일정 자동 발송 등록 완료\n"
        f"   다음 발송 예정: {next_sunday_kst.strftime('%Y-%m-%d %H:%M')} KST (매주 일요일 08:00)"
    )

    # ── 명령어 등록 ──
    app.add_handler(CommandHandler("weekly_report", weekly_report_command))
    app.add_handler(CommandHandler("schedule", schedule_command))
    print("✅ /weekly_report, /schedule 명령어 등록됨")
