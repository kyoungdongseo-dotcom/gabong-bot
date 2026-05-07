from telegram import Update
from telegram.ext import ContextTypes
import config
from utils import ask_claude, get_chat_mode, log_message, CHAT_HISTORY, GROUP_MESSAGES, LAST_MENTION
from handlers.report_parser import parse_report, save_report_to_sheet
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

AUTHORIZED_USERS = {
    414481241,
    5242761926,
    1104086017,
    1062746453,
    754270008,
}

REPORT_GROUP_ID = -1002777848839

def get_sheet_service():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    return build('sheets', 'v4', credentials=creds)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_user.id == config.get('bot_user_id'):
        return
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    text = update.message.text
    thread_id = update.message.message_thread_id
    print(f"그룹 ID: {chat_id} | 토픽 ID: {thread_id} | 그룹명: {update.message.chat.title} | 메시지: {text}")

    log_message(chat_id, user_id, user_name, "user", text, thread_id)
    if chat_id not in GROUP_MESSAGES:
        GROUP_MESSAGES[chat_id] = []
    GROUP_MESSAGES[chat_id].append(f"{user_name}: {text}")
    if len(GROUP_MESSAGES[chat_id]) > 100:
        GROUP_MESSAGES[chat_id] = GROUP_MESSAGES[chat_id][-100:]

    # ✅ 봉사보고서 자동 파싱 (12지파 사공대협 업무공유창)
    if chat_id == REPORT_GROUP_ID:
        report = parse_report(text)
        if report:
            try:
                service = get_sheet_service()
                spreadsheet_id = config.get('spreadsheet_id')
                success = save_report_to_sheet(report, service, spreadsheet_id)
                if success:
                    await update.message.reply_text(
                        f"✅ 봉사보고서 자동 저장 완료!\n"
                        f"📌 {report.get('지파명')} {report.get('교회명')}\n"
                        f"📋 {report.get('활동명')}\n"
                        f"👥 총 봉사자: {report.get('총봉사자')}명"
                    )
            except Exception as e:
                print(f"❌ 보고서 저장 오류: {e}")

    MY_KEYWORDS = config.get('my_keywords')
    my_keyword_found = any(kw in text for kw in MY_KEYWORDS)
    if my_keyword_found and update.effective_user.id != config.get('my_user_id'):
        group_name = update.message.chat.title or "그룹"
        sender = update.effective_user.first_name
        LAST_MENTION[config.get('my_user_id')] = {
            "chat_id": chat_id,
            "message_id": update.message.message_id
        }
        await context.bot.send_message(
            chat_id=config.get('my_user_id'),
            text=f"📣 멘션/호출 알림!\n\n그룹: {group_name}\n보낸 사람: {sender}\n내용: {text}\n\n답변하려면: /reply [내용]"
        )

    MENTION_KEYWORDS = config.get('mention_keywords')
    EXCLUDE_GROUPS = config.get('exclude_groups')
    TOPIC_IDS = config.get('topic_ids')
    for keyword, topic_name in MENTION_KEYWORDS.items():
        if keyword in text and update.effective_user.id not in AUTHORIZED_USERS and chat_id not in EXCLUDE_GROUPS:
            group_name = update.message.chat.title or "그룹"
            sender = update.effective_user.first_name
            topic_id = TOPIC_IDS[topic_name]
            await context.bot.send_message(
                chat_id=config.get('group_id'),
                message_thread_id=topic_id,
                text=f"📣 멘션 알림!\n\n그룹: {group_name}\n보낸 사람: {sender}\n내용: {text}"
            )
            break

    bot_username = context.bot.username
    if f"@{bot_username}" in text:
        question = text.replace(f"@{bot_username}", "").strip()
        if not question:
            return
        if "요약" in question and GROUP_MESSAGES.get(chat_id):
            history = "\n".join(GROUP_MESSAGES[chat_id])
            question = f"다음 대화를 한국어로 요약해주세요:\n{history}"
        mode = get_chat_mode(chat_id)
        await update.message.reply_text("🤖 AI가 답변 중입니다...")
        import asyncio
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, ask_claude, question, chat_id, user_id, user_name, thread_id, mode)
        await update.message.reply_text(f"🤖 AI 답변\n\n{answer}")
