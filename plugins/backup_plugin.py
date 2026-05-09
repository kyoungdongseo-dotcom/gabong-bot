from telegram.ext import CommandHandler
from handlers.backup_handler import backup_command


def register(app, config=None):
    app.add_handler(CommandHandler("backup", backup_command))
    print("✅ 백업 핸들러 등록 완료")
