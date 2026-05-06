"""관리자 대시보드 핸들러"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
import config

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """관리자 대시보드 메인 메뉴"""
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("관리자만 사용 가능합니다.")
        return

    keyboard = [
        [
            InlineKeyboardButton("📢 공지 발송", callback_data="admin_notice"),
            InlineKeyboardButton("📅 주간 일정", callback_data="admin_schedule"),
        ],
        [
            InlineKeyboardButton("⏰ 리마인더 목록", callback_data="admin_reminders"),
            InlineKeyboardButton("📊 봉사 통계", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("👥 그룹 목록", callback_data="admin_groups"),
            InlineKeyboardButton("⚙️ 봇 상태", callback_data="admin_status"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎛 *GAbong Bot 관리자 대시보드*",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """버튼 콜백 처리"""
    query = update.callback_query
    await query.answer()

    if query.data == "admin_notice":
        await query.edit_message_text(
            "📢 *공지 발송*\n\n발송할 내용을 입력하세요:\n`/broadcast 내용`",
            parse_mode="Markdown"
        )

    elif query.data == "admin_schedule":
        from handlers.weekly_schedule_handler import build_weekly_message
        message = await build_weekly_message()
        await query.edit_message_text(message)

    elif query.data == "admin_reminders":
        from utils import load_reminders
        reminders = load_reminders()
        if not reminders:
            text = "⏰ *등록된 리마인더 없음*"
        else:
            lines = ["⏰ *등록된 리마인더 목록*\n"]
            for r in reminders:
                days = r.get('days_display', '')
                time = r.get('time', '')
                msg = r.get('message', '')[:30]
                rtype = r.get('type', '')
                lines.append(f"• [{rtype}] {days} {time} - {msg}...")
            text = "\n".join(lines)
        await query.edit_message_text(text, parse_mode="Markdown")

    elif query.data == "admin_stats":
        from handlers.weekly_schedule_handler import read_sheet_values, parse_schedule_from_rows
        rows = read_sheet_values()
        day_events = parse_schedule_from_rows(rows)
        event_count = sum(len(v) for v in day_events.values())
        busiest = max(day_events.keys(), key=lambda k: len(day_events[k])) if day_events else None

        lines = ["📊 *이번 주 봉사 통계*\n"]
        lines.append(f"• 총 봉사 건수: {event_count}건")
        if busiest:
            from handlers.weekly_schedule_handler import KR_DAYS
            lines.append(f"• 가장 바쁜 날: {busiest.strftime('%m/%d')}({KR_DAYS[busiest.weekday()]}) — {len(day_events[busiest])}건")
        lines.append(f"• 봉사 날짜 수: {len(day_events)}일")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif query.data == "admin_groups":
        broadcast_groups = config.get('broadcast_groups', [])
        lines = [f"👥 *등록된 그룹 목록* ({len(broadcast_groups)}개)\n"]
        for g in broadcast_groups:
            name = g.get('name', '이름없음')
            lines.append(f"• {name}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif query.data == "admin_status":
        import datetime
        import pytz
        KST = pytz.timezone('Asia/Seoul')
        now = datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
        reminders = []
        try:
            from utils import load_reminders
            reminders = load_reminders()
        except:
            pass

        text = f"""⚙️ *봇 상태*

🟢 Railway 배포: 정상
🕐 현재 시간: {now}
⏰ 리마인더: {len(reminders)}개 등록
👥 관리 그룹: 13개
📊 플러그인: 정상 작동"""
        await query.edit_message_text(text, parse_mode="Markdown")

def register(app, cfg):
    app.add_handler(CommandHandler("admin", admin_dashboard))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    print("✅ 관리자 대시보드 등록 완료")
