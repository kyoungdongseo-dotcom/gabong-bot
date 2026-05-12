import re
from datetime import datetime
import pytz
from handlers.report_parser_utils import parse_multiline_kv, extract_first_line_meta

KST = pytz.timezone('Asia/Seoul')

_REPORT_KEY_ALIASES = {
    '활동명': ['활동명', '행사명', '프로그램명', '봉사명', '사업명'],
    '봉사분류': ['봉사분류', '분류', '봉사구분', '구분'],
    '활동일시': ['활동일시', '일시', '행사일시', '봉사일시', '일자', '날짜'],
    '활동장소': ['활동장소', '장소', '봉사장소', '행사장소'],
    '수혜자수': ['수혜자수', '수혜자', '수혜인원', '대상'],
    '내부봉사자': ['내부봉사자', '내부', '봉사자수내부'],
    '외부봉사자': ['외부봉사자', '외부'],
    '총봉사자': ['총봉사자', '전체봉사자', '봉사자수', '봉사인원'],
    '활동내용': ['활동내용', '내용', '봉사내용', '활동상세'],
    '반응특이사항': ['반응특이사항', '반응', '특이사항', '반응 및 특이사항'],
    '참여인사': ['참여인사', '참석자', '참가자'],
    '홍보도구': ['홍보도구', '홍보', '홍보물'],
    '잘된점': ['잘된점', '잘된 점', '좋았던점', '우수사항'],
    '개선할점': ['개선할점', '개선할 점', '개선사항', '보완사항'],
}


def parse_report(text: str) -> dict | None:
    if not text:
        return None
    # 띄어쓰기 무시 매칭 (예: "활동 보고", "봉사 보고서", "봉사 활동 보고" 모두 인식)
    # Why: 자연스러운 한국어 띄어쓰기로 silent fail 방지 (2026-05-12)
    if not re.search(r'(활동|봉사)\s*보고', text):
        return None

    result = {
        '등록일시': datetime.now(KST).strftime('%Y-%m-%d %H:%M'),
        '지파명': '', '교회명': '', '활동명': '', '봉사분류': '',
        '활동일시': '', '활동장소': '', '수혜자수': '',
        '내부봉사자': '', '외부봉사자': '', '총봉사자': '',
        '활동내용': '', '반응특이사항': '', '참여인사': '',
        '홍보도구': '', '잘된점': '', '개선할점': '',
        '사진1링크': '', '사진2링크': '', '사진3링크': '',
        '사진4링크': '', '사진5링크': '',
        '사진6링크': '', '사진7링크': '', '사진8링크': '',
        '사진9링크': '', '사진10링크': '',
        '원본메시지': text,
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

    # 내용 섹션: 번호 기반 파싱 (있을 때만 alias 값 덮어쓰기)
    def _section(pattern):
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ''

    for field, pattern in [
        ('활동내용', r'1\.\s*활동\s*내용(.+?)(?=2\.|$)'),
        ('반응특이사항', r'2\.\s*반응\s*및\s*특이\s*사항(.+?)(?=3\.|$)'),
        ('참여인사', r'3\.\s*참여인사(.+?)(?=4\.|$)'),
        ('홍보도구', r'4\.\s*홍보\s*도구(.+?)(?=5\.|$)'),
        ('잘된점', r'5\.\s*잘된\s*점(.+?)(?=6\.|$)'),
        ('개선할점', r'6\.\s*개선할\s*점(.+?)$'),
    ]:
        section_val = _section(pattern)
        if section_val:
            result[field] = section_val

    return result


def save_report_to_sheet(report: dict, service, spreadsheet_id: str):
    """봉사리포트 저장. 기존 A:W 23컬럼 호환을 위해 사진6~10링크는 마지막에 append."""
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
            # 사진 6~10링크는 X~AB 컬럼에 추가 (기존 A:W 컬럼 호환)
            report.get('사진6링크', ''),
            report.get('사진7링크', ''),
            report.get('사진8링크', ''),
            report.get('사진9링크', ''),
            report.get('사진10링크', ''),
        ]

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="봉사리포트!A:AB",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        print(f"✅ 봉사리포트 저장 완료: {report.get('활동명')}")
        return True

    except Exception as e:
        print(f"❌ 봉사리포트 저장 오류: {e}")
        return False
