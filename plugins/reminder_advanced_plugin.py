from telegram.ext import CommandHandler, MessageHandler, filters

from handlers.reminder_advanced_handler import (
    remind_if_keyword,
    handle_remind_if_keyword_command,
    reminder_stats,
    reminder_analysis
)


def register(app, config=None):
    """고급 리마인더 플러그인 등록"""

    try:
        # 명령어 핸들러
        app.add_handler(CommandHandler("reminder_stats", reminder_stats))
        app.add_handler(CommandHandler("reminder_analysis", reminder_analysis))

        # 키워드 리마인더 설정 명령어
        app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex(r'^/remind_if_keyword\s+'),
            handle_remind_if_keyword_command
        ))

        # 메시지 기반 키워드 감지 (항상 실행되어야 함)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            remind_if_keyword
        ))

        print("✅ 리마인더 고급 플러그인 등록 완료")

    except Exception as e:
        print(f"❌ 리마인더 고급 플러그인 등록 실패: {e}")


async def post_init(app):
    """플러그인 초기화 (현재 추가 작업 없음)"""
    pass
