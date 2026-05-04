from telegram.ext import CommandHandler
from handlers.notice_handler import start, notice, broadcast


def register(app, config):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("broadcast", broadcast))
