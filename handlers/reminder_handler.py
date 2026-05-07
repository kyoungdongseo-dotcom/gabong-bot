from telegram import Update
from telegram.ext import ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config
from database import add_reminder, get_reminders, delete_reminder as db_delete_reminder
from utils import send_reminder, send_broadcast_reminder

scheduler = AsyncIOScheduler()

async def remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /remind_daily HH:MM [내용]")
        return
    time_str = context.args[0]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(chat_id, None, "daily", text, time_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매일 {time_str}에 알림 등록! (ID: {reminder_id})")

async def remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_weekly 월,수,금 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(chat_id, None, "weekly", text, time_str, days_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 알림 등록! (ID: {reminder_id})")

async def remind_biweekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_biweekly 월 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(chat_id, None, "biweekly", text, time_str, days_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, week="*/2", args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 2주마다 {days_str} {time_str}에 알림 등록! (ID: {reminder_id})")

async def remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_monthly 일자 HH:MM [내용]")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(chat_id, None, "monthly", text, time_str, day_of_month=int(day))
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_reminder, 'cron', day=day, hour=hour, minute=minute, args=[context.bot, chat_id, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 알림 등록! (ID: {reminder_id})")

async def broadcast_remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /broadcast_remind_daily HH:MM [내용]")
        return
    time_str = context.args[0]
    text = update.message.text.split(time_str + " ", 1)[1]
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(0, None, "broadcast_daily", text, time_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_broadcast_reminder, 'cron', hour=hour, minute=minute, args=[context.bot, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매일 {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")

async def broadcast_remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_weekly 월,수,금 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(0, None, "broadcast_weekly", text, time_str, days_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_broadcast_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[context.bot, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")

async def broadcast_remind_biweekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_biweekly 월 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
    days = ",".join([day_map[d] for d in days_str.split(",")])
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(0, None, "broadcast_biweekly", text, time_str, days_str)
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_broadcast_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, week="*/2", args=[context.bot, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 2주마다 {days_str} {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")

async def broadcast_remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    ADMIN_IDS = config.get('admin_ids')
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_monthly 일자 HH:MM [내용]")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    hour, minute = map(int, time_str.split(":"))
    
    add_reminder(0, None, "broadcast_monthly", text, time_str, day_of_month=int(day))
    reminders = get_reminders()
    reminder_id = reminders[-1]['id'] if reminders else 1
    
    scheduler.add_job(send_broadcast_reminder, 'cron', day=day, hour=hour, minute=minute, args=[context.bot, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")

async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    all_reminders = get_reminders()
    reminders = [r for r in all_reminders if r.get("group_id") == chat_id or r.get("type", "").startswith("broadcast")]
    
    if not reminders:
        await update.message.reply_text("등록된 리마인더가 없습니다.")
        return
    
    msg = "⏰ 내 리마인더 목록\n\n"
    for r in reminders:
        r_type = r.get("type")
        if r_type == "daily":
            msg += f"ID {r['id']}: 매일 {r['time']} - {r['message']}\n"
        elif r_type == "weekly":
            msg += f"ID {r['id']}: 매주 {r['day_of_week']} {r['time']} - {r['message']}\n"
        elif r_type == "biweekly":
            msg += f"ID {r['id']}: 2주마다 {r['day_of_week']} {r['time']} - {r['message']}\n"
        elif r_type == "monthly":
            msg += f"ID {r['id']}: 매월 {r['day_of_month']}일 {r['time']} - {r['message']}\n"
        elif r_type == "broadcast_daily":
            msg += f"ID {r['id']}: [전체] 매일 {r['time']} - {r['message']}\n"
        elif r_type == "broadcast_weekly":
            msg += f"ID {r['id']}: [전체] 매주 {r['day_of_week']} {r['time']} - {r['message']}\n"
        elif r_type == "broadcast_biweekly":
            msg += f"ID {r['id']}: [전체] 2주마다 {r['day_of_week']} {r['time']} - {r['message']}\n"
        elif r_type == "broadcast_monthly":
            msg += f"ID {r['id']}: [전체] 매월 {r['day_of_month']}일 {r['time']} - {r['message']}\n"
    
    await update.message.reply_text(msg)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder [ID]")
        return
    
    reminder_id = int(context.args[0])
    db_delete_reminder(reminder_id)
    
    try:
        scheduler.remove_job(str(reminder_id))
    except:
        pass
    
    await update.message.reply_text(f"✅ 리마인더 {reminder_id} 삭제 완료!")
