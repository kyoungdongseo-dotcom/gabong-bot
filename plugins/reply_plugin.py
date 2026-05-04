from telegram.ext import CommandHandler
from handlers.reply_handler import reply_command


def register(app, config):
    app.add_handler(CommandHandler("reply", reply_command))
