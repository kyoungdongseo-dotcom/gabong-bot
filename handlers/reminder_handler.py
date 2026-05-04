from telegram import Update
from telegram.ext import ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config
from utils import load_reminders, save_reminders, send_reminder, send_broadcast_reminder

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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "daily", "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "weekly", "days": days_str, "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "biweekly", "days": days_str, "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "monthly", "day": day, "time": time_str, "text": text, "chat_id": chat_id})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "broadcast_daily", "time": time_str, "text": text, "chat_id": 0})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "broadcast_weekly", "days": days_str, "time": time_str, "text": text, "chat_id": 0})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "broadcast_biweekly", "days": days_str, "time": time_str, "text": text, "chat_id": 0})
    save_reminders(reminders)
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
    reminders = load_reminders()
    reminder_id = len(reminders) + 1
    reminders.append({"id": reminder_id, "type": "broadcast_monthly", "day": day, "time": time_str, "text": text, "chat_id": 0})
    save_reminders(reminders)
    scheduler.add_job(send_broadcast_reminder, 'cron', day=day, hour=hour, minute=minute, args=[context.bot, text], id=str(reminder_id))
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")

async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    reminders = [r for r in load_reminders() if r.get("chat_id") == chat_id or r.get("type", "").startswith("broadcast")]
    if not reminders:
        await update.message.reply_text("등록된 리마인더가 없습니다.")
        return
    msg = "⏰ 내 리마인더 목록\n\n"
    for r in reminders:
        if r["type"] == "daily":
            msg += f"ID {r['id']}: 매일 {r['time']} - {r['text']}\n"
        elif r["type"] == "weekly":
            msg += f"ID {r['id']}: 매주 {r['days']} {r['time']} - {r['text']}\n"
        elif r["type"] == "biweekly":
            msg += f"ID {r['id']}: 2주마다 {r['days']} {r['time']} - {r['text']}\n"
        elif r["type"] == "monthly":
            msg += f"ID {r['id']}: 매월 {r['day']}일 {r['time']} - {r['text']}\n"
        elif r["type"] == "broadcast_daily":
            msg += f"ID {r['id']}: [전체] 매일 {r['time']} - {r['text']}\n"
        elif r["type"] == "broadcast_weekly":
            msg += f"ID {r['id']}: [전체] 매주 {r['days']} {r['time']} - {r['text']}\n"
        elif r["type"] == "broadcast_biweekly":
            msg += f"ID {r['id']}: [전체] 2주마다 {r['days']} {r['time']} - {r['text']}\n"
        elif r["type"] == "broadcast_monthly":
            msg += f"ID {r['id']}: [전체] 매월 {r['day']}일 {r['time']} - {r['text']}\n"
    await update.message.reply_text(msg)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder [ID]")
        return
    reminder_id = context.args[0]
    reminders = [r for r in load_reminders() if str(r["id"]) != reminder_id]
    save_reminders(reminders)
    try:
        scheduler.remove_job(reminder_id)
    except:
        pass
    await update.message.reply_text(f"✅ 리마인더 {reminder_id} 삭제 완료!")