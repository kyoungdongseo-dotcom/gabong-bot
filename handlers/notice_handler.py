from telegram import Update
from telegram.ext import ContextTypes
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    msg = """안녕하세요! GAbong Bot입니다 🤖

📱 빠른 접근: /admin (관리자 대시보드)

━━━━━━━━━━━━━━━━━
📋 누구나 사용 가능
━━━━━━━━━━━━━━━━━
/help - 보고서 양식 안내 (인라인 버튼)
/myreports - 내 보고서 이력 (30일)
/reminder_stats - 내 리마인더 통계
/reminder_analysis - 내 리마인더 분석

📝 봉사보고서 자동 처리
- 봉사공유창 토픽에 양식 입력 시 자동 시트/Word 저장

━━━━━━━━━━━━━━━━━

📊 관리자 전용 — 리포트/점검
/weekly_ops - 주간 운영 리포트
/report_stats - 월간 보고서 통계
/status - 시스템 상태
/backup - 즉시 백업
/admin - 관리자 대시보드

📢 관리자 전용 — 공지
/notice [내용] - 총회봉교부 공지
/broadcast [내용] - 13개 그룹 일괄 공지
/add_group [id] - 봇 허용 그룹 추가
📎 사진/문서(PDF/Word/Excel) 캡션에 /broadcast 또는 /notice 입력 시 파일+텍스트 발송

📅 관리자 전용 — 일정
/schedule - 이번 주 봉사 일정
/weekly_report - 주간 일정 상세
/report - 주간 보고서 분석
/monthly - 월간 통계

🤖 관리자 전용 — AI 비서
/ai [질문] - AI에게 질문
/summary - 대화 요약
/reset - 대화 초기화
/mode [모드] - AI 모드 변경
/reply [내용] - 마지막 멘션에 답변

━━━━━━━━━━━━━━━━━

⭐공지 🔥교통 ❤홍보 👍대협 🙏소통 💯사공 👌진행

⏰ 리마인더 (총회봉교부)
/remind_daily HH:MM [내용]
/remind_weekly 월,수,금 HH:MM [내용]
/remind_biweekly 월 HH:MM [내용]
/remind_monthly 일자 HH:MM [내용]

⏰ 리마인더 (13개 그룹 전체)
/broadcast_remind_daily HH:MM [내용]
/broadcast_remind_weekly 월,수,금 HH:MM [내용]
/broadcast_remind_biweekly 월 HH:MM [내용]
/broadcast_remind_monthly 일자 HH:MM [내용]

/my_reminders - 리마인더 목록
/delete_reminder [ID] - 리마인더 삭제

📋 보고서 자동 처리
- 봉사보고서: 사진 + 형식 텍스트 → 자동 시트/Word 저장
- 수상보고서: 토픽 3553
- MOU 보고서: 토픽 3225
- 사진 1~10장 누적 가능
- /help 로 형식 확인"""
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

    if len(context.args) == 0:
        await update.message.reply_text("사용법: /notice [내용]")
        return
    # 원본 텍스트 보존 (줄바꿈/이중공백 유지) — 2026-05-15
    # context.args 는 split() 후 join 으로 줄바꿈 손실 → split(maxsplit=1) 로 명령어만 제거
    text = update.message.text.split(maxsplit=1)[1]
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

    if len(context.args) == 0:
        await update.message.reply_text("사용법: /broadcast [내용]")
        return
    # 원본 텍스트 보존 (줄바꿈/이중공백 유지) — 2026-05-15
    # context.args 는 split() 후 join 으로 줄바꿈 손실 → split(maxsplit=1) 로 명령어만 제거
    text = update.message.text.split(maxsplit=1)[1]
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

async def broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사진 + 캡션 /broadcast 또는 /notice 처리"""
    if not update.message or not update.message.photo:
        return

    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        return

    caption = update.message.caption or ""

    # /notice 처리
    if '/notice' in caption:
        caption = caption.replace('/notice', '').strip()
        GROUP_ID = config.get('group_id')
        TOPIC_ID = config.get('topic_id')
        try:
            await context.bot.send_photo(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_ID,
                photo=update.message.photo[-1].file_id,
                caption=f"📣 공지\n\n{caption}" if caption else "📣 공지"
            )
            await update.message.reply_text("✅ 사진 공지가 발송되었습니다.")
        except Exception as e:
            await update.message.reply_text(f"발송 실패: {e}")
        return

    # /broadcast 처리
    if '/broadcast' in caption:
        caption = caption.replace('/broadcast', '').strip()
        BROADCAST_GROUPS = config.get('broadcast_groups', [])
        success_count = 0
        fail_count = 0
        for group in BROADCAST_GROUPS:
            try:
                await context.bot.send_photo(
                    chat_id=group['id'],
                    message_thread_id=group.get('topic_id'),
                    photo=update.message.photo[-1].file_id,
                    caption=f"📣 공지\n\n{caption}" if caption else "📣 공지"
                )
                success_count += 1
            except Exception as e:
                print(f"❌ {group['name']} 발송 실패: {e}")
                fail_count += 1
        await update.message.reply_text(
            f"✅ {success_count}개 그룹 사진 공지 발송 완료!\n"
            f"{'❌ ' + str(fail_count) + '개 실패' if fail_count else ''}"
        )


async def broadcast_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """문서 파일 (PDF/Word/Excel 등) + 캡션 /broadcast 또는 /notice 처리.
    broadcast_photo 와 동일 패턴 — send_document 만 차이."""
    if not update.message or not update.message.document:
        return

    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        return

    caption = update.message.caption or ""

    # /notice 처리
    if '/notice' in caption:
        caption = caption.replace('/notice', '').strip()
        GROUP_ID = config.get('group_id')
        TOPIC_ID = config.get('topic_id')
        try:
            await context.bot.send_document(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_ID,
                document=update.message.document.file_id,
                caption=f"📣 공지\n\n{caption}" if caption else "📣 공지"
            )
            await update.message.reply_text("✅ 파일 공지가 발송되었습니다.")
        except Exception as e:
            await update.message.reply_text(f"발송 실패: {e}")
        return

    # /broadcast 처리
    if '/broadcast' in caption:
        caption = caption.replace('/broadcast', '').strip()
        BROADCAST_GROUPS = config.get('broadcast_groups', [])
        success_count = 0
        fail_count = 0
        for group in BROADCAST_GROUPS:
            try:
                await context.bot.send_document(
                    chat_id=group['id'],
                    message_thread_id=group.get('topic_id'),
                    document=update.message.document.file_id,
                    caption=f"📣 공지\n\n{caption}" if caption else "📣 공지"
                )
                success_count += 1
            except Exception as e:
                print(f"❌ {group['name']} 파일 발송 실패: {e}")
                fail_count += 1
        await update.message.reply_text(
            f"✅ {success_count}개 그룹 파일 공지 발송 완료!\n"
            f"{'❌ ' + str(fail_count) + '개 실패' if fail_count else ''}"
        )
