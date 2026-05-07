import re
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

def parse_report(text: str) -> dict | None:
    if not text:
        return None

    if '활동보고' not in text and '봉사보고' not in text:
        return None

    if '■ 활동명' not in text and '■활동명' not in text:
        return None

    result = {
        '등록일시': datetime.now(KST).strftime('%Y-%m-%d %H:%M'),
        '지파명': '',
        '교회명': '',
        '활동명': '',
        '봉사분류': '',
        '활동일시': '',
        '활동장소': '',
        '수혜자수': '',
        '내부봉사자': '',
        '외부봉사자': '',
        '총봉사자': '',
        '활동내용': '',
        '반응특이사항': '',
        '참여인사': '',
        '홍보도구': '',
        '잘된점': '',
        '개선할점': '',
        '사진1링크': '',
        '사진2링크': '',
        '사진3링크': '',
        '사진4링크': '',
        '사진5링크': '',
        '원본메시지': text
    }

    title_match = re.search(r'\[(.+?지파)\s*(.+?교회)', text)
    if title_match:
        result['지파명'] = title_match.group(1).strip()
        result['교회명'] = title_match.group(2).strip()

    def extract_field(pattern, text):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ''

    result['활동명'] = extract_field(r'■\s*활동명\s*:\s*(.+?)(?=■|\n\n|$)', text)
    result['봉사분류'] = extract_field(r'■\s*봉사분류\s*:\s*(.+?)(?=■|\n\n|$)', text)
    result['활동일시'] = extract_field(r'■\s*활동일시\s*:\s*(.+?)(?=■|\n\n|$)', text)
    result['활동장소'] = extract_field(r'■\s*활동장소\s*:\s*(.+?)(?=■|\n\n|$)', text)
    result['수혜자수'] = extract_field(r'■\s*수혜자\s*:\s*(\d+)', text)

    inner = extract_field(r'■\s*내부봉사자\s*:\s*(\d+)', text)
    outer = extract_field(r'■\s*외부봉사자\s*:\s*(\d+)', text)
    result['내부봉사자'] = inner
    result['외부봉사자'] = outer

    try:
        result['총봉사자'] = str(int(inner or 0) + int(outer or 0))
    except:
        result['총봉사자'] = ''

    result['활동내용'] = extract_field(r'1\.\s*활동\s*내용(.+?)(?=2\.|$)', text)
    result['반응특이사항'] = extract_field(r'2\.\s*반응\s*및\s*특이\s*사항(.+?)(?=3\.|$)', text)
    result['참여인사'] = extract_field(r'3\.\s*참여인사(.+?)(?=4\.|$)', text)
    result['홍보도구'] = extract_field(r'4\.\s*홍보\s*도구(.+?)(?=5\.|$)', text)
    result['잘된점'] = extract_field(r'5\.\s*잘된\s*점(.+?)(?=6\.|$)', text)
    result['개선할점'] = extract_field(r'6\.\s*개선할\s*점(.+?)$', text)

    return result


def save_report_to_sheet(report: dict, service, spreadsheet_id: str):
    try:
        row = [
            report.get('등록일시', ''),
            report.get('지파명', ''),
            report.get('교회명', ''),
            report.get('활동명', ''),
            report.get('봉사분류', ''),
            report.get('활동일시', ''),
            report.get('활동장소', ''),
            report.get('수혜자수', ''),
            report.get('내부봉사자', ''),
            report.get('외부봉사자', ''),
            report.get('총봉사자', ''),
            report.get('활동내용', ''),
            report.get('반응특이사항', ''),
            report.get('참여인사', ''),
            report.get('홍보도구', ''),
            report.get('잘된점', ''),
            report.get('개선할점', ''),
            report.get('사진1링크', ''),
            report.get('사진2링크', ''),
            report.get('사진3링크', ''),
            report.get('사진4링크', ''),
            report.get('사진5링크', ''),
            report.get('원본메시지', ''),
        ]

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="봉사리포트!A:W",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        print(f"✅ 봉사리포트 저장 완료: {report.get('활동명')}")
        return True

    except Exception as e:
        print(f"❌ 봉사리포트 저장 오류: {e}")
        return False
