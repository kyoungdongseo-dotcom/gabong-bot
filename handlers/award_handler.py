"""수상보고서 처리 핸들러"""

import asyncio
import os
import re
import tempfile
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

KST = pytz.timezone('Asia/Seoul')

AWARD_SPREADSHEET_ID = '1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4'
AWARD_SHEET_NAME = '수상보고창'
AWARD_GROUP_ID = -1002777848839
AWARD_TOPIC_ID = 3553
AWARD_RECIPIENT_ID = 754270008

HEADERS = ['등록일시', '지역', '지부명', '보고제목', '행사장소', '행사일시',
           '수여자', '수상자', '수상내용', '보고자', '사진링크']


# ── 파싱 ─────────────────────────────────────────────────────────────────────

def parse_award_caption(caption: str) -> dict | None:
    """캡션 파싱. '수상보고서' 없거나 파싱 실패 시 None 반환."""
    if not caption or '수상보고서' not in caption:
        return None

    lines = [l.strip() for l in caption.strip().splitlines() if l.strip()]
    if not lines:
        return None

    # 첫 줄: "[지역] [지부명] 수상보고서"
    지역, 지부명 = '', ''
    m = re.match(r'^(.+?)\s+(.+?지부)\s+수상보고서', lines[0])
    if m:
        지역 = m.group(1).strip()
        지부명 = m.group(2).strip()

    data = {
        '등록일시': datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S'),
        '지역': 지역,
        '지부명': 지부명,
        '보고제목': '',
        '행사장소': '',
        '행사일시': '',
        '수여자': '',
        '수상자': '',
        '수상내용': '',
        '보고자': '',
        '사진링크': '',
    }

    FIELD_KEYS = {'보고제목', '행사장소', '행사일시', '수여자', '수상자', '수상내용', '보고자'}
    for line in lines[1:]:
        if ':' in line:
            key, _, val = line.partition(':')
            key = key.strip()
            if key in FIELD_KEYS:
                data[key] = val.strip()

    return data


# ── Google Sheets ─────────────────────────────────────────────────────────────

def _get_sheet_service():
    scopes = config.get('google_scopes', ['https://www.googleapis.com/auth/spreadsheets'])
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=scopes)
    return build('sheets', 'v4', credentials=creds)


def _ensure_header(service):
    result = service.spreadsheets().values().get(
        spreadsheetId=AWARD_SPREADSHEET_ID,
        range=f'{AWARD_SHEET_NAME}!A1:K1'
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
        print(f"✅ 수상보고서 저장 완료: {data.get('보고제목')}")
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
            f"{data.get('지역', '')} {data.get('지부명', '')}\n자원봉사 수상보고서"
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

        # 행 1: 보고제목 (값 3열 병합)
        r0 = table.add_row()
        _label(r0.cells[0], '보고제목')
        r0.cells[1].merge(r0.cells[3])
        _value(r0.cells[1], data.get('보고제목'))

        # 행 2: 행사장소 | 행사일시
        r1 = table.add_row()
        _label(r1.cells[0], '행사장소')
        _value(r1.cells[1], data.get('행사장소'))
        _label(r1.cells[2], '행사일시')
        _value(r1.cells[3], data.get('행사일시'))

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
        date_p.add_run(data.get('행사일시', '')).font.size = Pt(11)

        reporter_p = doc.add_paragraph()
        reporter_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        reporter_run = reporter_p.add_run(
            f"보고자: {data.get('지부명', '')} {data.get('보고자', '')}"
        )
        reporter_run.font.size = Pt(11)

        doc.save(output_path)
        print(f"✅ 수상보고서 Word 생성 완료: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Word 생성 오류: {e}")
        return False


# ── 메인 핸들러 ───────────────────────────────────────────────────────────────

async def handle_award_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    if chat_id != AWARD_GROUP_ID:
        return
    if thread_id != AWARD_TOPIC_ID:
        return

    caption = update.message.caption or ''
    if '수상보고서' not in caption:
        return

    data = parse_award_caption(caption)
    if not data:
        await context.bot.send_message(
            chat_id=AWARD_RECIPIENT_ID,
            text=f"⚠️ 수상보고서 파싱 실패\n캡션:\n{caption[:300]}"
        )
        return

    # 사진 URL 획득
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)
    photo_url = photo_file.file_path
    data['사진링크'] = photo_url

    loop = asyncio.get_running_loop()

    # 스프레드시트 저장
    sheet_ok = await loop.run_in_executor(None, save_to_sheet, data)

    # 사진 다운로드 + Word 생성
    tmp_photo = await loop.run_in_executor(None, download_photo, photo_url)
    now_str = datetime.now(KST).strftime('%Y%m%d_%H%M%S')
    output_path = f"/tmp/award_{now_str}.docx"
    docx_ok = await loop.run_in_executor(None, generate_docx, data, tmp_photo, output_path)

    if tmp_photo:
        try:
            os.remove(tmp_photo)
        except Exception:
            pass

    # DM: 텍스트 요약
    summary = (
        f"✅ 수상보고서 자동 저장 완료\n"
        f"📌 {data.get('지역')} {data.get('지부명')}\n"
        f"🏆 {data.get('보고제목')}\n"
        f"📅 {data.get('행사일시')}"
    )
    if not sheet_ok:
        summary += "\n⚠️ 스프레드시트 저장 실패"

    await context.bot.send_message(chat_id=AWARD_RECIPIENT_ID, text=summary)

    # DM: Word 파일
    if docx_ok and os.path.exists(output_path):
        filename = (
            f"{data.get('지역', '')}_{data.get('지부명', '')}_수상보고서"
            f"_{datetime.now(KST).strftime('%Y%m%d')}.docx"
        ).replace(' ', '_').replace('/', '-')
        try:
            with open(output_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=AWARD_RECIPIENT_ID,
                    document=f,
                    filename=filename,
                    caption="📄 수상보고서 Word 파일"
                )
        finally:
            try:
                os.remove(output_path)
            except Exception:
                pass
