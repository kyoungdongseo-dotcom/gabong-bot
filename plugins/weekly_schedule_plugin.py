from telegram.ext import Application, CommandHandler
from handlers.weekly_schedule_handler import send_weekly_schedule, schedule_command
from datetime import time

def register(app: Application, config):
    """주간 스케줄 플러그인 등록"""
    job_queue = app.job_queue
    job_queue.run_weekly(
        send_weekly_schedule,
        day=0,
        time=time(9, 0, 0, tzinfo=None),
        name="weekly_schedule"
    )
    print("✅ 주간 스케줄 플러그인 등록됨 (매주 월 09:00)")
    
    # /schedule 명령어 등록
    app.add_handler(CommandHandler("schedule", schedule_command))
    print("✅ /schedule 명령어 등록됨 (사용자 호출 가능)")
