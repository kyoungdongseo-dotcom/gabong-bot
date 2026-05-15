"""3개 보고서 일일 자동 분석 + /report_stats 명령어"""

import asyncio
from collections import Counter
from datetime import datetime, timedelta

import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ContextTypes

import config

KST = pytz.timezone('Asia/Seoul')
ADMIN_USER_ID = config.get('my_user_id', 97057565)

# 시트 위치 (3종 보고서)
AWARD_SHEET_NAME = '수상보고창'
MOU_SHEET_NAME = '협약보고창'
SERVICE_SHEET_NAME = '봉사리포트'
AWARD_SPREADSHEET_ID = '1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4'


def _get_service():
    scopes = config.get('google_scopes', ['https://www.googleapis.com/auth/spreadsheets'])
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=scopes)
    return build('sheets', 'v4', credentials=creds)


def _read_sheet(sheet_id: str, sheet_name: str, rng: str = 'A:Z') -> list:
    try:
        service = _get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{sheet_name}'!{rng}",
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"⚠️ 시트 읽기 실패 ({sheet_name}): {e}")
        return []


def _filter_by_date(rows: list, target_date: datetime, date_col_idx: int = 0) -> list:
    """등록일시 컬럼 기준으로 특정 날짜 행만 필터링"""
    target_str = target_date.strftime('%Y-%m-%d')
    matched = []
    for row in rows[1:]:  # skip header
        if len(row) > date_col_idx:
            val = str(row[date_col_idx])
            if val.startswith(target_str):
                matched.append(row)
    return matched


def _filter_by_month(rows: list, target_year: int, target_month: int,
                     date_col_idx: int = 0) -> list:
    target_prefix = f"{target_year}-{target_month:02d}"
    matched = []
    for row in rows[1:]:
        if len(row) > date_col_idx:
            val = str(row[date_col_idx])
            if val.startswith(target_prefix):
                matched.append(row)
    return matched


def _count_by_jipa(rows: list, jipa_col_idx: int = 1) -> Counter:
    """지파/지역별 건수"""
    c = Counter()
    for row in rows:
        if len(row) > jipa_col_idx:
            jipa = str(row[jipa_col_idx]).strip() or '미상'
            c[jipa] += 1
    return c


def daily_analysis() -> str:
    """어제 들어온 3개 보고서 통계 (관리자 DM용 텍스트 생성)"""
    yesterday = datetime.now(KST) - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d (%a)')

    sheet_id = config.get('spreadsheet_id', AWARD_SPREADSHEET_ID)

    # 봉사보고서 (지파명: col 1)
    service_rows = _read_sheet(sheet_id, SERVICE_SHEET_NAME)
    service_yesterday = _filter_by_date(service_rows, yesterday, 0)
    # 봉사 어제 지파별
    service_y_jipa = Counter()
    for row in service_yesterday:
        if len(row) > 1:
            service_y_jipa[str(row[1]).strip() or '미상'] += 1

    # 수상보고서 (지역: col 1, 지부: col 2)
    award_rows = _read_sheet(AWARD_SPREADSHEET_ID, AWARD_SHEET_NAME)
    award_yesterday = _filter_by_date(award_rows, yesterday, 0)
    award_y_jipa = Counter()
    for row in award_yesterday:
        if len(row) > 1:
            award_y_jipa[str(row[1]).strip() or '미상'] += 1

    # MOU 보고서
    mou_rows = _read_sheet(AWARD_SPREADSHEET_ID, MOU_SHEET_NAME)
    mou_yesterday = _filter_by_date(mou_rows, yesterday, 0)
    mou_y_jipa = Counter()
    for row in mou_yesterday:
        if len(row) > 1:
            mou_y_jipa[str(row[1]).strip() or '미상'] += 1

    lines = [
        f"📊 일일 보고서 분석 — {date_str}",
        "━━━━━━━━━━━━━━━━━━",
        f"📋 봉사보고서: {len(service_yesterday)}건",
    ]
    if service_y_jipa:
        for jipa, n in service_y_jipa.most_common(5):
            lines.append(f"  • {jipa}: {n}건")

    lines += [
        "",
        f"🏆 수상보고서: {len(award_yesterday)}건",
    ]
    if award_y_jipa:
        for jipa, n in award_y_jipa.most_common(5):
            lines.append(f"  • {jipa}: {n}건")

    lines += [
        "",
        f"🤝 MOU 보고서: {len(mou_yesterday)}건",
    ]
    if mou_y_jipa:
        for jipa, n in mou_y_jipa.most_common(5):
            lines.append(f"  • {jipa}: {n}건")

    # 데이터 품질 점검
    quality_warnings = []
    for label, rows_y in [
        ('봉사', service_yesterday), ('수상', award_yesterday), ('MOU', mou_yesterday),
    ]:
        for row in rows_y:
            empty_required = sum(1 for v in row[1:5] if not v or not str(v).strip())
            if empty_required >= 2:
                quality_warnings.append(f"{label} 보고서 일부 항목 누락")
                break

    # 이상 패턴: 0건이면 경고
    if len(service_yesterday) == 0 and len(award_yesterday) == 0 and len(mou_yesterday) == 0:
        quality_warnings.append("어제 모든 보고서 0건 — 시스템 점검 필요")

    if quality_warnings:
        lines += ["", "⚠️ 데이터 품질 이슈:"]
        for w in set(quality_warnings):
            lines.append(f"  • {w}")

    return "\n".join(lines)


async def send_daily_analysis(bot):
    """매일 09:00 KST 자동 실행 — 관리자 DM"""
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, daily_analysis)
        await bot.send_message(chat_id=ADMIN_USER_ID, text=text)
        print("✅ 일일 분석 보고 발송 완료")
    except Exception as e:
        print(f"❌ 일일 분석 오류: {e}")
        try:
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"❌ 일일 보고서 분석 실패: {e}"
            )
        except Exception:
            pass


def monthly_stats() -> str:
    """이번 달 누적 통계 (/report_stats 용)"""
    now = datetime.now(KST)
    year, month = now.year, now.month
    month_str = f"{year}-{month:02d}"

    sheet_id = config.get('spreadsheet_id', AWARD_SPREADSHEET_ID)

    service_rows = _read_sheet(sheet_id, SERVICE_SHEET_NAME)
    award_rows = _read_sheet(AWARD_SPREADSHEET_ID, AWARD_SHEET_NAME)
    mou_rows = _read_sheet(AWARD_SPREADSHEET_ID, MOU_SHEET_NAME)

    service_m = _filter_by_month(service_rows, year, month, 0)
    award_m = _filter_by_month(award_rows, year, month, 0)
    mou_m = _filter_by_month(mou_rows, year, month, 0)

    service_jipa = Counter()
    for row in service_m:
        if len(row) > 1:
            service_jipa[str(row[1]).strip() or '미상'] += 1

    # 활동도 점수 = 봉사 + 수상 + MOU 가중합
    activity = Counter(service_jipa)
    for row in award_m:
        if len(row) > 1:
            activity[str(row[1]).strip() or '미상'] += 1
    for row in mou_m:
        if len(row) > 1:
            activity[str(row[1]).strip() or '미상'] += 1

    # 미제출 지파 (봉사 0건)
    expected_jipa = {
        '도마', '다대오', '바돌', '안드레', '요한', '시몬', '맛디아',
        '서야', '빌립', '부야', '베드로', '마태'
    }
    submitted = set()
    for jipa in service_jipa:
        for exp in expected_jipa:
            if exp in jipa:
                submitted.add(exp)
    missing = expected_jipa - submitted

    lines = [
        f"📈 {month_str} 월간 보고서 통계",
        "━━━━━━━━━━━━━━━━━━",
        f"📋 봉사: {len(service_m)}건  🏆 수상: {len(award_m)}건  🤝 MOU: {len(mou_m)}건",
        f"📊 합계: {len(service_m) + len(award_m) + len(mou_m)}건",
        "",
        "🏅 지파별 활동도 (Top 10):",
    ]
    for jipa, n in activity.most_common(10):
        lines.append(f"  • {jipa}: {n}건")

    if missing:
        lines += [
            "",
            f"⚠️ 미제출 지파 ({len(missing)}개):",
            f"  {', '.join(sorted(missing))}"
        ]

    # 데이터 품질 점수 (단순: 모든 필수 컬럼이 채워진 비율)
    quality_score = 0
    total = len(service_m) + len(award_m) + len(mou_m)
    if total > 0:
        complete = 0
        for rows_set in (service_m, award_m, mou_m):
            for row in rows_set:
                if len(row) >= 5 and all(str(v).strip() for v in row[:5]):
                    complete += 1
        quality_score = round(complete / total * 100)

    lines += ["", f"📐 데이터 품질 점수: {quality_score}%"]

    return "\n".join(lines)


async def report_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/report_stats — 월간 통계 (관리자만)"""
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    await update.message.reply_text("📊 통계 집계 중... (수 초 소요)")
    loop = asyncio.get_running_loop()
    try:
        text = await loop.run_in_executor(None, monthly_stats)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ 통계 생성 실패: {e}")
