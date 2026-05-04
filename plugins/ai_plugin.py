from telegram.ext import CommandHandler
from handlers.ai_handler import ai_command, summary, reset


def register(app, config):
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("reset", reset))
