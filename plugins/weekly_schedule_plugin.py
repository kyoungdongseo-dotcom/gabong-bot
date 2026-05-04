from telegram.ext import Application
from handlers.weekly_schedule_handler import send_weekly_schedule
from datetime import time

def register(app: Application, config):
    """주간 스케줄 플러그인 등록"""
    # 매주 월요일 09:00에 실행
    job_queue = app.job_queue
    job_queue.run_weekly(
        send_weekly_schedule,
        day=0,  # 0 = 월요일
        time=time(9, 0, 0, tzinfo=None),
        name="weekly_schedule"
    )
    print("✅ 주간 스케줄 플러그인 등록됨 (매주 월 09:00)")
