import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "8528876168:AAFGrNSFEPnBnfuEG1a2Pf4czCts***REVOKED***"

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.message_thread_id:
        print(f"토픽 ID: {update.message.message_thread_id} | 채팅: {update.message.chat.title} | 메시지: {update.message.text}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, check))
print("토픽 ID 확인 중...")
app.run_polling()
