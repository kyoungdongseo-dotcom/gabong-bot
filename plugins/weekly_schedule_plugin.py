from telegram.ext import Application, CommandHandler
from handlers.weekly_schedule_handler import send_weekly_schedule, schedule_command
from datetime import time, datetime, timedelta

def register(app: Application, config):
    """주간 스케줄 플러그인 등록"""
    job_queue = app.job_queue
    
    # 다음 월요일 09:00 계산
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    first_run = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # 매주 월요일 09:00에 반복 (1주일 = 604800초)
    job_queue.run_repeating(
        send_weekly_schedule,
        interval=604800,  # 1주일
        first=first_run,
        name="weekly_schedule"
    )
    print("✅ 주간 스케줄 플러그인 등록됨 (매주 월 09:00)")
    
    # /schedule 명령어 등록
    app.add_handler(CommandHandler("schedule", schedule_command))
    print("✅ /schedule 명령어 등록됨 (사용자 호출 가능)")
