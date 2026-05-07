import traceback
from datetime import datetime, timedelta
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import config

KST = pytz.timezone('Asia/Seoul')

def get_sheet_service():
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=config.get('google_scopes'))
    return build('sheets', 'v4', credentials=creds)

def get_this_week_range():
    today = datetime.now(KST).date()
    week_start = today - timedelta(days=today.weekday() + 7)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end

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

def analyze_weekly_report() -> str:
    """주간 봉사 분석 리포트 생성"""
    try:
        rows = read_report_data()
        week_start, week_end = get_this_week_range()

        weekly_rows = []
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
                        if week_start <= date <= week_end:
                            weekly_rows.append(row)
                        break
                    except:
                        continue
            except:
                continue

        if not weekly_rows:
            return (
                f"📊 주간 봉사 분석 리포트\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📅 {week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')}\n\n"
                f"이번 주 등록된 봉사보고서가 없습니다."
            )

        total_count = len(weekly_rows)
        total_inner = sum(int(r[8]) for r in weekly_rows if len(r) > 8 and r[8].isdigit())
        total_outer = sum(int(r[9]) for r in weekly_rows if len(r) > 9 and r[9].isdigit())
        total_volunteers = total_inner + total_outer
        total_beneficiary = sum(int(r[7]) for r in weekly_rows if len(r) > 7 and r[7].isdigit())

        category_count = {}
        for r in weekly_rows:
            if len(r) > 4 and r[4]:
                cat = r[4].strip()
                category_count[cat] = category_count.get(cat, 0) + 1

        jipa_count = {}
        for r in weekly_rows:
            if len(r) > 1 and r[1]:
                jipa = r[1].strip()
                jipa_count[jipa] = jipa_count.get(jipa, 0) + 1

        region_count = {}
        for r in weekly_rows:
            if len(r) > 6 and r[6]:
                region = r[6].strip()
                region_count[region] = region_count.get(region, 0) + 1

        week_num = (week_start.day - 1) // 7 + 1

        lines = [
            f"📊 총회봉사교통부 주간 봉사 분석",
            f"━━━━━━━━━━━━━━━━━━",
            f"📅 {week_start.year}년 {week_start.month}월 {week_num}주차 ({week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')})",
            f"",
            f"✅ 총 봉사 건수: {total_count}건",
            f"✅ 총 봉사자: {total_volunteers:,}명 (내부 {total_inner:,}명 / 외부 {total_outer:,}명)",
            f"✅ 총 수혜자: {total_beneficiary:,}명",
            f"",
            f"📌 봉사분류별",
        ]

        for cat, cnt in sorted(category_count.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  • {cat}: {cnt}건")

        lines.append(f"")
        lines.append(f"📌 지파별 활동 TOP5")
        for i, (jipa, cnt) in enumerate(sorted(jipa_count.items(), key=lambda x: -x[1])[:5], 1):
            lines.append(f"  {i}. {jipa}: {cnt}건")

        lines.append(f"")
        lines.append(f"📌 활동지역 TOP3")
        for i, (region, cnt) in enumerate(sorted(region_count.items(), key=lambda x: -x[1])[:3], 1):
            lines.append(f"  {i}. {region}: {cnt}건")

        return "\n".join(lines)

    except Exception as e:
        print(f"❌ 주간 분석 오류: {e}")
        traceback.print_exc()
        return "주간 분석 리포트 생성 중 오류가 발생했습니다."

async def send_weekly_report(bot):
    """매주 월요일 08:00 관리자 DM으로 발송"""
    try:
        report = analyze_weekly_report()
        admin_id = config.get('my_user_id')
        await bot.send_message(
            chat_id=admin_id,
            text=report
        )
        print(f"✅ 주간 분석 리포트 발송 완료")
    except Exception as e:
        print(f"❌ 주간 분석 리포트 발송 오류: {e}")
