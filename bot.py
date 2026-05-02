import gspread
import asyncio
import json
import os
import anthropic
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, MessageReactionHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8528876168:AAFGrNSFEPnBnfuEG1a2Pf4czCts***REVOKED***"
GROUP_ID = -1002363981206
TOPIC_ID = 2
ADMIN_IDS = [97057565]
MY_USER_ID = 97057565
MY_USERNAME = "gamdongwon"

TOPIC_IDS = {
    "홍보": 19116,
    "교통": 5,
    "대협": 19118,
    "사공": 4,
    "공지": 2,
    "소통": 3
}

REACTION_TOPICS = {
    "⭐": 2,
    "🔥": 5,
    "❤": 19116,
    "👍": 19118,
    "🙏": 3,
    "💯": 4,
}

REPLY_REACTIONS = {
    "👌": "네 진행 부탁드립니다."
}

MENTION_KEYWORDS = {
    "사공과장": "사공",
    "사공과장님": "사공",
    "교통과장": "교통",
    "교통과장님": "교통",
    "서무님": "소통",
    "대협과장님": "대협",
    "홍보과장": "홍보",
    "홍보과장님": "홍보",
    "과장님": "소통",
    "@msy3315": "대협",
    "@ahjak33": "소통",
    "@Siwal21": "홍보",
    "@yyjunnn": "교통",
    "지연": "사공",
    "예산": "교통",
    "행사": "교통",
}

MY_KEYWORDS = ["@gamdongwon", "부장님", "부장", "봉교부장님", "봉사교통부장님"]

EXCLUDE_GROUPS = [
    -1002363981206,
    -1002244990837,
    -1002162878310,
    -1002243480896,
    -1001972104172,
    -1001804969266,
    -1003546102596,
    -1003575758123,
    -1002582559428,
    -1002529584022,
    -1001525503443,
    -1002237080198,
]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_ID = "1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4"
CACHE_FILE = "/data/sheet_cache.json"
REMINDERS_FILE = "/data/reminders.json"
CHAT_HISTORY = {}
GROUP_MESSAGES = {}
LAST_MENTION = {}
scheduler = AsyncIOScheduler()

claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = "당신은 총회 봉사교통부의 AI 비서입니다. 반드시 한국어로만 답변하세요. 친절하고 전문적으로 답변하세요. 회의록 작성, 공문 초안, 업무 체크리스트, 아이디어 제안, 대화 요약 등 업무를 도와주세요. 답변은 간결하고 명확하게 해주세요. 확실하지 않은 정보는 모른다고 솔직하게 말하세요."

def ask_claude(question, chat_id=None):
    try:
        messages = []
        if chat_id and chat_id in CHAT_HISTORY:
            messages = CHAT_HISTORY[chat_id][-10:]
        messages.append({"role": "user", "content": question})
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        answer = response.content[0].text
        if chat_id:
            if chat_id not in CHAT_HISTORY:
                CHAT_HISTORY[chat_id] = []
            CHAT_HISTORY[chat_id].append({"role": "user", "content": question})
            CHAT_HISTORY[chat_id].append({"role": "assistant", "content": answer})
            if len(CHAT_HISTORY[chat_id]) > 20:
                CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-20:]
        return answer
    except Exception as e:
        print(f"Claude API 오류: {e}")
        return "죄송합니다. AI 답변 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

def get_sheet_data():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1.get_all_values()

def load_cache():
    os.makedirs("/data", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data):
    os.makedirs("/data", exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def load_reminders():
    os.makedirs("/data", exist_ok=True)
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)
                return [r for r in data if isinstance(r, dict) and "chat_id" in r]
        except:
            return []
    return []

def save_reminders(reminders):
    os.makedirs("/data", exist_ok=True)
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, ensure_ascii=False)

async def send_reminder(bot, chat_id, text):
    await bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=f"⏰ 리마인더\n\n{text}")

async def check_changes(app):
    while True:
        try:
            rows = get_sheet_data()
            cache = load_cache()
            new_cache = {}
            for i, row in enumerate(rows[4:9]):
                key = str(i)
                row_str = str(row)
                new_cache[key] = row_str
                if key in cache and cache[key] != row_str and row[0]:
                    msg = f"📋 업무 현황 변경!\n\n과명: {row[0]}\n회의 일자: {row[1]}\n회의 안건: {row[2]}\n금주 진행 일정: {row[8]}\n금주 진행 현황: {row[9]}"
                    await app.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
            save_cache(new_cache)
        except Exception as e:
            print(f"오류: {e}")
        await asyncio.sleep(60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = "안녕하세요! GAbong Bot입니다 🤖\n\n📢 공지\n/notice [내용] - 공지 전송 (관리자)\n\n🤖 AI 비서\n/ai [질문] - AI에게 질문\n/summary - 대화 요약\n/reset - 대화 초기화\n/reply [내용] - 마지막 멘션에 답변\n\n⭐공지 🔥교통 ❤홍보 👍대협 🙏소통 💯사공 👌진행\n이모티콘 반응으로 해당 토픽에 메시지 전달!\n\n⏰ 리마인더\n/remind_daily HH:MM [내용] - 매일 알림\n/remind_weekly 월,수,금 HH:MM [내용] - 매주 알림\n/remind_monthly 일자 HH:MM [내용] - 매월 알림\n\n/my_reminders - 내 리마인더 목록\n/delete_reminder ID - 리마인더 삭제"
    await update.message.reply_text(msg)

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 공지 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    text = update.message.text.split("/notice ", 1)[1]
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=f"📢 공지사항\n\n{text}")
    await update.message.reply_text("✅ 공지가 전송되었습니다!")

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    rows = get_sheet_data()
    msg = "📋 업무 현황\n\n"
    for row in rows[4:9]:
        if row[0]:
            msg += f"• {row[0]} | {row[1]} | {row[2]}\n"
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
    await update.message.reply_text("✅ 업무 현황이 전송되었습니다!")

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("사용법: /ai [질문]")
        return
    question = update.message.text.split("/ai ", 1)[1] if "/ai " in update.message.text else ""
if not question:
    await update.message.reply_text("사용법: /ai [질문]")
    return
    chat_id = update.effective_chat.id
    await update.message.reply_text("🤖 AI가 답변 중입니다...")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, ask_claude, question, chat_id)
    await update.message.reply_text(f"🤖 AI 답변\n\n{answer}")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    if chat_id not in CHAT_HISTORY or not CHAT_HISTORY[chat_id]:
        await update.message.reply_text("대화 내역이 없습니다.")
        return
    history_text = ""
    for msg in CHAT_HISTORY[chat_id]:
        role = "나" if msg["role"] == "user" else "AI"
        history_text += f"{role}: {msg['content']}\n"
    question = f"다음 대화를 한국어로 요약해주세요:\n{history_text}"
    await update.message.reply_text("🤖 요약 중입니다...")
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(None, ask_claude, question, None)
    await update.message.reply_text(f"📝 대화 요약\n\n{answer}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    if chat_id in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    if chat_id in GROUP_MESSAGES:
        GROUP_MESSAGES[chat_id] = []
    await update.message.reply_text("✅ 대화 내역이 초기화되었습니다!")

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
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

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"반응 이벤트 받음!")
    if not update.message_reaction:
        return
    reaction = update.message_reaction
    if reaction.user.id != MY_USER_ID:
        return
    for r in reaction.new_reaction:
        emoji = r.emoji
        print(f"이모티콘: {emoji}")
        if emoji in REACTION_TOPICS:
            topic_id = REACTION_TOPICS[emoji]
            try:
                await context.bot.forward_message(
                    chat_id=GROUP_ID,
                    message_thread_id=topic_id,
                    from_chat_id=reaction.chat.id,
                    message_id=reaction.message_id
                )
                print(f"전달 성공: {emoji} -> 토픽 {topic_id}")
            except Exception as e:
                print(f"전달 오류: {e}")
        if emoji in REPLY_REACTIONS:
            try:
                await context.bot.send_message(
                    chat_id=reaction.chat.id,
                    text=REPLY_REACTIONS[emoji],
                    reply_to_message_id=reaction.message_id
                )
                print(f"답장 성공: {emoji}")
            except Exception as e:
                print(f"답장 오류: {e}")

async def remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /remind_daily HH:MM [내용]")
        return
    time_str = context.args[0]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "daily", "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매일 {time_str}에 알림 등록! (ID: {reminder_id})")

async def remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_weekly 월,수,금 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "weekly", "days": days_str, "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 알림 등록! (ID: {reminder_id})")

async def remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_monthly 일자 HH:MM [내용]")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "monthly", "day": day, "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', day=day, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 알림 등록! (ID: {reminder_id})")

async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    reminders = [r for r in load_reminders() if r.get("chat_id") == chat_id]
    if not reminders:
        await update.message.reply_text("등록된 리마인더가 없습니다.")
        return
    msg = "⏰ 내 리마인더 목록\n\n"
    for r in reminders:
        if r["type"] == "daily":
            msg += f"ID {r['id']}: 매일 {r['time']} - {r['text']}\n"
        elif r["type"] == "weekly":
            msg += f"ID {r['id']}: 매주 {r['days']} {r['time']} - {r['text']}\n"
        elif r["type"] == "monthly":
            msg += f"ID {r['id']}: 매월 {r['day']}일 {r['time']} - {r['text']}\n"
    await update.message.reply_text(msg)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder [ID]")
        return
    reminder_id = context.args[0]
    reminders = [r for r in load_reminders() if str(r["id"]) != reminder_id]
    save_reminders(reminders)
    try:
        scheduler.remove_job(reminder_id)
    except:
        pass
    await update.message.reply_text(f"✅ 리마인더 {reminder_id} 삭제 완료!")

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    text = update.message.text
    print(f"그룹 ID: {chat_id} | 그룹명: {update.message.chat.title} | 메시지: {text}")

    if chat_id not in GROUP_MESSAGES:
        GROUP_MESSAGES[chat_id] = []
    GROUP_MESSAGES[chat_id].append(f"{user_name}: {text}")
    if len(GROUP_MESSAGES[chat_id]) > 100:
        GROUP_MESSAGES[chat_id] = GROUP_MESSAGES[chat_id][-100:]

    my_keyword_found = any(kw in text for kw in MY_KEYWORDS)
    if my_keyword_found and update.effective_user.id != MY_USER_ID:
        group_name = update.message.chat.title or "그룹"
        sender = update.effective_user.first_name
        LAST_MENTION[MY_USER_ID] = {
            "chat_id": chat_id,
            "message_id": update.message.message_id
        }
        await context.bot.send_message(
            chat_id=MY_USER_ID,
            text=f"📣 멘션/호출 알림!\n\n그룹: {group_name}\n보낸 사람: {sender}\n내용: {text}\n\n답변하려면: /reply [내용]"
        )

    for keyword, topic_name in MENTION_KEYWORDS.items():
        if keyword in text and update.effective_user.id != MY_USER_ID and chat_id not in EXCLUDE_GROUPS:
            group_name = update.message.chat.title or "그룹"
            sender = update.effective_user.first_name
            topic_id = TOPIC_IDS[topic_name]
            await context.bot.send_message(
                chat_id=GROUP_ID,
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
        await update.message.reply_text("🤖 AI가 답변 중입니다...")
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, ask_claude, question, chat_id)
        await update.message.reply_text(f"🤖 AI 답변\n\n{answer}")

async def post_init(app):
    scheduler.start()
    for r in load_reminders():
        try:
            hour, minute = map(int, r["time"].split(":"))
            if r["type"] == "daily":
                scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "weekly":
                day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                days = ",".join([day_map[d] for d in r["days"].split(",")])
                scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "monthly":
                scheduler.add_job(send_reminder, 'cron', day=r["day"], hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
        except:
            pass
    asyncio.create_task(check_changes(app))

app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("notice", notice))
app.add_handler(CommandHandler("sheet", sheet))
app.add_handler(CommandHandler("ai", ai_command))
app.add_handler(CommandHandler("summary", summary))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("reply", reply_command))
app.add_handler(CommandHandler("remind_daily", remind_daily))
app.add_handler(CommandHandler("remind_weekly", remind_weekly))
app.add_handler(CommandHandler("remind_monthly", remind_monthly))
app.add_handler(CommandHandler("my_reminders", my_reminders))
app.add_handler(CommandHandler("delete_reminder", delete_reminder))
app.add_handler(MessageReactionHandler(handle_reaction))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))

print("봇 시작!")
app.run_polling(allowed_updates=["message", "message_reaction"])
