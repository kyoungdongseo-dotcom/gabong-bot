from telegram.ext import CommandHandler
from handlers.notice_handler import start, notice, broadcast
from handlers.weekly_schedule_handler import schedule, weekly_report


def register(app, config):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CommandHandler("weekly_report", weekly_report))
