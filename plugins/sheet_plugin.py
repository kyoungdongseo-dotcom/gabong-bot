from telegram.ext import CommandHandler
from handlers.sheet_handler import sheet


def register(app, config):
    app.add_handler(CommandHandler("sheet", sheet))
