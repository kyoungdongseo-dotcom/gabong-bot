import re
from datetime import datetime
import pytz
from handlers.report_parser_utils import parse_multiline_kv, extract_first_line_meta

KST = pytz.timezone('Asia/Seoul')

_REPORT_KEY_ALIASES = {
    '활동명': ['활동명', '행사명', '프로그램명'],
    '봉사분류': ['봉사분류', '분류'],
    '활동일시': ['활동일시', '일시', '행사일시'],
    '활동장소': ['활동장소', '장소'],
    '수혜자수': ['수혜자수', '수혜자'],
    '내부봉사자': ['내부봉사자', '내부'],
    '외부봉사자': ['외부봉사자', '외부'],
    '총봉사자': ['총봉사자', '전체봉사자'],
}


def parse_report(text: str) -> dict | None:
    if not text:
        return None
    if '활동보고' not in text and '봉사보고' not in text:
        return None

    result = {
        '등록일시': datetime.now(KST).strftime('%Y-%m-%d %H:%M'),
        '지파명': '', '교회명': '', '활동명': '', '봉사분류': '',
        '활동일시': '', '활동장소': '', '수혜자수': '',
        '내부봉사자': '', '외부봉사자': '', '총봉사자': '',
        '활동내용': '', '반응특이사항': '', '참여인사': '',
        '홍보도구': '', '잘된점': '', '개선할점': '',
        '사진1링크': '', '사진2링크': '', '사진3링크': '',
        '사진4링크': '', '사진5링크': '', '원본메시지': text,
    }

    # 지파명/교회명: 브래킷 형식 우선, 실패 시 첫 줄 토큰
    title_match = re.search(r'\[(.+?지파)\s*(.+?교회)', text)
    if title_match:
        result['지파명'] = title_match.group(1).strip()
        result['교회명'] = title_match.group(2).strip()
    else:
        first_line = text.strip().splitlines()[0]
        p1, p2 = extract_first_line_meta(
            first_line, ['봉사 활동보고', '활동보고', '봉사보고']
        )
        result['지파명'] = p1
        result['교회명'] = p2

    # 메타데이터 필드: 별칭 기반 유연한 파싱
    meta = parse_multiline_kv(text, _REPORT_KEY_ALIASES)
    for field, val in meta.items():
        if val:
            result[field] = val

    # 수혜자 숫자만 추출
    if result['수혜자수']:
        m = re.search(r'(\d+)', result['수혜자수'])
        result['수혜자수'] = m.group(1) if m else result['수혜자수']

    # 봉사자 수 숫자 추출 (없으면 0)
    for field in ['내부봉사자', '외부봉사자']:
        raw = result[field]
        m = re.search(r'(\d+)', raw) if raw else None
        result[field] = m.group(1) if m else '0'

    # 총봉사자 계산 (원본에 없으면)
    if not result['총봉사자']:
        try:
            result['총봉사자'] = str(int(result['내부봉사자'] or 0) + int(result['외부봉사자'] or 0))
        except Exception:
            result['총봉사자'] = '0'

    # 내용 섹션: 번호 기반 파싱 유지 (■ 없이도 동작)
    def _section(pattern):
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ''

    result['활동내용'] = _section(r'1\.\s*활동\s*내용(.+?)(?=2\.|$)')
    result['반응특이사항'] = _section(r'2\.\s*반응\s*및\s*특이\s*사항(.+?)(?=3\.|$)')
    result['참여인사'] = _section(r'3\.\s*참여인사(.+?)(?=4\.|$)')
    result['홍보도구'] = _section(r'4\.\s*홍보\s*도구(.+?)(?=5\.|$)')
    result['잘된점'] = _section(r'5\.\s*잘된\s*점(.+?)(?=6\.|$)')
    result['개선할점'] = _section(r'6\.\s*개선할\s*점(.+?)$')

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
