import json
import os
import subprocess
from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')

GENERATE_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generate_report.js')
DOCX_RECIPIENT_ID = 754270008

async def generate_and_send_docx(bot, chat_id, report: dict, message_id: int = None):
    """보고서 데이터로 Word 파일 생성 후 전송"""
    try:
        output_path = f"/tmp/report_{datetime.now(KST).strftime('%Y%m%d_%H%M%S')}.docx"

        report_json = json.dumps(report, ensure_ascii=False)

        result = subprocess.run(
            ['node', GENERATE_SCRIPT, report_json, output_path],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            print(f"❌ Word 생성 오류: {result.stderr}")
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
