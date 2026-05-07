import os
from datetime import datetime
import pytz
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

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
        add_table_row(table, '■ 내부봉사자', f"{report.get('내부봉사자', '-')}명")
        add_table_row(table, '■ 외부봉사자', f"{report.get('외부봉사자', '-')}명")
        add_table_row(table, '■ 총봉사자', f"{report.get('총봉사자', '-')}명")

        doc.add_paragraph()

        add_section(doc, '1. 활동 내용', report.get('활동내용'))
        add_section(doc, '2. 반응 및 특이사항', report.get('반응특이사항'))
        add_section(doc, '3. 참여인사', report.get('참여인사'))
        add_section(doc, '4. 홍보도구', report.get('홍보도구'))
        add_section(doc, '5. 잘된 점', report.get('잘된점'))
        add_section(doc, '6. 개선할 점', report.get('개선할점'))

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
    """보고서 데이터로 Word 파일 생성 후 서무에게 전송"""
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
        print(f"✅ Word 파일 전송 완료: {filename} → {DOCX_RECIPIENT_ID}")
        return True

    except Exception as e:
        print(f"❌ Word 파일 생성/전송 오류: {e}")
        return False
