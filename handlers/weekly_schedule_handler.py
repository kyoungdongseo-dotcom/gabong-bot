"""주간 봉사일정 및 총회 스케줄 자동 발송"""

import re
import traceback
from datetime import datetime, timedelta
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ContextTypes
import config

KST = pytz.timezone('Asia/Seoul')
KR_DAYS = ['월', '화', '수', '목', '금', '토', '일']
DAY_EMOJIS = {0: '☀️', 1: '☀️', 2: '☀️', 3: '☀️', 4: '☀️', 5: '🌟', 6: '🌞'}

def parse_date(text: str, default_year: int = None) -> datetime | None:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    year = default_year or datetime.now(KST).year
    patterns = [
        (r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', lambda m: datetime(int(m[0]), int(m[1]), int(m[2]))),
        (r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})', lambda m: datetime(int(m[2]), int(m[0]), int(m[1]))),
        (r'(\d{1,2})[./](\d{1,2})', lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'(\d{1,2})월\s*(\d{1,2})일', lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'^(\d{1,2})$', lambda m: datetime(year, datetime.now(KST).month, int(m[0]))),
    ]
    for pattern, converter in patterns:
        match = re.match(pattern, text)
        if match:
            try:
                return converter(match.groups())
            except:
                continue
    return None

def this_week_range():
    today = datetime.now(KST).date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

def read_sheet_values():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    service = build('sheets', 'v4', credentials=creds)
    sheet_id = config.get('weekly_schedule_sheet_id')
    sheet_name = config.get('weekly_schedule_sheet_name', '')
    data_range = config.get('weekly_schedule_range', 'A1:J500')
    full_range = f"'{sheet_name}'!{data_range}" if sheet_name else data_range
    result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=full_range, valueRenderOption='FORMATTED_VALUE').execute()
    return result.get('values', [])

def parse_schedule_from_rows(rows):
    week_start, week_end = this_week_range()
    year = datetime.now(KST).year
    day_events = {}
    
    if len(rows) < 2:
        return day_events
    
    date_row = rows[0]
    for col_idx, date_str in enumerate(date_row):
        dt = parse_date(str(date_str), year)
        if dt and week_start <= dt.date() <= week_end:
            date_key = dt.date()
            if not day_events.get(date_key):
                day_events[date_key] = []
            for row_idx in range(1, len(rows)):
                if col_idx < len(rows[row_idx]):
                    event = str(rows[row_idx][col_idx]).strip()
                    if event and event != "" and not event.isdigit() and not parse_date(event, year):
                        day_events[date_key].append(event)
    
    return day_events

async def get_council_schedule() -> str:
    """총회 스케줄을 읽고 포맷팅 (5월/6월 모두 반영)."""
    try:
        rows = read_sheet_values()
        week_start, week_end = this_week_range()
        year = datetime.now(KST).year
        current_month = datetime.now(KST).month
        
        lines = []
        
        if current_month == 5:
            # A1:J500 기준: rows[46]=A47(3~9), rows[47]=A48(내용)
            date_content_pairs = [(46, 47), (49, 50), (51, 52), (53, 54)]
            col_range = range(1, 8)  # B~H
        elif current_month == 6:
            date_content_pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
            col_range = range(0, 7)
        else:
            return "이 달 총회 스케줄은 아직 등록되지 않았습니다."
        
        for date_row_idx, content_row_idx in date_content_pairs:
            if date_row_idx >= len(rows) or content_row_idx >= len(rows):
                continue
            date_row = rows[date_row_idx]
            content_row = rows[content_row_idx]
            for col_idx in col_range:
                if col_idx >= len(date_row):
                    continue
                date_str = str(date_row[col_idx]).strip()
                dt = parse_date(date_str, year)
                if dt and week_start <= dt.date() <= week_end:
                    day_name = KR_DAYS[dt.weekday()]
                    lines.append(f"📅 {dt.strftime('%m/%d')} ({day_name})")
                    if col_idx < len(content_row):
                        event = str(content_row[col_idx]).strip()
                        if event and event != "":
                            for item in event.split("\n"):
                                if item.strip():
                                    lines.append(f"  • {item.strip()}")
        
        return "\n".join(lines) if lines else "등록된 총회 일정이 없습니다."
    except Exception as e:
        print(f"총회 스케줄 조회 오류: {e}")
        traceback.print_exc()
        return ""

async def build_weekly_message() -> str:
    try:
        rows = read_sheet_values()
        day_events = parse_schedule_from_rows(rows)
        week_start, week_end = this_week_range()
        date_range_str = f"{week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')}"
        
        lines = [f"📅 총회봉사교통부 이번 주 일정 ({date_range_str})", "━━━━━━━━━━━━━━━━━━"]
        
        council_schedule = await get_council_schedule()
        lines.append("📋 총회 스케줄")
        lines.append(council_schedule)
        
        lines.append("📋 봉사 일정")
        if day_events:
            for date_key in sorted(day_events.keys()):
                emoji = DAY_EMOJIS[date_key.weekday()]
                day_name = KR_DAYS[date_key.weekday()]
                lines.append(f"{emoji} {date_key.strftime('%m/%d')} ({day_name})")
                for event in day_events[date_key]:
                    lines.append(f"  • {event}")
        else:
            lines.append("이번 주 봉사일정이 없습니다.")
        
        event_count = sum(len(events) for events in day_events.values())
        busiest_day = max(day_events.keys(), key=lambda k: len(day_events[k])) if day_events else None
        lines.append("📊 한 주 요약")
        lines.append(f"  • 총 봉사 건수: {event_count}건")
        if busiest_day:
            busy_count = len(day_events[busiest_day])
            day_name = KR_DAYS[busiest_day.weekday()]
            lines.append(f"  • 가장 바쁜 날: {busiest_day.strftime('%m/%d')}({day_name}) — {busy_count}건")
        
        return "\n".join(lines)
    except Exception as e:
        print(f"주간 메시지 생성 오류: {e}")
        traceback.print_exc()
        return "일정을 불러올 수 없습니다."

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    message = await build_weekly_message()
    await update.message.reply_text(message)

async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("관리자만 사용 가능합니다.")
        return
    message = await build_weekly_message()
    group_id = config.get('group_id')
    topic_id = config.get('topic_id')
    try:
        await context.bot.send_message(chat_id=group_id, message_thread_id=topic_id, text=message)
        await update.message.reply_text("✅ 주간 일정이 발송되었습니다.")
    except Exception as e:
        print(f"발송 오류: {e}")
        await update.message.reply_text(f"발송 실패: {e}")

def register(app, config):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CommandHandler("weekly_report", weekly_report))
    print("✅ /weekly_report, /schedule 명령어 등록됨")
