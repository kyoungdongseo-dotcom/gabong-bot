from telegram import Update
from utils.permissions import check_admin
from telegram.ext import ContextTypes
import asyncio
import config
from utils import ask_claude, get_chat_history, clear_chat_history, get_chat_mode, CHAT_HISTORY, GROUP_MESSAGES

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    if chat_id < 0:
        allowed_groups = config.get('allowed_groups') or []
        if allowed_groups and chat_id not in allowed_groups:
            await update.message.reply_text("❌ 이 그룹에서는 /ai를 사용할 수 없습니다.")
            return
    if not await check_admin(update, context):
        return
    if not context.args:
        await update.message.reply_text("사용법: /ai [질문]")
        return
    args_text = update.message.text.split(" ", 1)
    if len(args_text) < 2:
        await update.message.reply_text("사용법: /ai [질문]")
        return
    question = args_text[1]
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    thread_id = update.message.message_thread_id
    mode = get_chat_mode(chat_id)
    await update.message.reply_text("🤖 AI가 답변 중입니다...")
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(None, ask_claude, question, chat_id, user_id, user_name, thread_id, mode)
    await update.message.reply_text(f"🤖 AI 답변\n\n{answer}")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await check_admin(update, context):
        return
    chat_id = update.effective_chat.id
    history = get_chat_history(chat_id, limit=50)
    if not history:
        await update.message.reply_text("대화 내역이 없습니다.")
        return
    history_text = ""
    for msg in history:
        role = "나" if msg["role"] == "user" else "AI"
        history_text += f"{role}: {msg['content']}\n"
    question = f"다음 대화를 한국어로 요약해주세요:\n{history_text}"
    await update.message.reply_text("🤖 요약 중입니다...")
    mode = get_chat_mode(chat_id)
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(None, ask_claude, question, chat_id, update.effective_user.id, update.effective_user.first_name, update.message.message_thread_id, mode)
    await update.message.reply_text(f"📝 대화 요약\n\n{answer}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await check_admin(update, context):
        return
    chat_id = update.effective_chat.id
    if chat_id in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    if chat_id in GROUP_MESSAGES:
        GROUP_MESSAGES[chat_id] = []
    clear_chat_history(chat_id)
    await update.message.reply_text("✅ 대화 내역이 초기화되었습니다!")