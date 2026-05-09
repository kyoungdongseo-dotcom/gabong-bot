from telegram.ext import MessageHandler, filters
from handlers.award_handler import handle_award_photo, handle_award_text


def register(app, config=None):
    # 사진 (캡션 있음/없음 모두)
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_award_photo),
        group=-1
    )
    # 텍스트 보고서 (사진 나중에 오는 케이스)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_award_text),
        group=-1
    )
    print("✅ 수상보고서 핸들러 등록 완료 (사진+텍스트)")
