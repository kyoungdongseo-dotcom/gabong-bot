import os
import requests
import tempfile
from datetime import datetime
import pytz
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import config

KST = pytz.timezone('Asia/Seoul')
DOCX_RECIPIENT_ID = 754270008

def set_cell_background(cell, color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tcPr.append(shd)

def add_table_row(table, label, value):
    row = table.add_row()
    label_cell = row.cells[0]
    value_cell = row.cells[1]
    label_cell.text = label
    label_cell.paragraphs[0].runs[0].bold = True
    label_cell.paragraphs[0].runs[0].font.size = Pt(10)
    set_cell_background(label_cell, 'D5E8F0')
    value_cell.text = value or '-'
    value_cell.paragraphs[0].runs[0].font.size = Pt(10)

def add_section(doc, title, content):
    p = doc.add_paragraph()
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    content_p = doc.add_paragraph(content or '-')
    content_p.runs[0].font.size = Pt(10)
    content_p.paragraph_format.space_after = Pt(8)

def download_photo(url: str) -> str | None:
    try:
        token = config.get('telegram_token')
        if not url.startswith('http'):
            full_url = f"https://api.telegram.org/file/bot{token}/{url}"
        else:
            full_url = url
        response = requests.get(full_url, timeout=10)
        if response.status_code == 200:
            suffix = '.jpg' if 'jpg' in url.lower() else '.png'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(response.content)
            tmp.close()
            return tmp.name
        return None
    except Exception as e:
        print(f"❌ 사진 다운로드 오류: {e}")
        return None

def add_photos_grid(doc, photo_paths):
    """사진을 2열로 배치 (1페이지 4장)"""
    if not photo_paths:
        return

    p = doc.add_paragraph()
    run = p.add_run('📸 봉사 사진')
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(8)

    # 2장씩 같은 줄에 배치
    for i in range(0, len(photo_paths), 2):
        pair = photo_paths[i:i+2]

        # 2열 테이블 생성
        photo_table = doc.add_table(rows=1, cols=len(pair))

        for j, path in enumerate(pair):
            cell = photo_table.rows[0].cells[j]
            try:
                para = cell.paragraphs[0]
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run()
                run.add_picture(path, width=Cm(8), height=Cm(5))
            except Exception as e:
                print(f"❌ 사진 삽입 오류: {e}")
                cell.paragraphs[0].add_run("사진 오류")

        doc.add_paragraph()

def generate_docx(report: dict, output_path: str) -> bool:
    try:
        doc = Document()

        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(f"{report.get('지파명', '')} {report.get('교회명', '')} 봉사 활동보고")
        run.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        title.paragraph_format.space_after = Pt(6)

        subtitle = doc.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run2 = subtitle.add_run(report.get('활동명', ''))
        run2.font.size = Pt(12)
        run2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
        subtitle.paragraph_format.space_after = Pt(12)

        table = doc.add_table(rows=0, cols=2)
        table.style = 'Table Grid'
        table.columns[0].width = Cm(4)
        table.columns[1].width = Cm(12)

        add_table_row(table, '■ 활동명', report.get('활동명'))
        add_table_row(table, '■ 봉사분류', report.get('봉사분류'))
        add_table_row(table, '■ 활동일시', report.get('활동일시'))
        add_table_row(table, '■ 수혜자', report.get('수혜자수'))
        add_table_row(table, '■ 활동장소', report.get('활동장소'))
        add_table_row(table, '■ 내부봉사자', f"{report.get('내부봉사자', '0')}명")
        add_table_row(table, '■ 외부봉사자', f"{report.get('외부봉사자', '0')}명")
        add_table_row(table, '■ 총봉사자', f"{report.get('총봉사자', '0')}명")

        doc.add_paragraph()

        add_section(doc, '1. 활동 내용', report.get('활동내용'))
        add_section(doc, '2. 반응 및 특이사항', report.get('반응특이사항'))
        add_section(doc, '3. 참여인사', report.get('참여인사'))
        add_section(doc, '4. 홍보도구', report.get('홍보도구'))
        add_section(doc, '5. 잘된 점', report.get('잘된점'))
        add_section(doc, '6. 개선할 점', report.get('개선할점'))

        # 사진 다운로드 및 삽입 (최대 10장)
        photo_urls = [report.get(f'사진{i}링크', '') for i in range(1, 11)
                      if report.get(f'사진{i}링크')]

        if photo_urls:
            tmp_files = []
            failed_count = 0
            for url in photo_urls:
                tmp_path = download_photo(url)
                if tmp_path:
                    tmp_files.append(tmp_path)
                else:
                    failed_count += 1

            if tmp_files:
                add_photos_grid(doc, tmp_files)

            if failed_count > 0:
                note_p = doc.add_paragraph()
                note_run = note_p.add_run(
                    f"⚠️ 사진 {len(tmp_files)}장 첨부 완료 / {failed_count}장 다운로드 실패"
                    " (텔레그램 파일 링크 만료 가능)"
                )
                note_run.font.size = Pt(9)
                note_run.font.color.rgb = RGBColor(0xFF, 0x66, 0x00)

            for tmp_path in tmp_files:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        footer = doc.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run3 = footer.add_run(f"등록일시: {report.get('등록일시', '')}")
        run3.font.size = Pt(9)
        run3.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

        doc.save(output_path)
        print(f"✅ Word 파일 생성 완료: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Word 생성 오류: {e}")
        return False

async def generate_and_send_docx(bot, chat_id, report: dict, message_id: int = None):
    try:
        output_path = f"/tmp/report_{datetime.now(KST).strftime('%Y%m%d_%H%M%S')}.docx"

        success = generate_docx(report, output_path)
        if not success:
            return False

        jipa = report.get('지파명', '')
        church = report.get('교회명', '')
        activity = report.get('활동명', '')
        date = report.get('활동일시', '')[:10] if report.get('활동일시') else ''

        filename = f"{jipa}_{church}_{activity}_{date}.docx"
        filename = filename.replace(' ', '_').replace('/', '-')

        with open(output_path, 'rb') as f:
            await bot.send_document(
                chat_id=DOCX_RECIPIENT_ID,
                document=f,
                filename=filename,
                caption=f"📄 새 봉사보고서 Word 파일\n📌 {jipa} {church}\n📋 {activity}\n📅 {date}"
            )

        os.remove(output_path)
        print(f"✅ Word 파일 전송 완료: {filename}")
        return True

    except Exception as e:
        print(f"❌ Word 파일 생성/전송 오류: {e}")
        return False
