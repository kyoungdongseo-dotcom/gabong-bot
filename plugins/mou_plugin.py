from telegram.ext import MessageHandler, filters
from handlers.mou_handler import handle_mou_photo, handle_mou_text


def register(app, config=None):
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_mou_photo),
        group=-1
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mou_text),
        group=-1
    )
    print("✅ MOU 체결보고서 핸들러 등록 완료 (사진+텍스트)")
