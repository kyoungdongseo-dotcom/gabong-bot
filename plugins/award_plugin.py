from telegram.ext import MessageHandler, filters
from handlers.award_handler import handle_award_message


def register(app, config=None):
    app.add_handler(
        MessageHandler(filters.PHOTO & filters.CAPTION, handle_award_message),
        group=-1
    )
    print("✅ 수상보고서 핸들러 등록 완료")
