from telegram.ext import MessageHandler, filters
from handlers.press_handler import handle_press_photo, handle_press_text


def register(app, config=None):
    # group=-2 사용 — award_plugin (group=-1) 의 filters.PHOTO/TEXT 가
    # 모든 사진/텍스트를 먼저 매칭해 group=-1 슬롯을 소비하는 문제 회피.
    # 다른 group 에서 독립 실행되도록 분리 (2026-05-18 핫픽스).
    # PTB v22: 다른 그룹 끼리는 모두 실행됨 (같은 그룹 안에서만 first-match-wins).
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_press_photo),
        group=-2
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_press_text),
        group=-2
    )
    print("✅ 언론보도 보고서 핸들러 등록 완료 (group=-2, 사진+텍스트)")


def post_init(app):
    """봇 시작 시 PENDING 복원"""
    from handlers.press_handler import restore_pending_from_db
    restore_pending_from_db()
