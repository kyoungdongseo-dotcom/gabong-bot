"""
주간 봉사일정 자동 발송 핸들러

- 매주 일요일 08:00 KST 자동 발송 (job queue 콜백)
- /weekly_report 명령어로 즉시 수동 발송 (관리자 전용)
- /schedule 명령어도 동일하게 동작 (기존 호환)

[시트 구조 설정]
config.json 에서 아래 값을 설정하면 파싱을 조정할 수 있습니다:
  - weekly_schedule_sheet_id : 봉사달력 스프레드시트 ID
  - weekly_schedule_sheet_name : 시트 탭 이름 (없으면 첫 번째 시트)
  - weekly_schedule_range : 데이터 범위 (기본값: "A1:J500")
  - weekly_schedule_date_col : 날짜가 있는 열 인덱스 (0=A, 1=B ..., 기본 0)
  - weekly_schedule_region_col : 지역 열 인덱스 (기본 1)
  - weekly_schedule_program_col : 프로그램명 열 인덱스 (기본 2)
"""

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
DAY_EMOJIS = {0: '☀️', 1: '☀️', 2: '☀️', 3: '☀️', 4: '☀️', 5: '🌟', 6: '🌞'}  # 월~일


# ─────────────────────────────────────────────
#  날짜 파싱 유틸
# ─────────────────────────────────────────────

def parse_date(text: str, default_year: int = None) -> datetime | None:
    """다양한 날짜 형식을 datetime으로 변환. 실패 시 None 반환."""
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    year = default_year or datetime.now(KST).year

    patterns = [
        (r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', lambda m: datetime(int(m[0]), int(m[1]), int(m[2]))),
        (r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})', lambda m: datetime(int(m[2]), int(m[0]), int(m[1]))),
        (r'(\d{1,2})[./](\d{1,2})',                  lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'(\d{1,2})월\s*(\d{1,2})일',               lambda m: datetime(year, int(m[0]), int(m[1]))),
        (r'^(\d{1,2})$',                             lambda m: datetime(year, 5, int(m[0]))),  # 5월 단순 숫자
    ]
    for pat, builder in patterns:
        m = re.search(pat, text)
        if m:
            try:
                return builder(m.groups())
            except ValueError:
                continue
    return None


def this_week_range():
    """이번 주 일요일(시작) ~ 토요일(끝) 반환 (KST, date 객체)."""
    now = datetime.now(KST)
    # Python weekday: 0=월 … 6=일
    # 이번 주 일요일 = 오늘 - ((weekday+1) % 7) 일
    days_since_sunday = (now.weekday() + 1) % 7
    sunday = now.date() - timedelta(days=days_since_sunday)
    saturday = sunday + timedelta(days=6)
    return sunday, saturday


# ─────────────────────────────────────────────
#  시트 데이터 읽기 & 파싱
# ─────────────────────────────────────────────

def read_sheet_values():
    """serviceAccountKey.json 을 사용해 봉사달력 시트 전체 데이터 반환."""
    creds = Credentials.from_service_account_file(
        'serviceAccountKey.json',
        scopes=config.get('google_scopes')
    )
    service = build('sheets', 'v4', credentials=creds)

    sheet_id   = config.get('weekly_schedule_sheet_id')
    sheet_name = config.get('weekly_schedule_sheet_name', '')
    data_range = config.get('weekly_schedule_range', 'A1:J500')
    full_range = f"'{sheet_name}'!{data_range}" if sheet_name else data_range

    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=full_range,
        valueRenderOption='FORMATTED_VALUE'
    ).execute()
    return result.get('values', [])


def parse_schedule_from_rows(rows):
    """
    행 데이터에서 이번 주 일정 추출.

    지원 구조:
    A) 행 기반: 날짜 | 지역 | 프로그램명 (한 행 = 한 일정)
       예) ['2026/5/4', '강남구', '주일예배봉사']
    B) 그리드: 날짜 헤더 행 + 아래 행들이 일~토 열에 일정
       예) 헤더: ['5/3', '5/4', '5/5', ...]
           이벤트: ['강남-예배', '회의', '', ...]

    두 방식을 모두 시도하고 이번 주 데이터가 있는 쪽 반환.
    """
    week_start, week_end = this_week_range()
    year = datetime.now(KST).year

    col_date    = config.get('weekly_schedule_date_col', 0)
    col_region  = config.get('weekly_schedule_region_col', 1)
    col_program = config.get('weekly_schedule_program_col', 2)

    # ── 방식 A: 날짜 컬럼이 있는 행 기반 ──
    result_a = {}
    for row in rows:
        if not row:
            continue
        cell0 = row[col_date] if len(row) > col_date else ''
        dt = parse_date(str(cell0), year)
        if not dt or not (week_start <= dt.date() <= week_end):
            continue

        # 날짜 셀이 여러 개인 행 = 그리드 헤더 → 방식A에서 제외
        date_count = sum(1 for c in row if parse_date(str(c), year))
        if date_count >= 3:
            continue

        region  = row[col_region].strip()  if len(row) > col_region  and row[col_region]  else ''
        program = row[col_program].strip() if len(row) > col_program and row[col_program] else ''

        if region and program:
            event = f"{region} — {program}"
        elif region or program:
            event = region or program
        else:
            cells = [c.strip() for c in row if c and c.strip()]
            event = ' | '.join(cells) if cells else ''

        if event:
            result_a.setdefault(dt.date(), []).append(event)

    if result_a:
        return result_a

    # ── 방식 B: 그리드 (컬럼 = 일~토 날짜 헤더) ──
    result_b = {}
    i = 0
    while i < len(rows):
        row = rows[i]
        if not row:
            i += 1
            continue

        # 행 내 날짜 셀 수집
        col_to_date = {}
        for j, cell in enumerate(row):
            dt = parse_date(str(cell), year)
            if dt and week_start <= dt.date() <= week_end:
                col_to_date[j] = dt.date()

        # 이번 주 날짜가 3개 이상 → 그리드 헤더 행
        if len(col_to_date) >= 3:
            i += 1
            while i < len(rows):
                next_row = rows[i]
                if not next_row:
                    i += 1
                    break

                # 다음 그리드 헤더(날짜 셀 3개 이상)가 나오면 종료
                next_date_count = sum(
                    1 for c in next_row if parse_date(str(c), year)
                )
                if next_date_count >= 3:
                    break

                for col_idx, date_key in col_to_date.items():
                    if col_idx < len(next_row):
                        event = next_row[col_idx].strip()
                        if event and not event.isdigit():
                            result_b.setdefault(date_key, []).append(event)
                i += 1
            break  # 이번 주 헤더 처리 완료
        i += 1

    return result_b


# ─────────────────────────────────────────────
#  메시지 조합
# ─────────────────────────────────────────────


async def get_council_schedule() -> str:
    """총회 스케줄을 읽고 포맷팅."""
    try:
        creds = Credentials.from_service_account_file(
            'serviceAccountKey.json',
            scopes=config.get('google_scopes')
        )
        service = build('sheets', 'v4', credentials=creds)
        
        sheet_id = config.get('weekly_schedule_sheet_id')
        sheet_name = config.get('weekly_schedule_sheet_name', '')
        council_range = "B44:H54"
        full_range = f"'{sheet_name}'!{council_range}" if sheet_name else council_range
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=full_range,
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        
        rows = result.get('values', [])
        week_start, week_end = this_week_range()
        year = datetime.now(KST).year
        
        # 날짜 헤더 행 찾기
        date_cols = {}
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row):
                dt = parse_date(str(cell), year)
                if dt and week_start <= dt.date() <= week_end:
                    date_cols[col_idx] = dt.date()
            if date_cols:
                break
        
        if not date_cols:
            return "등록된 총회 일정이 없습니다."
        
        # 같은 컬럼에서 일정 추출
        lines = []
        for col_idx, date_key in sorted(date_cols.items()):
            day_name = KR_DAYS[date_key.weekday()]
            lines.append(f"📅 {date_key.strftime('%m/%d')} ({day_name})")
            
            # 이 컬럼의 모든 행에서 일정 찾기
            for row_idx in range(1, len(rows)):
                if col_idx < len(rows[row_idx]):
                    event = rows[row_idx][col_idx].strip()
                    if event and not event.isdigit():
                        lines.append(f"  • {event}")
        
        return "
".join(lines) if lines else "등록된 총회 일정이 없습니다."
    except Exception as e:
        print(f"총회 스케줄 조회 오류: {e}")
        return ""


async def build_weekly_message() -> str:
    """이번 주 일정 메시지를 생성해 반환."""
    try:
        rows = read_sheet_values()
        day_events = parse_schedule_from_rows(rows)

        week_start, week_end = this_week_range()
        date_range_str = (
            f"{week_start.strftime('%m/%d')} ~ "
            f"{week_end.strftime('%m/%d')}"
        )

        lines = [
            f"📅 총회봉사교통부 이번 주 일정 ({date_range_str})",
            "━━━━━━━━━━━━━━━━━━",
            "",
            "📋 총회 스케줄",
        ]
        
        council_schedule = await get_council_schedule()
        if council_schedule:
            lines.append(council_schedule)
        lines.append("")
        lines.append("📋 봉사 일정")
        lines.append("")

        total_count = 0
        busiest_day = None
        busiest_count = 0

        # 일요일~토요일 순서 정렬
        all_dates = sorted(day_events.keys())
        for date_key in all_dates:
            events = day_events[date_key]
            if not events:
                continue
            count = len(events)
            total_count += count
            if count > busiest_count:
                busiest_count = count
                busiest_day = date_key

            weekday = date_key.weekday()  # 0=월 … 6=일
            day_name = KR_DAYS[weekday]
            emoji = DAY_EMOJIS.get(weekday, '📌')
            lines.append(f"{emoji} {date_key.strftime('%m/%d')} ({day_name})")
            for evt in events:
                lines.append(f"  • {evt}")
            lines.append("")

        if not day_events:
            lines.append("이번 주 등록된 봉사 일정이 없습니다.")
            lines.append("")
            lines.append("💡 시트 구조가 다른 경우 config.json 의")
            lines.append("   weekly_schedule_range / weekly_schedule_sheet_name 을 확인해주세요.")
            lines.append("")

        # 요약 섹션
        lines.append("📊 한 주 요약")
        lines.append(f"  • 총 봉사 건수: {total_count}건")
        if busiest_day:
            bday_name = KR_DAYS[busiest_day.weekday()]
            lines.append(f"  • 가장 바쁜 날: {busiest_day.strftime('%m/%d')}({bday_name}) — {busiest_count}건")

        return "\n".join(lines) if lines else "등록된 총회 일정이 없습니다."

    except Exception as e:
        print(f"❌ 주간 일정 메시지 생성 오류: {e}")
        traceback.print_exc()
        return f"⚠️ 이번 주 일정을 불러오는 중 오류가 발생했습니다.\n오류: {str(e)}"


# ─────────────────────────────────────────────
#  텔레그램 콜백 / 핸들러
# ─────────────────────────────────────────────

async def send_weekly_schedule_job(context: ContextTypes.DEFAULT_TYPE):
    """
    [Job Queue 콜백] 매주 일요일 08:00 KST 자동 발송.
    ※ job_queue 콜백은 update 없이 context 만 받습니다.
    """
    try:
        message = await build_weekly_message()
        await context.bot.send_message(
            chat_id=config.get('group_id'),
            message_thread_id=config.get('topic_id'),
            text=message,
        )
        print("✅ 주간 봉사일정 자동 발송 완료")
    except Exception as e:
        print(f"❌ 주간 봉사일정 자동 발송 실패: {e}")
        traceback.print_exc()
        try:
            await context.bot.send_message(
                chat_id=config.get('my_user_id'),
                text=f"⚠️ 주간 일정 자동 발송 실패:\n{str(e)}"
            )
        except Exception:
            pass


async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /weekly_report — 관리자가 즉시 이번 주 일정을 그룹에 발송.
    """
    if not update.message:
        return

    admin_ids = config.get('admin_ids') or []
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("❌ 이 명령어는 관리자만 사용할 수 있습니다.")
        return

    await update.message.reply_text("📤 이번 주 봉사일정을 조회 중입니다...")

    message = await build_weekly_message()
    await context.bot.send_message(
        chat_id=config.get('group_id'),
        message_thread_id=config.get('topic_id'),
        text=message,
    )
    await update.message.reply_text("✅ 이번 주 봉사일정이 그룹 공지 토픽에 발송되었습니다!")


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/schedule — /weekly_report 와 동일 (기존 명령어 유지)."""
    await weekly_report_command(update, context)
