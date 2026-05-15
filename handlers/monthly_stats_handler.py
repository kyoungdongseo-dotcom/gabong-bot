import logging
import traceback
from datetime import datetime, timedelta
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config

logger = logging.getLogger(__name__)

KST = pytz.timezone('Asia/Seoul')

def get_sheet_service():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    return build('sheets', 'v4', credentials=creds)

def get_last_month_range():
    """지난달 시작일, 종료일 계산"""
    today = datetime.now(KST)
    first_day = today.replace(day=1)
    last_month_end = first_day - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start.date(), last_month_end.date()

def read_report_data():
    """봉사리포트 시트에서 데이터 읽기"""
    try:
        service = get_sheet_service()
        spreadsheet_id = config.get('spreadsheet_id')
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="봉사리포트!A2:W1000",
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"❌ 봉사리포트 읽기 오류: {e}")
        return []

def get_week_number(date, month_start):
    """해당 날짜의 주차 계산"""
    delta = (date - month_start).days
    return delta // 7 + 1

def analyze_monthly_stats():
    """지난달 데이터 주차별 집계"""
    try:
        rows = read_report_data()
        month_start, month_end = get_last_month_range()

        weekly_data = {}

        for row in rows:
            if len(row) < 6:
                continue
            try:
                date_str = row[5]
                if not date_str:
                    continue
                for fmt in ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d']:
                    try:
                        date = datetime.strptime(date_str[:10], fmt).date()
                        if month_start <= date <= month_end:
                            week_num = get_week_number(date, month_start)
                            if week_num not in weekly_data:
                                week_start = month_start + timedelta(weeks=week_num-1)
                                week_end = min(week_start + timedelta(days=6), month_end)
                                weekly_data[week_num] = {
                                    'week_start': week_start,
                                    'week_end': week_end,
                                    'rows': []
                                }
                            weekly_data[week_num]['rows'].append(row)
                        break
                    except Exception as e:
                        logger.debug(f"analyze_monthly_stats 날짜 파싱 무시된 예외: {e}")
                        continue
            except Exception as e:
                logger.debug(f"analyze_monthly_stats 행 처리 무시된 예외: {e}")
                continue

        result_rows = []
        for week_num in sorted(weekly_data.keys()):
            week = weekly_data[week_num]
            week_rows = week['rows']

            total_count = len(week_rows)
            total_inner = sum(int(r[8]) for r in week_rows if len(r) > 8 and r[8].isdigit())
            total_outer = sum(int(r[9]) for r in week_rows if len(r) > 9 and r[9].isdigit())
            total_volunteers = total_inner + total_outer
            total_beneficiary = sum(int(r[7]) for r in week_rows if len(r) > 7 and r[7].isdigit())

            category_count = {}
            for r in week_rows:
                if len(r) > 4 and r[4]:
                    cat = r[4].strip()
                    category_count[cat] = category_count.get(cat, 0) + 1
            top_category = max(category_count, key=category_count.get) if category_count else ''

            regions = set(r[6].strip() for r in week_rows if len(r) > 6 and r[6])
            jipas = set(r[1].strip() for r in week_rows if len(r) > 1 and r[1])

            result_rows.append([
                month_start.year,
                month_start.month,
                f"{week_num}주차",
                week['week_start'].strftime('%Y-%m-%d'),
                week['week_end'].strftime('%Y-%m-%d'),
                total_count,
                total_inner,
                total_outer,
                total_volunteers,
                total_beneficiary,
                top_category,
                len(regions),
                len(jipas)
            ])

        return result_rows, month_start

    except Exception as e:
        print(f"❌ 월간통계 분석 오류: {e}")
        traceback.print_exc()
        return [], None

def save_monthly_stats(result_rows):
    """월간통계 시트에 저장"""
    try:
        service = get_sheet_service()
        spreadsheet_id = config.get('spreadsheet_id')

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="월간통계!A:M",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': result_rows}
        ).execute()

        print(f"✅ 월간통계 저장 완료: {len(result_rows)}개 주차")
        return True

    except Exception as e:
        print(f"❌ 월간통계 저장 오류: {e}")
        return False

async def send_monthly_stats(bot):
    """매월 1일 00:00 관리자 DM으로 발송"""
    try:
        result_rows, month_start = analyze_monthly_stats()

        if not result_rows:
            await bot.send_message(
                chat_id=config.get('my_user_id'),
                text="📈 지난달 봉사 데이터가 없습니다."
            )
            return

        save_monthly_stats(result_rows)

        total_count = sum(r[5] for r in result_rows)
        total_volunteers = sum(r[8] for r in result_rows)
        total_beneficiary = sum(r[9] for r in result_rows)

        lines = [
            f"📈 {month_start.year}년 {month_start.month}월 월간 봉사 통계",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"✅ 총 봉사 건수: {total_count}건",
            f"✅ 총 봉사자: {total_volunteers:,}명",
            f"✅ 총 수혜자: {total_beneficiary:,}명",
            "",
            "📌 주차별 현황",
        ]

        for r in result_rows:
            lines.append(
                f"  {r[2]}: {r[5]}건 / 봉사자 {r[8]:,}명 / 수혜자 {r[9]:,}명"
            )

        lines.append("")
        lines.append("✅ 월간통계 시트 자동 저장 완료!")

        await bot.send_message(
            chat_id=config.get('my_user_id'),
            text="\n".join(lines)
        )
        print("✅ 월간통계 리포트 발송 완료")

    except Exception as e:
        print(f"❌ 월간통계 발송 오류: {e}")
