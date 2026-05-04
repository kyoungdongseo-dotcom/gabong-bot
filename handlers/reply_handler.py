from telegram import Update
from telegram.ext import ContextTypes
import config
from utils import LAST_MENTION

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    MY_USER_ID = config.get('my_user_id')
    if update.effective_user.id != MY_USER_ID:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /reply [내용]")
        return
    if MY_USER_ID not in LAST_MENTION:
        await update.message.reply_text("❌ 멘션된 메시지가 없습니다.")
        return
    text = update.message.text.split("/reply ", 1)[1]
    mention_info = LAST_MENTION[MY_USER_ID]
    await context.bot.send_message(
        chat_id=mention_info["chat_id"],
        text=f"💬 {text}",
        reply_to_message_id=mention_info["message_id"]
    )
    await update.message.reply_text("✅ 답변이 전송되었습니다!")