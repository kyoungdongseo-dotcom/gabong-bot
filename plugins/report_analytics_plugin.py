from telegram.ext import CommandHandler
from handlers.report_analytics import report_stats_command


def register(app, config=None):
    app.add_handler(CommandHandler("report_stats", report_stats_command))
    print("✅ /report_stats 명령어 등록 완료")


async def post_init(app):
    """봇 시작 시: PENDING 복원 + 스케줄러 등록"""
    # 1) PENDING 복원
    try:
        from handlers.award_handler import restore_pending_from_db as restore_award
        restore_award()
    except Exception as e:
        print(f"⚠️ award PENDING 복원 호출 실패: {e}")
    try:
        from handlers.mou_handler import restore_pending_from_db as restore_mou
        restore_mou()
    except Exception as e:
        print(f"⚠️ MOU PENDING 복원 호출 실패: {e}")

    # 2) 일일 분석 스케줄 등록 (09:00 KST)
    try:
        from utils import scheduler
        from handlers.report_analytics import send_daily_analysis
        scheduler.add_job(
            send_daily_analysis, 'cron',
            hour=9, minute=0,
            args=[app.bot],
            id="daily_report_analysis",
            replace_existing=True,
        )
        print("✅ 일일 보고서 분석 스케줄 등록 (매일 09:00 KST)")
    except Exception as e:
        print(f"⚠️ 일일 분석 스케줄 등록 실패: {e}")
