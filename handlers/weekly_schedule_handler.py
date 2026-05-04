from telegram import Update
from telegram.ext import ContextTypes
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import config
from datetime import datetime, timedelta

async def send_weekly_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """매주 월요일 주간 스케줄 발송"""
    try:
        creds = Credentials.from_service_account_file(
            'serviceAccountKey.json',
            scopes=config.get('google_scopes')
        )
        service = build('sheets', 'v4', credentials=creds)
        
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        sheet_id = config.get('weekly_schedule_sheet_id')
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='B47:G49'
        ).execute()
        
        values = result.get('values', [])
        
        schedule_text = f"📅 **주간 스케줄**\n{monday.strftime('%Y년 %m월 %d일')} ~ {sunday.strftime('%m월 %d일')}\n\n"
        
        days = ['월', '화', '수', '목', '금', '토']
        
        for i, day in enumerate(days):
            day_schedule = []
            for row in values:
                if len(row) > i and row[i]:
                    item = row[i].strip()
                    if item and not item.isdigit():
                        day_schedule.append(item)
            
            if day_schedule:
                schedule_text += f"**{day}요일:**\n"
                for item in day_schedule:
                    schedule_text += f"  • {item}\n"
                schedule_text += "\n"
        
        MAX_MESSAGE_LENGTH = 4000
        if len(schedule_text) > MAX_MESSAGE_LENGTH:
            schedule_text = schedule_text[:MAX_MESSAGE_LENGTH] + "\n\n...(내용 생략)"
        
        await context.bot.send_message(
            chat_id=config.get('group_id'),
            message_thread_id=config.get('topic_id'),
            text=schedule_text,
            parse_mode='Markdown'
        )
        
        print("✅ 주간 스케줄 발송 완료")
        
    except Exception as e:
        print(f"❌ 주간 스케줄 발송 실패: {e}")
        await context.bot.send_message(
            chat_id=config.get('my_user_id'),
            text=f"⚠️ 주간 스케줄 발송 중 오류 발생:\n{str(e)}"
        )


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자가 /schedule 명령어로 호출할 때 주간 스케줄 발송"""
    await send_weekly_schedule(update, context)
