from telegram.ext import CommandHandler
from handlers.weekly_ops_report import weekly_ops_command


def register(app, config=None):
    app.add_handler(CommandHandler("weekly_ops", weekly_ops_command))
    print("✅ /weekly_ops 명령어 등록 완료")


async def post_init(app):
    """봇 시작 시 매주 월 10:00 KST 스케줄 등록"""
    try:
        from utils import scheduler
        from handlers.weekly_ops_report import send_weekly_ops_report
        scheduler.add_job(
            send_weekly_ops_report, 'cron',
            day_of_week='mon', hour=10, minute=0,
            args=[app.bot], id="weekly_ops_report",
            replace_existing=True,
        )
        print("✅ 주간 운영 리포트 스케줄 등록 (매주 월 10:00 KST)")
    except Exception as e:
        print(f"⚠️ 주간 운영 리포트 스케줄 등록 실패: {e}")
