import gspread
import asyncio
import json
import os
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8740092962:AAEheWkRrOYDSJLFpvkOQdq3X-gaYAV_Vjc"
GROUP_ID = -1002363981206
TOPIC_ID = 2
ADMIN_IDS = [97057565]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_ID = "1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4"
CACHE_FILE = "sheet_cache.json"

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
    await update.message.reply_text("안녕하세요! GAbong Bot입니다 🤖")

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ 공지 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    text = " ".join(context.args)
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


async def post_init(app):
    asyncio.create_task(check_changes(app))

app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("notice", notice))
app.add_handler(CommandHandler("sheet", sheet))

print("봇 시작!")
app.run_polling()
