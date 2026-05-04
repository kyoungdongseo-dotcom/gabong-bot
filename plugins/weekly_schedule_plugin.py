from telegram.ext import Application
from handlers.weekly_schedule_handler import send_weekly_schedule, schedule_command
from datetime import time
import pytz

def register(app: Application, config):
    """주간 스케줄 플러그인 등록"""
    job_queue = app.job_queue
    
    # 매주 월요일 09:00 (한국 시간)에 실행
    job_queue.run_repeating(
        send_weekly_schedule,
        interval=604800,  # 1주일 = 604800초
        first=time(9, 0, 0, tzinfo=pytz.timezone('Asia/Seoul')),
        day_of_week=0,  # 0 = 월요일
        name="weekly_schedule"
    )
    print("✅ 주간 스케줄 플러그인 등록됨 (매주 월 09:00)")
    
    # /schedule 명령어 등록
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("schedule", schedule_command))
    print("✅ /schedule 명령어 등록됨 (사용자 호출 가능)")
