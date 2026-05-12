from telegram.ext import CommandHandler, MessageHandler, filters
from handlers.notice_handler import (
    start, notice, broadcast, broadcast_photo, broadcast_document,
)
from handlers.weekly_schedule_handler import schedule, weekly_report


def register(app, config):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CommandHandler("weekly_report", weekly_report))
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.CAPTION,
        broadcast_photo
    ))
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.CAPTION,
        broadcast_document
    ))
