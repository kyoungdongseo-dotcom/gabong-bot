from telegram.ext import CommandHandler
from handlers.status_handler import status_command


def register(app, config=None):
    app.add_handler(CommandHandler("status", status_command))
    print("✅ 상태 핸들러 등록 완료")
