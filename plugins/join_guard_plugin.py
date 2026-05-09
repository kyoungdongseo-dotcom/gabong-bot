from telegram.ext import Application, ChatMemberHandler, CommandHandler
from handlers.join_guard_handler import handle_bot_added, add_group


def register(app: Application, config):
    app.add_handler(ChatMemberHandler(handle_bot_added, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("add_group", add_group))
    print("✅ 봇 초대 관리자 전용 가드 등록 완료")
