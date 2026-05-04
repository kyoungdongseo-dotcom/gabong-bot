from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = "안녕하세요! GAbong Bot입니다 🤖\n\n📢 공지\n/notice [내용] - 총회봉교부 공지\n/broadcast [내용] - 13개 그룹 일괄 공지\n\n🤖 AI 비서\n/ai [질문] - AI에게 질문\n/summary - 대화 요약\n/reset - 대화 초기화\n/reply [내용] - 마지막 멘션에 답변\n\n⭐공지 🔥교통 ❤홍보 👍대협 🙏소통 💯사공 👌진행\n\n⏰ 리마인더 (총회봉교부)\n/remind_daily HH:MM [내용] - 매일\n/remind_weekly 월,수,금 HH:MM [내용] - 매주\n/remind_biweekly 월 HH:MM [내용] - 2주에 1번\n/remind_monthly 일자 HH:MM [내용] - 매월\n\n⏰ 리마인더 (13개 그룹 전체)\n/broadcast_remind_daily HH:MM [내용] - 매일\n/broadcast_remind_weekly 월,수,금 HH:MM [내용] - 매주\n/broadcast_remind_biweekly 월 HH:MM [내용] - 2주에 1번\n/broadcast_remind_monthly 일자 HH:MM [내용] - 매월\n\n/my_reminders - 리마인더 목록\n/delete_reminder ID - 리마인더 삭제"
    await update.message.reply_text(msg)

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 공지 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    text = update.message.text.split("/notice ", 1)[1]
    GROUP_ID = config.get('group_id')
    TOPIC_ID = config.get('topic_id')
    await context.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=f"📢 공지사항\n\n{text}")
    await update.message.reply_text("✅ 공지가 전송되었습니다!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /broadcast [내용]")
        return
    text = update.message.text.split("/broadcast ", 1)[1]
    await update.message.reply_text("📢 일괄 공지 전송 중...")
    BROADCAST_GROUPS = config.get('broadcast_groups')
    success = 0
    fail = 0
    for group in BROADCAST_GROUPS:
        try:
            await context.bot.send_message(
                chat_id=group["id"],
                message_thread_id=group["topic_id"],
                text=f"📢 공지사항\n\n{text}"
            )
            success += 1
        except Exception as e:
            print(f"전송 실패 {group['name']}: {e}")
            fail += 1
    await update.message.reply_text(f"✅ 전송 완료!\n성공: {success}개\n실패: {fail}개")

def register(app, config):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("notice", notice))
    app.add_handler(CommandHandler("broadcast", broadcast))