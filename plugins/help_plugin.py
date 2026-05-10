from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers.help_handler import help_command, help_callback, myreports_command


def register(app, config=None):
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myreports", myreports_command))
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help_"))
    print("✅ /help, /myreports 명령어 등록 완료")
