from datetime import datetime, timedelta
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
import config
from utils import (
    ask_claude,
    get_chat_history,
    fetch_weekly_messages,
    get_chat_mode,
    set_chat_mode,
    log_message,
)


def _get_week_start():
    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _build_history_text(history):
    if not history:
        return ""
    lines = []
    for msg in history:
        if msg.get("role") == "assistant":
            lines.append(f"AI: {msg['content']}")
        else:
            lines.append(f"사용자: {msg['content']}")
    return "\n".join(lines)


def _build_weekly_prompt(messages, group_name=None):
    title = f"{group_name}의 주간 보고서" if group_name else "주간 보고서"
    history_text = "\n".join(
        [f"[{item['timestamp']}] {item['user_name'] or '사용자'}: {item['text']}" for item in messages]
    )
    return (
        f"다음은 {title}에 대한 이번 주 대화 기록입니다. 아래 항목에 따라 한국어로 정리해주세요:\n"
        "1. 이번 주 주요 업무\n"
        "2. 논의된 이슈\n"
        "3. 다음주 계획\n\n"
        f"대화 기록:\n{history_text}"
    )


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        available = ", ".join(config.get('role_prompt_modes', {}).keys())
        await update.message.reply_text(f"사용 가능한 모드: {available}\n사용법: /mode [meeting|proposal|checklist]")
        return

    selected_mode = context.args[0].strip().lower()
    available = config.get('role_prompt_modes', {}) or {}
    if selected_mode not in available:
        await update.message.reply_text(
            f"유효하지 않은 모드입니다. 사용 가능한 모드: {', '.join(available.keys())}"
        )
        return

    chat_id = update.effective_chat.id
    set_chat_mode(chat_id, selected_mode)
    await update.message.reply_text(
        f"✅ 모드가 '{selected_mode}'(으)로 설정되었습니다. 이제부터 해당 역할에 맞는 AI 응답을 제공합니다."
    )


async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    thread_id = update.message.message_thread_id

    since = _get_week_start()
    messages = fetch_weekly_messages(chat_id, since)
    if not messages:
        await update.message.reply_text("이번 주에 기록된 대화가 없습니다.")
        return

    prompt = _build_weekly_prompt(messages, update.effective_chat.title)
    await update.message.reply_text("🤖 주간 보고서를 생성 중입니다...")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None,
        ask_claude,
        prompt,
        chat_id,
        user_id,
        user_name,
        thread_id,
        get_chat_mode(chat_id),
    )
    await update.message.reply_text(f"📊 주간 보고서\n\n{answer}")


async def summary_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    thread_id = update.message.message_thread_id

    history = get_chat_history(chat_id, limit=100)
    if not history:
        await update.message.reply_text("대화 내역이 없습니다.")
        return

    history_text = _build_history_text(history)
    question = f"다음 대화를 아주 상세히 한국어로 요약하고, 주요 결정 사항과 액션 항목을 정리해주세요:\n{history_text}"
    await update.message.reply_text("🤖 상세 요약을 생성 중입니다...")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None,
        ask_claude,
        question,
        chat_id,
        user_id,
        user_name,
        thread_id,
        get_chat_mode(chat_id),
    )
    await update.message.reply_text(f"📝 상세 요약\n\n{answer}")


async def summary_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    thread_id = update.message.message_thread_id

    history = get_chat_history(chat_id, limit=100)
    if not history:
        await update.message.reply_text("대화 내역이 없습니다.")
        return

    history_text = _build_history_text(history)
    question = f"다음 대화를 간단하고 명확하게 한국어로 요약해 주세요. 핵심 내용만 포함하세요:\n{history_text}"
    await update.message.reply_text("🤖 간단 요약을 생성 중입니다...")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None,
        ask_claude,
        question,
        chat_id,
        user_id,
        user_name,
        thread_id,
        get_chat_mode(chat_id),
    )
    await update.message.reply_text(f"📝 간단 요약\n\n{answer}")


async def send_weekly_report_job(bot):
    summary_groups = config.get('summary_groups') or {}
    target_user_id = config.get('my_user_id')
    if not summary_groups or not target_user_id:
        return

    since = _get_week_start()
    for group_id_str, group_name in summary_groups.items():
        try:
            group_id = int(group_id_str)
        except ValueError:
            continue

        messages = fetch_weekly_messages(group_id, since)
        if not messages:
            continue

        prompt = _build_weekly_prompt(messages, group_name)
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            ask_claude,
            prompt,
            group_id,
            None,
            None,
            None,
            None,
        )
        await bot.send_message(
            chat_id=target_user_id,
            text=f"📅 자동 주간 보고서 - {group_name}\n\n{answer}"
        )
