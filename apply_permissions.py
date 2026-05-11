import re

# ── ai_handler.py 수정 ──────────────────────────────────────────
ai_path = "/Users/seogyeongdong/gabong-bot/handlers/ai_handler.py"
with open(ai_path, "r") as f:
    src = f.read()

# import 추가
if "from utils.permissions import check_admin" not in src:
    src = src.replace(
        "from telegram import Update",
        "from telegram import Update\nfrom utils.permissions import check_admin"
    )

# ai_command 권한 추가
src = src.replace(
    "async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not context.args:",
    "async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    if not context.args:"
)

# summary 권한 추가
src = src.replace(
    "async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    chat_id",
    "async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    chat_id"
)

# reset 권한 추가
src = src.replace(
    "async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    chat_id",
    "async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    chat_id"
)

with open(ai_path, "w") as f:
    f.write(src)
print("✅ ai_handler.py 완료")


# ── ai_advanced_handler.py 수정 ────────────────────────────────
adv_path = "/Users/seogyeongdong/gabong-bot/handlers/ai_advanced_handler.py"
with open(adv_path, "r") as f:
    src = f.read()

# import 추가
if "from utils.permissions import check_admin" not in src:
    src = src.replace(
        "from telegram import Update",
        "from telegram import Update\nfrom utils.permissions import check_admin"
    )

# mode_command 권한 추가
src = src.replace(
    "async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not context.args:",
    "async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    if not context.args:"
)

# weekly_report 권한 추가
src = src.replace(
    "async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    chat_id = update.effective_chat.id\n    user_id = update.effective_user.id\n    user_name = update.effective_user.first_name\n    thread_id = update.message.message_thread_id\n\n    since",
    "async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    chat_id = update.effective_chat.id\n    user_id = update.effective_user.id\n    user_name = update.effective_user.first_name\n    thread_id = update.message.message_thread_id\n\n    since"
)

# summary_detailed 권한 추가
src = src.replace(
    "async def summary_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    chat_id",
    "async def summary_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    chat_id"
)

# summary_brief 권한 추가
src = src.replace(
    "async def summary_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    chat_id",
    "async def summary_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    if not update.message:\n        return\n    if not await check_admin(update, context):\n        return\n    chat_id"
)

with open(adv_path, "w") as f:
    f.write(src)
print("✅ ai_advanced_handler.py 완료")

print("\n🎉 모든 권한 설정 완료!")
print("remind 계열은 그대로 유지 (공통 사용 허용)")
