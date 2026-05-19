"""관리자 대시보드 — /admin 8버튼 인터랙티브 메뉴

- 권한: config.admin_ids
- 진입: /admin
- callback_data prefix: "admin:"
- 결과: edit_message_text 우선, 실패/문서첨부 시 reply 로 fallback
"""

import asyncio
import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import config


# ───────────────────────────── 메뉴 정의 ─────────────────────────────

MAIN_TITLE = "🎛 GAbong Bot 관리자 대시보드"

MAIN_KEYBOARD = [
    [
        InlineKeyboardButton("📊 봇 상태", callback_data="admin:status"),
        InlineKeyboardButton("💾 즉시 백업", callback_data="admin:backup"),
    ],
    [
        InlineKeyboardButton("📝 주간보고서", callback_data="admin:weekly_report"),
        InlineKeyboardButton("📰 뉴스 현황", callback_data="admin:news_status"),
    ],
    [
        InlineKeyboardButton("⏰ 리마인더", callback_data="admin:my_reminders"),
        InlineKeyboardButton("🤖 AI 요약", callback_data="admin:summary_brief"),
    ],
    [
        InlineKeyboardButton("📋 보고서통계", callback_data="admin:report_stats"),
        InlineKeyboardButton("📅 주간일정", callback_data="admin:schedule"),
    ],
    [
        InlineKeyboardButton("👥 그룹 목록", callback_data="admin:groups"),
        InlineKeyboardButton("📊 봉사 통계", callback_data="admin:stats"),
    ],
]

BACK_KEYBOARD = [[InlineKeyboardButton("◀ 뒤로", callback_data="admin:back")]]

TG_TEXT_LIMIT = 4000  # 텔레그램 message 한도 4096 — 여유분 96자


# ───────────────────────────── 헬퍼 ─────────────────────────────

def _is_admin(user_id: int) -> bool:
    return user_id in (config.get("admin_ids") or [])


async def _show_main_menu(query):
    """메인 8버튼 메뉴 표시 (edit 우선)."""
    markup = InlineKeyboardMarkup(MAIN_KEYBOARD)
    try:
        await query.edit_message_text(MAIN_TITLE, reply_markup=markup)
    except BadRequest:
        # edit 실패 (예: 메시지가 너무 오래됐거나 그대로) → 새 메시지
        await query.message.reply_text(MAIN_TITLE, reply_markup=markup)


async def _show_result(query, text: str):
    """결과 화면 + [◀ 뒤로] — 길면 reply 로 fallback."""
    markup = InlineKeyboardMarkup(BACK_KEYBOARD)
    if not text:
        text = "(결과 없음)"
    # 한도 초과 → 분할: edit 으로 안내, 본문은 reply 로 분할 전송
    if len(text) > TG_TEXT_LIMIT:
        try:
            await query.edit_message_text(
                "📤 결과가 길어 별도 메시지로 전송합니다.",
                reply_markup=markup,
            )
        except BadRequest:
            pass
        # 4000자 단위로 잘라 reply
        for i in range(0, len(text), TG_TEXT_LIMIT):
            await query.message.reply_text(text[i:i + TG_TEXT_LIMIT])
        return
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except BadRequest as e:
        # 동일 텍스트 edit 등 → 새 메시지 fallback
        print(f"[ADMIN] edit_message_text BadRequest: {e}")
        await query.message.reply_text(text, reply_markup=markup)


# ───────────────────────────── 데이터 빌더 (각 분기) ─────────────────────────────

async def _build_status_text() -> str:
    """기존 handlers/status_handler.py 의 status_command 로직을 callback 컨텍스트로 재구성."""
    import os
    from datetime import datetime
    from database import get_reminders
    from utils import get_scheduler
    from handlers.status_handler import BOT_START_TIME, _get_last_commit, _get_last_backup

    delta = datetime.now() - BOT_START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}시간 {m}분 {s}초"

    try:
        reminder_count = len(get_reminders())
    except Exception:
        reminder_count = -1

    jobs = get_scheduler().get_jobs()
    job_list = "\n".join(f"  • {j.id}" for j in jobs) if jobs else "  (없음)"

    allowed = config.get("allowed_groups") or []
    exclude = config.get("exclude_groups") or []

    api_status = "✅ 설정됨" if os.environ.get("ANTHROPIC_API_KEY") else "❌ 미설정"
    sheets_ok = os.path.exists("credentials.json") and os.path.exists("serviceAccountKey.json")
    sheets_status = "✅ 파일 존재" if sheets_ok else "⚠️ credentials 없음"
    last_backup = _get_last_backup()
    commit = _get_last_commit()

    try:
        from handlers.message_handler import (
            MENTION_TRIGGER_HISTORY, MY_KEYWORD_TRIGGER_HISTORY,
            PENDING_REPORTS, PENDING_PHOTOS, MEDIA_GROUP_CACHE,
        )
        from utils import CHAT_HISTORY, GROUP_MESSAGES
        mem_lines = (
            f"  • MENTION_HISTORY: {len(MENTION_TRIGGER_HISTORY)}\n"
            f"  • MY_KEYWORD_HISTORY: {len(MY_KEYWORD_TRIGGER_HISTORY)}\n"
            f"  • CHAT_HISTORY: {len(CHAT_HISTORY)}\n"
            f"  • GROUP_MESSAGES: {len(GROUP_MESSAGES)}\n"
            f"  • PENDING_REPORTS: {len(PENDING_REPORTS)}\n"
            f"  • PENDING_PHOTOS: {len(PENDING_PHOTOS)}\n"
            f"  • MEDIA_GROUP_CACHE: {len(MEDIA_GROUP_CACHE)}"
        )
    except Exception as e:
        mem_lines = f"  (메모리 dict 조회 실패: {e})"

    return (
        f"🤖 봇 상태\n"
        f"\n"
        f"📌 최신 커밋: {commit}\n"
        f"⏱ 업타임: {uptime_str}\n"
        f"🔢 PID: {os.getpid()}\n"
        f"\n"
        f"📝 리마인더: {reminder_count}개\n"
        f"✅ 허가 그룹: {len(allowed)}개\n"
        f"🚫 제외 그룹: {len(exclude)}개\n"
        f"\n"
        f"🤖 Claude API: {api_status}\n"
        f"📊 Google Sheets: {sheets_status}\n"
        f"💾 마지막 백업: {last_backup}\n"
        f"\n"
        f"📊 메모리 dict (keys):\n"
        f"{mem_lines}\n"
        f"\n"
        f"📅 스케줄 job ({len(jobs)}개):\n"
        f"{job_list}"
    )


async def _build_reminders_text(chat_id) -> str:
    """callback 호출 chat 기준 리마인더 목록 — handlers/reminder_handler.my_reminders 로직 재현."""
    from database import get_reminders
    try:
        all_reminders = get_reminders()
    except Exception as e:
        return f"❌ 리마인더 조회 실패: {e}"

    reminders = [
        r for r in all_reminders
        if str(r.get("group_id")) == str(chat_id) or r.get("type", "").startswith("broadcast")
    ]
    if not reminders:
        return "⏰ 이 그룹에 등록된 리마인더가 없습니다."

    lines = [f"⏰ 리마인더 목록 ({len(reminders)}개)\n"]
    for r in reminders:
        r_type = r.get("type", "")
        rid = r.get("id", "")
        t = r.get("time", "")
        msg_text = (r.get("message") or "")[:40]
        dow = r.get("day_of_week", "")
        dom = r.get("day_of_month", "")
        if r_type == "daily":
            lines.append(f"[{rid}] 매일 {t} - {msg_text}")
        elif r_type == "weekly":
            lines.append(f"[{rid}] 매주 {dow} {t} - {msg_text}")
        elif r_type == "biweekly":
            lines.append(f"[{rid}] 2주마다 {dow} {t} - {msg_text}")
        elif r_type == "monthly":
            lines.append(f"[{rid}] 매월 {dom}일 {t} - {msg_text}")
        elif r_type.startswith("broadcast_"):
            suffix = r_type.replace("broadcast_", "")
            lines.append(f"[{rid}] [전체] {suffix} {t} - {msg_text}")
        else:
            lines.append(f"[{rid}] {r_type} {t} - {msg_text}")
    return "\n".join(lines)


async def _build_news_status_text() -> str:
    """handlers/news_clipping_handler.cmd_news_status 의 권역 집계 로직 재현."""
    try:
        from handlers.news_clipping_handler import (
            _open_spreadsheet, _ensure_worksheet, _read_candidates,
            CANDIDATE_SHEET, CANDIDATE_HEADERS, REGION_QUERY_MAP,
        )
        ss = await asyncio.to_thread(_open_spreadsheet)
        ws, _ = await asyncio.to_thread(_ensure_worksheet, ss, CANDIDATE_SHEET, CANDIDATE_HEADERS)
        rows, _ = await asyncio.to_thread(_read_candidates, ws)
    except Exception as e:
        return f"❌ 뉴스 상태 조회 실패: {str(e)[:200]}"

    region_total: dict = {}
    region_checked: dict = {}
    for r in rows:
        region = r.get("권역", "") or "(미지정)"
        region_total[region] = region_total.get(region, 0) + 1
        if (r.get("발송", "") or "").upper() == "TRUE":
            region_checked[region] = region_checked.get(region, 0) + 1

    lines = ["📰 권역별 뉴스 후보 현황"]
    for region in REGION_QUERY_MAP:
        total = region_total.get(region, 0)
        checked = region_checked.get(region, 0)
        lines.append(f"  • {region}: {total}건 중 {checked}건 선별")
    other = [r for r in region_total if r not in REGION_QUERY_MAP]
    for r in other:
        lines.append(f"  • {r} (외): {region_total[r]}건 중 {region_checked.get(r, 0)}건")
    return "\n".join(lines)


async def _build_weekly_report_text(chat_id, user_id, user_name, thread_id) -> str:
    """AI 주간 보고서 — handlers/ai_advanced_handler.weekly_report 로직 재현."""
    try:
        from utils import ask_claude, fetch_weekly_messages, get_chat_mode
        from handlers.ai_advanced_handler import _get_week_start, _build_weekly_prompt
        since = _get_week_start()
        messages = fetch_weekly_messages(chat_id, since)
        if not messages:
            return "이번 주에 기록된 대화가 없습니다."
        prompt = _build_weekly_prompt(messages)
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None, ask_claude, prompt, chat_id, user_id, user_name, thread_id,
            get_chat_mode(chat_id),
        )
        return f"📊 주간 보고서\n\n{answer}"
    except Exception as e:
        return f"❌ 주간 보고서 생성 실패: {e}"


async def _build_summary_brief_text(chat_id, user_id, user_name, thread_id) -> str:
    """AI 간단 요약 — handlers/ai_advanced_handler.summary_brief 로직 재현."""
    try:
        from utils import ask_claude, get_chat_history, get_chat_mode
        from handlers.ai_advanced_handler import _build_history_text
        history = get_chat_history(chat_id, limit=100)
        if not history:
            return "대화 내역이 없습니다."
        history_text = _build_history_text(history)
        question = (
            "다음 대화를 간단하고 명확하게 한국어로 요약해 주세요. 핵심 내용만 포함하세요:\n"
            f"{history_text}"
        )
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None, ask_claude, question, chat_id, user_id, user_name, thread_id,
            get_chat_mode(chat_id),
        )
        return f"📝 간단 요약\n\n{answer}"
    except Exception as e:
        return f"❌ AI 요약 실패: {e}"


async def _build_report_stats_text() -> str:
    """월간 통계 — monthly_stats() 그대로 호출."""
    try:
        from handlers.report_analytics import monthly_stats
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, monthly_stats)
    except Exception as e:
        return f"❌ 보고서 통계 생성 실패: {e}"


async def _build_schedule_text() -> str:
    """주간 봉사일정 — build_weekly_message() 그대로 호출."""
    try:
        from handlers.weekly_schedule_handler import build_weekly_message
        return await build_weekly_message()
    except Exception as e:
        return f"❌ 일정 조회 실패: {e}"


async def _build_groups_text() -> str:
    """등록 broadcast 그룹 목록 — config.broadcast_groups 기반."""
    broadcast_groups = config.get("broadcast_groups") or []
    if not broadcast_groups:
        return "👥 등록된 그룹 없음"
    lines = [f"👥 등록된 그룹 목록 ({len(broadcast_groups)}개)\n"]
    for g in broadcast_groups:
        name = g.get("name", "이름없음")
        lines.append(f"• {name}")
    return "\n".join(lines)


async def _build_busy_summary_text() -> str:
    """이번 주 봉사 통계 (건수 / 가장 바쁜 날) — 봉사달력 시트 기준."""
    try:
        from handlers.weekly_schedule_handler import (
            read_sheet_values, parse_schedule_from_rows, KR_DAYS,
        )
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, read_sheet_values)
        day_events = parse_schedule_from_rows(rows)
    except Exception as e:
        return f"📊 통계 조회 오류: {e}"

    event_count = sum(len(v) for v in day_events.values())
    lines = ["📊 이번 주 봉사 통계\n", f"• 총 봉사 건수: {event_count}건"]
    if day_events:
        busiest = max(day_events.keys(), key=lambda k: len(day_events[k]))
        lines.append(
            f"• 가장 바쁜 날: {busiest.strftime('%m/%d')}"
            f"({KR_DAYS[busiest.weekday()]}) - {len(day_events[busiest])}건"
        )
    lines.append(f"• 봉사 날짜 수: {len(day_events)}일")
    return "\n".join(lines)


# ───────────────────────────── 진입점: /admin ─────────────────────────────

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    markup = InlineKeyboardMarkup(MAIN_KEYBOARD)
    await update.message.reply_text(MAIN_TITLE, reply_markup=markup)


# ───────────────────────────── 콜백 라우터 ─────────────────────────────

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    if not _is_admin(query.from_user.id):
        await query.answer("❌ 권한이 없습니다.", show_alert=True)
        return
    await query.answer()

    data = query.data or ""
    print(f"[ADMIN] 버튼: {data}")

    try:
        if data == "admin:back":
            await _show_main_menu(query)
            return

        # AI / 백업 / 시트 조회는 시간이 걸리므로 진행 표시
        loading_map = {
            "admin:weekly_report": "🤖 AI 주간 보고서 생성 중...",
            "admin:summary_brief": "🤖 AI 요약 생성 중...",
            "admin:report_stats": "📊 월간 통계 집계 중...",
            "admin:news_status": "📰 뉴스 현황 조회 중...",
            "admin:backup": "💾 백업 진행 중...",
        }
        if data in loading_map:
            try:
                await query.edit_message_text(loading_map[data])
            except BadRequest:
                pass

        if data == "admin:status":
            text = await _build_status_text()

        elif data == "admin:backup":
            from handlers.backup_handler import run_backup
            # run_backup 은 ADMIN_ID 로 DM 첨부 발송 + 결과 텍스트 반환
            text = await run_backup(context.bot)
            text = (text or "백업 완료") + "\n\n(zip 파일은 관리자 DM 으로 전송됨)"

        elif data == "admin:weekly_report":
            chat_id = update.effective_chat.id
            user_id = query.from_user.id
            user_name = query.from_user.first_name
            thread_id = query.message.message_thread_id if query.message else None
            text = await _build_weekly_report_text(chat_id, user_id, user_name, thread_id)

        elif data == "admin:news_status":
            text = await _build_news_status_text()

        elif data == "admin:my_reminders":
            chat_id = update.effective_chat.id
            text = await _build_reminders_text(chat_id)

        elif data == "admin:summary_brief":
            chat_id = update.effective_chat.id
            user_id = query.from_user.id
            user_name = query.from_user.first_name
            thread_id = query.message.message_thread_id if query.message else None
            text = await _build_summary_brief_text(chat_id, user_id, user_name, thread_id)

        elif data == "admin:report_stats":
            text = await _build_report_stats_text()

        elif data == "admin:schedule":
            text = await _build_schedule_text()

        elif data == "admin:groups":
            text = await _build_groups_text()

        elif data == "admin:stats":
            text = await _build_busy_summary_text()

        else:
            text = f"알 수 없는 동작: {data}"

        await _show_result(query, text)

    except Exception as e:
        print(f"[ADMIN] 콜백 오류: {e}")
        traceback.print_exc()
        await _show_result(query, f"❌ 오류 발생: {e}")


def register(app, cfg):
    app.add_handler(CommandHandler("admin", admin_dashboard), group=-1)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin:"), group=-1)
    print("✅ 관리자 대시보드 (8버튼) 등록 완료")
