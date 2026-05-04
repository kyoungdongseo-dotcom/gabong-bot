import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "8528876168:AAFGrNSFEPnBnfuEG1a2Pf4czCts***REVOKED***"

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        print(f"그룹 ID: {update.message.chat.id} | 그룹명: {update.message.chat.title} | 메시지: {update.message.text}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, check))
print("그룹 ID 확인 중...")
app.run_polling()
