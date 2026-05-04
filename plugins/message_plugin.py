from telegram.ext import MessageHandler, filters
from handlers.message_handler import handle_all_messages


def register(app, config):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
