from telegram.ext import CommandHandler
import config
from handlers.ai_advanced_handler import (
    mode_command,
    weekly_report,
    summary_detailed,
    summary_brief,
    send_weekly_report_job,
)
from utils import scheduler


def register(app, config):
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("weekly_report", weekly_report))
    app.add_handler(CommandHandler("summary_detailed", summary_detailed))
    app.add_handler(CommandHandler("summary_brief", summary_brief))


def post_init(app):
    day_of_week = config.get('weekly_report_day') or 'mon'
    report_time = config.get('weekly_report_time') or '09:00'
    try:
        hour, minute = map(int, report_time.split(':'))
    except Exception:
        hour, minute = 9, 0

    scheduler.add_job(
        send_weekly_report_job,
        'cron',
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
        args=[app.bot],
        id='weekly_report_auto',
    )
