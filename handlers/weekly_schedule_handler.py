"""주간 봉사일정 및 총회 스케줄"""

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

def get_current_service_sheet_name():
    """현재 달 봉사달력 시트명 자동 감지"""
    try:
        creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
        service = build('sheets', 'v4', credentials=creds)
        
        sheet_id = config.get('weekly_schedule_sheet_id')
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=sheet_id
        ).execute()
        
        sheets = spreadsheet.get('sheets', [])
        current_month = datetime.now(KST).month
        month_kr = ['', '1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']
        
        for sheet in sheets:
            title = sheet['properties']['title']
            if '봉사달력' in title and month_kr[current_month] in title:
                print(f"✅ 봉사달력 시트 감지: {title}")
                return title
        
        fallback = f"봉사달력 {month_kr[current_month]}"
        print(f"⚠️ 정확한 시트 못 찾음, 기본값 사용: {fallback}")
        return fallback
    
    except Exception as e:
        print(f"❌ 시트명 자동감지 오류: {e}")
        return config.get('weekly_schedule_sheet_name', '봉사달력 5월')

def parse_date(text: str, default_year: int = None) -> datetime | None:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    year = default_year or datetime.now(KST).year
    month = datetime.now(KST).month
    patterns = [
        (r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', lambda m: datetime(int(m[0]), int(m[1]), int(m[2]))),
        (r'(\d{1,2})[./](\d{1,2})', lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'(\d{1,2})월\s*(\d{1,2})일', lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'^(\d{1,2})$', lambda m: datetime(year, month, int(m[0]))),
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
    week_start = today - timedelta(days=today.weekday() + 2)
    week_end = week_start + timedelta(days=8)
    return week_start, week_end

def read_sheet_values():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    service = build('sheets', 'v4', credentials=creds)
    sheet_id = config.get('weekly_schedule_sheet_id')
    
    sheet_name = get_current_service_sheet_name()
    
    data_range = config.get('weekly_schedule_range', 'A1:H500')
    full_range = f"'{sheet_name}'!{data_range}" if sheet_name else data_range
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=full_range,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    return result.get('values', [])

def parse_schedule_from_rows(rows):
    """봉사 일정 파싱: rows[17]=날짜행, rows[18:43]=봉사내용"""
    week_start, week_end = this_week_range()
    year = datetime.now(KST).year
    day_events = {}

    if len(rows) <= 17:
        return day_events

    date_row = rows[17]

    for col_idx, date_str in enumerate(date_row):
        dt = parse_date(str(date_str), year)
        if dt and week_start <= dt.date() <= week_end:
            date_key = dt.date()
            if not day_events.get(date_key):
                day_events[date_key] = []
            for row_idx in range(18, min(43, len(rows))):
                if col_idx < len(rows[row_idx]):
                    event = str(rows[row_idx][col_idx]).strip()
                    if event and event != "" and not event.isdigit() and not parse_date(event, year):
                        day_events[date_key].append(event)
    return day_events

def read_council_sheet_values():
    """총회 스케줄 시트 별도로 읽기"""
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    service = build('sheets', 'v4', credentials=creds)
    sheet_id = config.get('weekly_schedule_sheet_id')
    sheet_name = config.get('council_schedule_sheet_name', '2026년 총회 업무일정')
    data_range = config.get('council_schedule_range', 'B44:M80')
    full_range = f"'{sheet_name}'!{data_range}"
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=full_range,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    return result.get('values', [])

async def get_council_schedule() -> str:
    """총회 스케줄 파싱: 총회 시트에서 직접 읽기"""
    try:
        rows = read_council_sheet_values()
        week_start, week_end = this_week_range()
        year = datetime.now(KST).year
        lines = []

        date_content_pairs = [(3, 4), (5, 6), (7, 8), (9, 10)]

        for date_row_idx, content_row_idx in date_content_pairs:
            if date_row_idx >= len(rows) or content_row_idx >= len(rows):
                continue
            date_row = rows[date_row_idx]
            content_row = rows[content_row_idx]

            for col_idx in range(0, 7):
                if col_idx >= len(date_row):
                    continue
                date_str = str(date_row[col_idx]).strip()
                dt = parse_date(date_str, year)
                if dt and week_start <= dt.date() <= week_end:
                    day_name = KR_DAYS[dt.weekday()]
                    lines.append(f"📅 {dt.strftime('%m/%d')} ({day_name})")
                    if col_idx < len(content_row):
                        content = str(content_row[col_idx]).strip()
                        if content and content != "":
                            lines.append(f"  • {content}")

        return "\n".join(lines) if lines else "이번 주 총회 일정이 없습니다."
    except Exception as e:
        print(f"총회 스케줄 오류: {e}")
        traceback.print_exc()
        return ""

async def build_weekly_message() -> str:
    try:
        rows = read_sheet_values()
        day_events = parse_schedule_from_rows(rows)
        week_start, week_end = this_week_range()
        date_range_str = f"{week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')}"

        lines = [f"📅 총회봉사교통부 이번 주 일정 ({date_range_str})", "━━━━━━━━━━━━━━━━━━"]

        council = await get_council_schedule()
        lines.append("📋 총회 스케줄")
        lines.append(council)

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

        event_count = sum(len(v) for v in day_events.values())
        lines.append("📊 한 주 요약")
        lines.append(f"  • 총 봉사 건수: {event_count}건")

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
        await update.message.reply_text(f"발송 실패: {e}")

def register(app, config):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CommandHandler("weekly_report", weekly_report))
    print("✅ /weekly_report, /schedule 명령어 등록됨")
