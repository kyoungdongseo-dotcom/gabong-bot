from telegram.ext import MessageHandler, filters
from handlers.press_handler import handle_press_photo, handle_press_text


def register(app, config=None):
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_press_photo),
        group=-1
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_press_text),
        group=-1
    )
    print("✅ 언론보도 보고서 핸들러 등록 완료 (사진+텍스트)")


def post_init(app):
    """봇 시작 시 PENDING 복원"""
    from handlers.press_handler import restore_pending_from_db
    restore_pending_from_db()
