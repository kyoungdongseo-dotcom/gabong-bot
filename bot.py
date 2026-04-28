import gspread
import asyncio
import json
import os
from datetime import datetime
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8740092962:AAEheWkRrOYDSJLFpvkOQdq3X-gaYAV_Vjc"
GROUP_ID = -1002363981206
TOPIC_ID = 2
ADMIN_IDS = [97057565]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_ID = "1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4"
CACHE_FILE = "/data/sheet_cache.json"
REMINDERS_FILE ="/data/reminders.json"

scheduler = AsyncIOScheduler()

def get_sheet_data():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet.get_all_values()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, ensure_ascii=False)

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
    msg = """안녕하세요! GAbong Bot입니다 🤖

📢 공지
/notice [내용] - 공지 전송 (관리자)

⏰ 리마인더
/remind_daily HH:MM [내용] - 매일 알림
/remind_weekly 월,수,금 HH:MM [내용] - 매주 알림
/remind_monthly 일자 HH:MM [내용] - 매월 알림

/my_reminders - 내 리마인더 목록
/delete_reminder ID - 리마인더 삭제"""
    await update.message.reply_text(msg)

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ 공지 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    text = update.message.text.split("/notice ", 1)[1]
    msg = f"📢 공지사항\n\n{text}"
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
    await update.message.reply_text("✅ 공지가 전송되었습니다!")

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    rows = get_sheet_data()
    msg = "📋 업무 현황\n\n"
    for row in rows[4:9]:
        if row[0]:
            msg += f"• {row[0]} | {row[1]} | {row[2]}\n"
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
    await update.message.reply_text("✅ 업무 현황이 전송되었습니다!")

async def remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /remind_daily HH:MM [내용]\n예: /remind_daily 09:00 아침 업무 시작")
        return
    time_str = context.args[0]
    text = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminder = {"id": reminder_id, "type": "daily", "time": time_str, "text": text, "chat_id": chat_id}
    reminders.append(reminder)
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매일 {time_str}에 '{text}' 알림이 등록되었습니다! (ID: {reminder_id})")

async def remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_weekly 월,수,금 HH:MM [내용]\n예: /remind_weekly 월,수 10:00 주간 회의")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = " ".join(context.args[2:])
    chat_id = update.effective_chat.id
    day_map = {"월": "mon", "화": "tue", "수": "wed", "목": "thu", "금": "fri", "토": "sat", "일": "sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminder = {"id": reminder_id, "type": "weekly", "days": days_str, "time": time_str, "text": text, "chat_id": chat_id}
    reminders.append(reminder)
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 '{text}' 알림이 등록되었습니다! (ID: {reminder_id})")

async def remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_monthly 일자 HH:MM [내용]\n예: /remind_monthly 25 14:00 보고서 제출")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = " ".join(context.args[2:])
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminder = {"id": reminder_id, "type": "monthly", "day": day, "time": time_str, "text": text, "chat_id": chat_id}
    reminders.append(reminder)
    save_reminders(reminders)
    scheduler.add_job(send_reminder, 'cron', day=day, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 '{text}' 알림이 등록되었습니다! (ID: {reminder_id})")

async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reminders = [r for r in load_reminders() if r["chat_id"] == chat_id]
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
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder [ID]")
        return
    reminder_id = context.args[0]
    reminders = load_reminders()
    reminders = [r for r in reminders if str(r["id"]) != reminder_id]
    save_reminders(reminders)
    try:
        scheduler.remove_job(reminder_id)
    except:
        pass
    await update.message.reply_text(f"✅ 리마인더 {reminder_id}가 삭제되었습니다!")

async def send_reminder(bot, chat_id, text):
    await bot.send_message(chat_id=chat_id, text=f"⏰ 리마인더\n\n{text}")

async def post_init(app):
    scheduler.start()
    reminders = load_reminders()
    for r in reminders:
        try:
            hour, minute = map(int, r["time"].split(":"))
            if r["type"] == "daily":
                scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "weekly":
                day_map = {"월": "mon", "화": "tue", "수": "wed", "목": "thu", "금": "fri", "토": "sat", "일": "sun"}
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
app.add_handler(CommandHandler("remind_daily", remind_daily))
app.add_handler(CommandHandler("remind_weekly", remind_weekly))
app.add_handler(CommandHandler("remind_monthly", remind_monthly))
app.add_handler(CommandHandler("my_reminders", my_reminders))
app.add_handler(CommandHandler("delete_reminder", delete_reminder))

print("봇 시작!")
app.run_polling()
