"""관리자 대시보드 핸들러"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
import config

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("🎛 GAbong Bot 관리자 대시보드", reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in config.get('admin_ids', []):
        await query.answer("❌ 권한이 없습니다.", show_alert=True)
        return
    await query.answer()
    print(f"[ADMIN] 버튼 클릭: {query.data}")
    text = "오류가 발생했습니다."

    try:
        if query.data == "admin_notice":
            text = "📢 공지 발송\n\n발송할 내용을 입력하세요:\n/broadcast 내용"

        elif query.data == "admin_schedule":
            from handlers.weekly_schedule_handler import build_weekly_message
            text = await build_weekly_message()
            text = text[:4000]

        elif query.data == "admin_reminders":
            try:
                from database import get_reminders
                reminders = get_reminders()
            except Exception:
                reminders = []
            if not reminders:
                text = "⏰ 등록된 리마인더 없음"
            else:
                items = [f"⏰ 등록된 리마인더 목록 ({len(reminders)}개)\n"]
                for i, r in enumerate(reminders, 1):
                    r_type = r.get("type", "")
                    time_str = r.get("time", "")
                    msg = (r.get("message") or "")[:40]
                    rid = r.get("id", "")
                    dow = r.get("day_of_week") or ""
                    dom = r.get("day_of_month") or ""
                    if r_type == "daily":
                        label = f"매일 {time_str}"
                    elif r_type in ("weekly", "biweekly"):
                        prefix = "2주마다" if r_type == "biweekly" else "매주"
                        label = f"{prefix} {dow} {time_str}"
                    elif r_type == "monthly":
                        label = f"매월 {dom}일 {time_str}"
                    elif r_type.startswith("broadcast_"):
                        label = f"[전체] {r_type.replace('broadcast_', '')} {time_str}"
                    else:
                        label = f"{r_type} {time_str}"
                    items.append(f"{i}. [{rid}] {label}")
                    items.append(f"   {msg}")
                text = "\n".join(items)

        elif query.data == "admin_stats":
            try:
                from handlers.weekly_schedule_handler import read_sheet_values, parse_schedule_from_rows, KR_DAYS
                rows = read_sheet_values()
                day_events = parse_schedule_from_rows(rows)
                event_count = sum(len(v) for v in day_events.values())
                busiest = max(day_events.keys(), key=lambda k: len(day_events[k])) if day_events else None
                items = ["📊 이번 주 봉사 통계\n"]
                items.append(f"• 총 봉사 건수: {event_count}건")
                if busiest:
                    items.append(f"• 가장 바쁜 날: {busiest.strftime('%m/%d')}({KR_DAYS[busiest.weekday()]}) - {len(day_events[busiest])}건")
                items.append(f"• 봉사 날짜 수: {len(day_events)}일")
                text = "\n".join(items)
            except Exception as e:
                text = f"📊 통계 조회 오류: {e}"

        elif query.data == "admin_groups":
            broadcast_groups = config.get('broadcast_groups', [])
            if not broadcast_groups:
                text = "👥 등록된 그룹 없음"
            else:
                items = [f"👥 등록된 그룹 목록 ({len(broadcast_groups)}개)\n"]
                for g in broadcast_groups:
                    name = g.get('name', '이름없음')
                    items.append(f"• {name}")
                text = "\n".join(items)

        elif query.data == "admin_status":
            import datetime
            import pytz
            KST = pytz.timezone('Asia/Seoul')
            now = datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
            try:
                from database import get_reminders
                reminders = get_reminders()
            except Exception:
                reminders = []
            group_count = len(config.get('broadcast_groups', []))
            text = (
                f"⚙️ 봇 상태\n\n"
                f"🟢 Oracle Cloud 서버: 정상\n"
                f"🕐 현재 시간: {now}\n"
                f"⏰ 리마인더: {len(reminders)}개 등록\n"
                f"👥 관리 그룹: {group_count}개"
            )

    except Exception as e:
        print(f"[ADMIN] 콜백 오류: {e}")
        import traceback
        traceback.print_exc()
        text = f"오류 발생: {e}"

    await query.edit_message_text(text)

def register(app, cfg):
    app.add_handler(CommandHandler("admin", admin_dashboard))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    print("✅ 관리자 대시보드 등록 완료")
