from telegram import Update
from telegram.ext import ContextTypes
import config
from utils import get_sheet_data

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    rows = get_sheet_data()
    msg = "📋 업무 현황\n\n"
    for row in rows[4:9]:
        if row[0]:
            msg += f"• {row[0]} | {row[1]} | {row[2]}\n"
    GROUP_ID = config.get('group_id')
    TOPIC_ID = config.get('topic_id')
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
    await update.message.reply_text("✅ 업무 현황이 전송되었습니다!")