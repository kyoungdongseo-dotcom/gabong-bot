import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8740092962:AAHnR-u7qcWyhQdIC9tVvCbh41pEBFavu58"
GROUP_ID = -1002363981206
TOPIC_ID = 2
ADMIN_IDS = [97057565]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SPREADSHEET_NAME = "총회 봉사교통부 진행 업무 현황표"

def get_sheet_data():
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    rows = sheet.get_all_values()
    return rows

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

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("notice", notice))
app.add_handler(CommandHandler("sheet", sheet))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

print("봇 시작!")
app.run_polling()
