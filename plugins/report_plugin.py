from telegram.ext import CommandHandler
from handlers.report_commands import report, monthly


def register(app, config):
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("monthly", monthly))
    print("✅ /report, /monthly 명령어 등록됨")
