from telegram.ext import CommandHandler
from handlers.reminder_handler import (
    remind_daily, remind_weekly, remind_biweekly, remind_monthly,
    broadcast_remind_daily, broadcast_remind_weekly, broadcast_remind_biweekly,
    broadcast_remind_monthly, my_reminders, delete_reminder
)
from utils import scheduler, load_reminders, send_reminder, send_broadcast_reminder


def register(app, config):
    app.add_handler(CommandHandler("remind_daily", remind_daily))
    app.add_handler(CommandHandler("remind_weekly", remind_weekly))
    app.add_handler(CommandHandler("remind_biweekly", remind_biweekly))
    app.add_handler(CommandHandler("remind_monthly", remind_monthly))
    app.add_handler(CommandHandler("broadcast_remind_daily", broadcast_remind_daily))
    app.add_handler(CommandHandler("broadcast_remind_weekly", broadcast_remind_weekly))
    app.add_handler(CommandHandler("broadcast_remind_biweekly", broadcast_remind_biweekly))
    app.add_handler(CommandHandler("broadcast_remind_monthly", broadcast_remind_monthly))
    app.add_handler(CommandHandler("my_reminders", my_reminders))
    app.add_handler(CommandHandler("delete_reminder", delete_reminder))


def post_init(app):
    # 기존 job 제거 (중복 방지)
    scheduler.remove_all_jobs()
    
    for r in load_reminders():
        try:
            hour, minute = map(int, r["time"].split(":"))
            if r["type"] == "daily":
                scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "weekly":
                day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                days = ",".join([day_map[d] for d in r["days"].split(",")])
                scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "biweekly":
                day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                days = ",".join([day_map[d] for d in r["days"].split(",")])
                scheduler.add_job(send_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, week="*/2", args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "monthly":
                scheduler.add_job(send_reminder, 'cron', day=r["day"], hour=hour, minute=minute, args=[app.bot, r["chat_id"], r["text"]], id=str(r["id"]))
            elif r["type"] == "broadcast_daily":
                scheduler.add_job(send_broadcast_reminder, 'cron', hour=hour, minute=minute, args=[app.bot, r["text"]], id=str(r["id"]))
            elif r["type"] == "broadcast_weekly":
                day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                days = ",".join([day_map[d] for d in r["days"].split(",")])
                scheduler.add_job(send_broadcast_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, args=[app.bot, r["text"]], id=str(r["id"]))
            elif r["type"] == "broadcast_biweekly":
                day_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                days = ",".join([day_map[d] for d in r["days"].split(",")])
                scheduler.add_job(send_broadcast_reminder, 'cron', day_of_week=days, hour=hour, minute=minute, week="*/2", args=[app.bot, r["text"]], id=str(r["id"]))
            elif r["type"] == "broadcast_monthly":
                scheduler.add_job(send_broadcast_reminder, 'cron', day=r["day"], hour=hour, minute=minute, args=[app.bot, r["text"]], id=str(r["id"]))
        except:
            pass
