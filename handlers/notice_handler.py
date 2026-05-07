from telegram import Update
from telegram.ext import ContextTypes
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = """안녕하세요! GAbong Bot입니다 🤖
📢 공지
/notice [내용] - 총회봉교부 공지
/broadcast [내용] - 13개 그룹 일괄 공지

📅 주간 일정
/schedule - 이번 주 봉사 일정
/weekly_report - 주간 일정 상세 보고

🤖 AI 비서
/ai [질문] - AI에게 질문
/summary - 대화 요약
/reset - 대화 초기화
/reply [내용] - 마지막 멘션에 답변

⭐공지 🔥교통 ❤홍보 👍대협 🙏소통 💯사공 👌진행

⏰ 리마인더 (총회봉교부)
/remind_daily HH:MM [내용] - 매일
/remind_weekly 월,수,금 HH:MM [내용] - 매주
/remind_biweekly 월 HH:MM [내용] - 2주에 1번
/remind_monthly 일자 HH:MM [내용] - 매월

⏰ 리마인더 (13개 그룹 전체)
/broadcast_remind_daily HH:MM [내용] - 매일
/broadcast_remind_weekly 월,수,금 HH:MM [내용] - 매주
/broadcast_remind_biweekly 월 HH:MM [내용] - 2주에 1번
/broadcast_remind_monthly 일자 HH:MM [내용] - 매월

/my_reminders - 리마인더 목록
/delete_reminder ID - 리마인더 삭제

🎛 관리자 전용
/admin - 관리자 대시보드"""
    await update.message.reply_text(msg)

async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능합니다.")
        return

    GROUP_ID = config.get('group_id')
    TOPIC_ID = config.get('topic_id')

    # 사진 첨부 여부 확인
    photo = update.message.photo
    caption = update.message.caption or ""

    if photo:
        # 사진 + 캡션 공지
        try:
            await context.bot.send_photo(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_ID,
                photo=photo[-1].file_id,
                caption=f"📣 공지\n\n{caption}"
            )
            await update.message.reply_text("✅ 사진 공지가 발송되었습니다.")
        except Exception as e:
            await update.message.reply_text(f"발송 실패: {e}")
    else:
        # 텍스트만 공지
        if len(context.args) == 0:
            await update.message.reply_text("사용법: /notice [내용] 또는 사진+캡션으로 /notice")
            return
        text = " ".join(context.args)
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_ID,
                text=f"📣 공지\n\n{text}"
            )
            await update.message.reply_text("✅ 공지가 발송되었습니다.")
        except Exception as e:
            await update.message.reply_text(f"발송 실패: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("관리자만 사용 가능합니다.")
        return

    BROADCAST_GROUPS = config.get('broadcast_groups', [])

    # 사진 첨부 여부 확인
    photo = update.message.photo
    caption = update.message.caption or ""

    if photo:
        # 사진 + 캡션 broadcast
        success_count = 0
        fail_count = 0
        for group in BROADCAST_GROUPS:
            try:
                await context.bot.send_photo(
                    chat_id=group['id'],
                    message_thread_id=group.get('topic_id'),
                    photo=photo[-1].file_id,
                    caption=f"📣 공지\n\n{caption}"
                )
                success_count += 1
            except Exception as e:
                print(f"❌ {group['name']} 발송 실패: {e}")
                fail_count += 1
        await update.message.reply_text(
            f"✅ {success_count}개 그룹 사진 공지 발송 완료!\n"
            f"{'❌ ' + str(fail_count) + '개 실패' if fail_count else ''}"
        )
    else:
        # 텍스트만 broadcast
        if len(context.args) == 0:
            await update.message.reply_text("사용법: /broadcast [내용] 또는 사진+캡션으로 /broadcast")
            return
        text = " ".join(context.args)
        success_count = 0
        fail_count = 0
        for group in BROADCAST_GROUPS:
            try:
                await context.bot.send_message(
                    chat_id=group['id'],
                    message_thread_id=group.get('topic_id'),
                    text=f"📣 공지\n\n{text}"
                )
                success_count += 1
            except Exception as e:
                print(f"❌ {group['name']} 발송 실패: {e}")
                fail_count += 1
        await update.message.reply_text(
            f"✅ {success_count}개 그룹 공지 발송 완료!\n"
            f"{'❌ ' + str(fail_count) + '개 실패' if fail_count else ''}"
        )
