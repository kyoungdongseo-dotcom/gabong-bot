from telegram.ext import Application, ChatMemberHandler
from handlers.join_guard_handler import handle_bot_added

def register(app: Application, config):
    app.add_handler(
        ChatMemberHandler(handle_bot_added, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    print("✅ 봇 초대 관리자 전용 가드 등록 완료")
