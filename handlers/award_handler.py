"""수상보고서 처리 핸들러"""

import asyncio
import os
import re
import tempfile
import time
from datetime import datetime

import pytz
import requests
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ContextTypes

import config
from handlers.report_parser_utils import parse_multiline_kv, extract_first_line_meta

KST = pytz.timezone('Asia/Seoul')

AWARD_SPREADSHEET_ID = '1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4'
AWARD_SHEET_NAME = '수상보고창'
AWARD_GROUP_ID = -1002777848839
AWARD_TOPIC_ID = 3553
AWARD_RECIPIENT_ID = 754270008

HEADERS = ['등록일시', '지역', '지부', '수상명', '수상일시', '장소',
           '수여자', '수상자', '수상내용', '사진링크']

AWARD_PENDING_REPORTS = {}   # (chat_id, topic_id) -> {data, photos, saved, last_photo_time, created}
AWARD_PENDING_PHOTOS = {}    # (chat_id, topic_id) -> {photos, created}
AWARD_PHOTOS_TTL = 300       # 5분

ADMIN_USER_ID = 97057565


def _alias_hint(field: str) -> str:
    aliases = AWARD_KEY_ALIASES.get(field, [field]) if 'AWARD_KEY_ALIASES' in globals() else [field]
    return f"{field} (다음 중 하나로 입력 가능: {', '.join(aliases)})"


async def _notify_admin(context, error_text: str):
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=error_text[:4000])
    except Exception as e:
        print(f"❌ 관리자 알림 실패: {e}")


async def _send_to_recipient(context, **kwargs):
    """서무 DM 전송, 실패 시 관리자 백업 알림"""
    try:
        if 'document' in kwargs:
            await context.bot.send_document(chat_id=AWARD_RECIPIENT_ID, **kwargs)
        else:
            await context.bot.send_message(chat_id=AWARD_RECIPIENT_ID, **kwargs)
        return True
    except Exception as e:
        await _notify_admin(context, f"❌ 수상보고서 서무 DM 실패: {e}\n내용: {str(kwargs.get('text', ''))[:300]}")
        return False


# ── 파싱 ─────────────────────────────────────────────────────────────────────

AWARD_KEY_ALIASES = {
    '수상명': ['수상명', '보고제목', '내용', '행사명', '표창명', '상명'],
    '수상일시': ['수상일시', '행사일시', '일시', '일자', '날짜'],
    '수여자': ['수여자', '시상자'],
    '수상자': ['수상자'],
    '수상내용': ['수상내용', '수상내역', '내역'],
    '장소': ['장소', '행사장소'],
}
REQUIRED_FIELDS = {'수상명', '수상일시', '수상자'}


def parse_award_caption(caption: str) -> dict | None:
    if not caption:
        return None
    if '수상' not in caption or '보고' not in caption:
        return None
    lines = [l.strip() for l in caption.strip().splitlines() if l.strip()]
    if not lines:
        return None
    지역, 지부 = extract_first_line_meta(
        lines[0], ['수상보고서', '수상보고', '보고서', '보고']
    )
    body = '\n'.join(lines[1:])
    meta = parse_multiline_kv(body, AWARD_KEY_ALIASES)
    data: dict = {
        '등록일시': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S'),
        '지역': 지역, '지부': 지부, '사진링크': '',
    }
    data.update(meta)
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        data['_missing'] = missing
    return data


# ── Google Sheets ─────────────────────────────────────────────────────────────

def _get_sheet_service():
    scopes = config.get('google_scopes', ['https://www.googleapis.com/auth/spreadsheets'])
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=scopes)
    return build('sheets', 'v4', credentials=creds)


def _ensure_header(service):
    result = service.spreadsheets().values().get(
        spreadsheetId=AWARD_SPREADSHEET_ID,
        range=f'{AWARD_SHEET_NAME}!A1:J1'
    ).execute()
    existing = result.get('values', [[]])
    if not existing or not any(existing[0]):
        service.spreadsheets().values().update(
            spreadsheetId=AWARD_SPREADSHEET_ID,
            range=f'{AWARD_SHEET_NAME}!A1',
            valueInputOption='RAW',
            body={'values': [HEADERS]}
        ).execute()


def save_to_sheet(data: dict) -> bool:
    try:
        service = _get_sheet_service()
        _ensure_header(service)
        row = [data.get(h, '') for h in HEADERS]
        service.spreadsheets().values().append(
            spreadsheetId=AWARD_SPREADSHEET_ID,
            range=f'{AWARD_SHEET_NAME}!A:K',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()
        print(f"✅ 수상보고서 저장 완료: {data.get('수상명')}")
        return True
    except Exception as e:
        print(f"❌ 수상보고서 저장 오류: {e}")
        return False


# ── 사진 다운로드 ─────────────────────────────────────────────────────────────

def download_photo(url: str) -> str | None:
    try:
        token = config.get('telegram_token')
        full_url = url if url.startswith('http') else f"https://api.telegram.org/file/bot{token}/{url}"
        resp = requests.get(full_url, timeout=10)
        if resp.status_code == 200:
            suffix = '.jpg' if 'jpg' in url.lower() else '.png'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(resp.content)
            tmp.close()
            return tmp.name
        return None
    except Exception as e:
        print(f"❌ 사진 다운로드 오류: {e}")
        return None


# ── Word 생성 ─────────────────────────────────────────────────────────────────

def _set_cell_bg(cell, color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tcPr.append(shd)


def _set_para_bg(para, color: str):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    pPr.append(shd)


def _label(cell, text: str):
    cell.text = text
    run = cell.paragraphs[0].runs[0]
    run.bold = True
    run.font.size = Pt(10)
    _set_cell_bg(cell, 'D5E8F0')


def _value(cell, text: str):
    cell.text = text or '-'
    cell.paragraphs[0].runs[0].font.size = Pt(10)


def generate_docx(data: dict, photo_path: str | None, output_path: str) -> bool:
    try:
        doc = Document()
        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        # 1. 제목
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(
            f"{data.get('지역', '')} {data.get('지부', '')}\n자원봉사 수상보고서"
        )
        title_run.bold = True
        title_run.font.size = Pt(16)
        title_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        title_p.paragraph_format.space_after = Pt(12)

        # 2. 정보 테이블 (4열: label/value/label/value)
        table = doc.add_table(rows=0, cols=4)
        table.style = 'Table Grid'
        table.columns[0].width = Cm(3)
        table.columns[1].width = Cm(5.5)
        table.columns[2].width = Cm(3)
        table.columns[3].width = Cm(4.5)

        # 행 1: 수상명 (값 3열 병합)
        r0 = table.add_row()
        _label(r0.cells[0], '수상명')
        r0.cells[1].merge(r0.cells[3])
        _value(r0.cells[1], data.get('수상명'))

        # 행 2: 장소 | 수상일시
        r1 = table.add_row()
        _label(r1.cells[0], '장소')
        _value(r1.cells[1], data.get('장소'))
        _label(r1.cells[2], '수상일시')
        _value(r1.cells[3], data.get('수상일시'))

        # 행 3: 수여자 | 수상자
        r2 = table.add_row()
        _label(r2.cells[0], '수여자')
        _value(r2.cells[1], data.get('수여자'))
        _label(r2.cells[2], '수상자')
        _value(r2.cells[3], data.get('수상자'))

        # 행 4: 수상내용 (값 3열 병합)
        r3 = table.add_row()
        _label(r3.cells[0], '수상내용')
        r3.cells[1].merge(r3.cells[3])
        _value(r3.cells[1], data.get('수상내용'))

        doc.add_paragraph()

        # 3. 사진 섹션
        photo_title = doc.add_paragraph()
        photo_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pt_run = photo_title.add_run('상장, 상패 사진')
        pt_run.bold = True
        pt_run.font.size = Pt(11)
        _set_para_bg(photo_title, 'CCCCCC')
        photo_title.paragraph_format.space_after = Pt(6)

        if photo_path and os.path.exists(photo_path):
            try:
                photo_p = doc.add_paragraph()
                photo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                photo_p.add_run().add_picture(photo_path, width=Cm(12))
            except Exception as e:
                print(f"❌ 사진 삽입 오류: {e}")
                doc.add_paragraph('[사진 삽입 실패]').alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            doc.add_paragraph('[사진 없음]').alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph()

        # 4. 하단
        footer_p = doc.add_paragraph()
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_p.add_run('위와 같이 보고합니다.\n').font.size = Pt(11)

        date_p = doc.add_paragraph()
        date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_p.add_run(data.get('수상일시', '')).font.size = Pt(11)

        reporter_p = doc.add_paragraph()
        reporter_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        reporter_run = reporter_p.add_run(
            f"{data.get('지역', '')} {data.get('지부', '')}"
        )
        reporter_run.font.size = Pt(11)

        doc.save(output_path)
        print(f"✅ 수상보고서 Word 생성 완료: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Word 생성 오류: {e}")
        return False


# ── 사진 대기 관리 ─────────────────────────────────────────────────────────────

def _award_key(chat_id: int, thread_id):
    return (chat_id, thread_id or 0)


def _cleanup_award_photos():
    now = time.time()
    expired = [k for k, v in list(AWARD_PENDING_PHOTOS.items())
               if now - v.get('created', 0) > AWARD_PHOTOS_TTL]
    for k in expired:
        AWARD_PENDING_PHOTOS.pop(k, None)


async def _finalize_award(context, data: dict, photos: list):
    try:
        if photos:
            data['사진링크'] = photos[0]
        loop = asyncio.get_running_loop()

        # 시트 저장
        try:
            sheet_ok = await loop.run_in_executor(None, save_to_sheet, data)
        except Exception as e:
            sheet_ok = False
            print(f"❌ 수상 시트 저장 예외: {e}")

        # 사진 다운로드
        tmp_photo = None
        photo_failed = False
        if data.get('사진링크'):
            try:
                tmp_photo = await loop.run_in_executor(None, download_photo, data['사진링크'])
                photo_failed = (tmp_photo is None)
            except Exception as e:
                photo_failed = True
                print(f"❌ 수상 사진 다운로드 예외: {e}")

        # Word 생성
        now_str = datetime.now(KST).strftime('%Y%m%d_%H%M%S')
        output_path = f"/tmp/award_{now_str}.docx"
        try:
            docx_ok = await loop.run_in_executor(None, generate_docx, data, tmp_photo, output_path)
        except Exception as e:
            docx_ok = False
            print(f"❌ 수상 Word 생성 예외: {e}")

        if tmp_photo:
            try:
                os.remove(tmp_photo)
            except Exception:
                pass

        # 요약 DM
        summary = (
            f"{'✅' if sheet_ok else '⚠️'} 수상보고서 처리 결과\n"
            f"📌 {data.get('지역')} {data.get('지부')}\n"
            f"🏆 {data.get('수상명')}\n"
            f"📅 {data.get('수상일시')}"
        )
        warnings = []
        if not sheet_ok:
            warnings.append("스프레드시트 저장 실패 — 수동 저장 필요")
        if not docx_ok:
            warnings.append("Word 파일 생성 실패 — 텍스트만 저장됨")
        if photo_failed:
            warnings.append("사진 다운로드 실패 (파일 링크 만료 가능)")
        if warnings:
            summary += "\n\n⚠️ " + "\n⚠️ ".join(warnings)

        await _send_to_recipient(context, text=summary)

        # Word 파일 전송
        if docx_ok and os.path.exists(output_path):
            filename = (
                f"{data.get('지역', '')}_{data.get('지부', '')}_수상보고서"
                f"_{datetime.now(KST).strftime('%Y%m%d')}.docx"
            ).replace(' ', '_').replace('/', '-')
            try:
                with open(output_path, 'rb') as f:
                    await _send_to_recipient(
                        context, document=f, filename=filename,
                        caption="📄 수상보고서 Word 파일"
                    )
            finally:
                try:
                    os.remove(output_path)
                except Exception:
                    pass
    except Exception as e:
        import traceback
        await _notify_admin(
            context,
            f"❌ 수상보고서 처리 중 예외 발생: {e}\n"
            f"데이터: {str(data)[:300]}\n"
            f"{traceback.format_exc()[:1000]}"
        )


async def _flush_award_report(context, key):
    """60초 기다린 후, 사진이 계속 오면 5초씩 연장 (최대 5분)"""
    start = time.time()
    await asyncio.sleep(60)
    while True:
        entry = AWARD_PENDING_REPORTS.get(key)
        if not entry or entry.get('saved'):
            return
        last_photo = entry.get('last_photo_time', 0)
        elapsed = time.time() - start
        if last_photo > 0 and (time.time() - last_photo) < 5 and elapsed < 300:
            await asyncio.sleep(5)
            continue
        break
    entry = AWARD_PENDING_REPORTS.pop(key, None)
    if not entry or entry.get('saved'):
        return
    entry['saved'] = True
    await _finalize_award(context, entry['data'], entry['photos'])


# ── 메인 핸들러 ───────────────────────────────────────────────────────────────

def _award_parse_and_check(text: str, source_label: str, bot_coro_factory):
    """parse 후 누락 필드 확인. (코루틴 팩토리 패턴 대신 직접 반환)"""
    pass  # 아래 핸들러에서 인라인으로 처리


async def handle_award_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사진 수신 처리 — 캡션 있음/없음 모두 대응 (케이스 A~G)"""
    if not update.message or not update.message.photo:
        return
    if update.effective_chat.id != AWARD_GROUP_ID:
        return
    if update.message.message_thread_id != AWARD_TOPIC_ID:
        return

    caption = update.message.caption or ''
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_url = photo_file.file_path
    key = _award_key(update.effective_chat.id, update.message.message_thread_id)

    # 케이스 A/B: 사진+캡션 → 즉시 처리
    if caption and '수상' in caption and '보고' in caption:
        data = parse_award_caption(caption)
        if not data:
            await _send_to_recipient(
                context,
                text=f"⚠️ 수상보고서 파싱 실패 (수상+보고 키워드 필요)\n캡션:\n{caption[:300]}"
            )
            return
        if '_missing' in data:
            hints = '\n  - '.join(_alias_hint(f) for f in data['_missing'])
            await _send_to_recipient(
                context,
                text=f"⚠️ 수상보고서 필수 항목 누락:\n  - {hints}\n\n캡션:\n{caption[:300]}"
            )
            return
        await _finalize_award(context, data, [photo_url])
        return

    # 케이스 C/D/G: 텍스트 보고서 등록 후 사진 도착
    if key in AWARD_PENDING_REPORTS and not AWARD_PENDING_REPORTS[key].get('saved'):
        AWARD_PENDING_REPORTS[key]['photos'].append(photo_url)
        AWARD_PENDING_REPORTS[key]['last_photo_time'] = time.time()
        return

    # 케이스 F: 사진 먼저 도착 → PENDING_PHOTOS 보관
    _cleanup_award_photos()
    if key not in AWARD_PENDING_PHOTOS:
        AWARD_PENDING_PHOTOS[key] = {'photos': [], 'created': time.time()}
    AWARD_PENDING_PHOTOS[key]['photos'].append(photo_url)


async def handle_award_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """텍스트 보고서 수신 → PENDING 등록 (케이스 C~G 지원)"""
    if not update.message or not update.message.text:
        return
    if update.effective_chat.id != AWARD_GROUP_ID:
        return
    if update.message.message_thread_id != AWARD_TOPIC_ID:
        return
    text = update.message.text
    if '수상' not in text or '보고' not in text:
        return
    data = parse_award_caption(text)
    if not data:
        return
    if '_missing' in data:
        hints = '\n  - '.join(_alias_hint(f) for f in data['_missing'])
        await _send_to_recipient(
            context,
            text=f"⚠️ 수상보고서 필수 항목 누락:\n  - {hints}\n\n텍스트:\n{text[:300]}"
        )
        return
    key = _award_key(update.effective_chat.id, update.message.message_thread_id)
    # 케이스 F/G: 먼저 도착한 사진 연결
    pre_photos: list = []
    if key in AWARD_PENDING_PHOTOS:
        pre_photos = AWARD_PENDING_PHOTOS.pop(key)['photos']
    AWARD_PENDING_REPORTS[key] = {
        'data': data, 'photos': pre_photos, 'saved': False,
        'last_photo_time': time.time() if pre_photos else 0,
        'created': time.time(),
    }
    asyncio.create_task(_flush_award_report(context, key))
