from telegram import Update
from telegram.ext import ContextTypes
import config
from database import add_reminder, get_reminders, delete_reminder as db_delete_reminder
from utils import get_scheduler, send_reminder, send_broadcast_reminder

DAY_MAP = {"월": "mon", "화": "tue", "수": "wed", "목": "thu",
           "금": "fri", "토": "sat", "일": "sun"}


async def remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /remind_daily HH:MM [내용]")
        return
    time_str = context.args[0]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    topic_id = update.message.message_thread_id
    user_id = update.effective_user.id
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(chat_id, topic_id, "daily", text, time_str, user_id=user_id)
    get_scheduler().add_job(
        send_reminder, 'cron',
        hour=hour, minute=minute,
        args=[context.bot, chat_id, text, topic_id],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매일 {time_str}에 알림 등록! (ID: {reminder_id})")


async def remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_weekly 월,수,금 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    topic_id = update.message.message_thread_id
    user_id = update.effective_user.id
    days_en = ",".join(DAY_MAP[d] for d in days_str.split(","))
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(chat_id, topic_id, "weekly", text, time_str, days_str, user_id=user_id)
    get_scheduler().add_job(
        send_reminder, 'cron',
        day_of_week=days_en, hour=hour, minute=minute,
        args=[context.bot, chat_id, text, topic_id],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 알림 등록! (ID: {reminder_id})")


async def remind_biweekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_biweekly 월 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    topic_id = update.message.message_thread_id
    user_id = update.effective_user.id
    days_en = ",".join(DAY_MAP[d] for d in days_str.split(","))
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(chat_id, topic_id, "biweekly", text, time_str, days_str, user_id=user_id)
    get_scheduler().add_job(
        send_reminder, 'cron',
        day_of_week=days_en, hour=hour, minute=minute, week="*/2",
        args=[context.bot, chat_id, text, topic_id],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 2주마다 {days_str} {time_str}에 알림 등록! (ID: {reminder_id})")


async def remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /remind_monthly 일자 HH:MM [내용]")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    chat_id = update.effective_chat.id
    topic_id = update.message.message_thread_id
    user_id = update.effective_user.id
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(chat_id, topic_id, "monthly", text, time_str,
                               day_of_month=int(day), user_id=user_id)
    get_scheduler().add_job(
        send_reminder, 'cron',
        day=day, hour=hour, minute=minute,
        args=[context.bot, chat_id, text, topic_id],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 알림 등록! (ID: {reminder_id})")


async def broadcast_remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids'):
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("사용법: /broadcast_remind_daily HH:MM [내용]")
        return
    time_str = context.args[0]
    text = update.message.text.split(time_str + " ", 1)[1]
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(0, None, "broadcast_daily", text, time_str)
    get_scheduler().add_job(
        send_broadcast_reminder, 'cron',
        hour=hour, minute=minute,
        args=[context.bot, text],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매일 {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")


async def broadcast_remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids'):
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_weekly 월,수,금 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    days_en = ",".join(DAY_MAP[d] for d in days_str.split(","))
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(0, None, "broadcast_weekly", text, time_str, days_str)
    get_scheduler().add_job(
        send_broadcast_reminder, 'cron',
        day_of_week=days_en, hour=hour, minute=minute,
        args=[context.bot, text],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매주 {days_str} {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")


async def broadcast_remind_biweekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids'):
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_biweekly 월 HH:MM [내용]")
        return
    days_str = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    days_en = ",".join(DAY_MAP[d] for d in days_str.split(","))
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(0, None, "broadcast_biweekly", text, time_str, days_str)
    get_scheduler().add_job(
        send_broadcast_reminder, 'cron',
        day_of_week=days_en, hour=hour, minute=minute, week="*/2",
        args=[context.bot, text],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 2주마다 {days_str} {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")


async def broadcast_remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids'):
        await update.message.reply_text("❌ 권한이 없습니다.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("사용법: /broadcast_remind_monthly 일자 HH:MM [내용]")
        return
    day = context.args[0]
    time_str = context.args[1]
    text = update.message.text.split(time_str + " ", 1)[1]
    hour, minute = map(int, time_str.split(":"))

    reminder_id = add_reminder(0, None, "broadcast_monthly", text, time_str, day_of_month=int(day))
    get_scheduler().add_job(
        send_broadcast_reminder, 'cron',
        day=day, hour=hour, minute=minute,
        args=[context.bot, text],
        id=str(reminder_id)
    )
    await update.message.reply_text(f"✅ 매월 {day}일 {time_str}에 13개 그룹 알림 등록! (ID: {reminder_id})")


async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    chat_id = update.effective_chat.id
    all_reminders = get_reminders()
    reminders = [
        r for r in all_reminders
        if str(r.get("group_id")) == str(chat_id) or r.get("type", "").startswith("broadcast")
    ]

    if not reminders:
        await update.message.reply_text("등록된 리마인더가 없습니다.")
        return

    msg = "⏰ 리마인더 목록\n\n"
    for r in reminders:
        r_type = r.get("type", "")
        rid = r['id']
        time = r.get('time', '')
        msg_text = (r.get('message') or '')[:40]
        dow = r.get('day_of_week', '')
        dom = r.get('day_of_month', '')
        if r_type == "daily":
            msg += f"[{rid}] 매일 {time} - {msg_text}\n"
        elif r_type == "weekly":
            msg += f"[{rid}] 매주 {dow} {time} - {msg_text}\n"
        elif r_type == "biweekly":
            msg += f"[{rid}] 2주마다 {dow} {time} - {msg_text}\n"
        elif r_type == "monthly":
            msg += f"[{rid}] 매월 {dom}일 {time} - {msg_text}\n"
        elif r_type == "broadcast_daily":
            msg += f"[{rid}] [전체] 매일 {time} - {msg_text}\n"
        elif r_type == "broadcast_weekly":
            msg += f"[{rid}] [전체] 매주 {dow} {time} - {msg_text}\n"
        elif r_type == "broadcast_biweekly":
            msg += f"[{rid}] [전체] 2주마다 {dow} {time} - {msg_text}\n"
        elif r_type == "broadcast_monthly":
            msg += f"[{rid}] [전체] 매월 {dom}일 {time} - {msg_text}\n"

    await update.message.reply_text(msg)


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if update.effective_user.id not in config.get('admin_ids', []):
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder [ID]")
        return

    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID는 숫자여야 합니다.")
        return

    db_delete_reminder(reminder_id)
    try:
        get_scheduler().remove_job(str(reminder_id))
    except Exception:
        pass

    await update.message.reply_text(f"✅ 리마인더 {reminder_id} 삭제 완료!")
