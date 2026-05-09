"""
리마인더 플러그인 — SQLite 단일 저장소
저장: database.py (gabong.db / reminders 테이블)
스케줄러: utils.get_scheduler() (main.py에서 시작한 단일 인스턴스)
"""
from telegram.ext import CommandHandler
from handlers.reminder_handler import (
    remind_daily, remind_weekly, remind_biweekly, remind_monthly,
    broadcast_remind_daily, broadcast_remind_weekly,
    broadcast_remind_biweekly, broadcast_remind_monthly,
    my_reminders, delete_reminder,
)
from database import get_reminders
from utils import get_scheduler, send_reminder, send_broadcast_reminder

DAY_MAP = {"월": "mon", "화": "tue", "수": "wed", "목": "thu",
           "금": "fri", "토": "sat", "일": "sun"}


def _add_job(scheduler, r: dict, bot):
    """
    SQLite reminders 테이블의 row 1건을 스케줄러 job으로 등록.
    스케줄러가 이미 실행 중일 때 호출되므로 replace_existing=True.

    SQLite 필드:
      id (int), group_id (str), type (str), message (str),
      time ("HH:MM"), day_of_week ("월,수"), day_of_month (int)
    """
    rid = str(r["id"])
    r_type = r.get("type", "")
    time_str = r.get("time") or "00:00"
    message = r.get("message", "")
    group_id = r.get("group_id")  # send_reminder가 내부적으로 GROUP_ID 사용

    try:
        hour, minute = map(int, time_str.split(":"))
    except Exception as e:
        print(f"[리마인더] 시간 파싱 실패 id={rid}: {time_str} ({e})")
        return

    try:
        if r_type == "daily":
            scheduler.add_job(
                send_reminder, 'cron',
                hour=hour, minute=minute,
                args=[bot, group_id, message],
                id=rid, replace_existing=True
            )

        elif r_type in ("weekly", "biweekly"):
            day_of_week_kr = r.get("day_of_week") or ""
            days_en = ",".join(
                DAY_MAP.get(d.strip(), d.strip())
                for d in day_of_week_kr.split(",")
                if d.strip()
            )
            kw = dict(
                day_of_week=days_en,
                hour=hour, minute=minute,
                args=[bot, group_id, message],
                id=rid, replace_existing=True
            )
            if r_type == "biweekly":
                kw["week"] = "*/2"
            scheduler.add_job(send_reminder, 'cron', **kw)

        elif r_type == "monthly":
            scheduler.add_job(
                send_reminder, 'cron',
                day=r.get("day_of_month", 1),
                hour=hour, minute=minute,
                args=[bot, group_id, message],
                id=rid, replace_existing=True
            )

        elif r_type == "broadcast_daily":
            scheduler.add_job(
                send_broadcast_reminder, 'cron',
                hour=hour, minute=minute,
                args=[bot, message],
                id=rid, replace_existing=True
            )

        elif r_type in ("broadcast_weekly", "broadcast_biweekly"):
            day_of_week_kr = r.get("day_of_week") or ""
            days_en = ",".join(
                DAY_MAP.get(d.strip(), d.strip())
                for d in day_of_week_kr.split(",")
                if d.strip()
            )
            kw = dict(
                day_of_week=days_en,
                hour=hour, minute=minute,
                args=[bot, message],
                id=rid, replace_existing=True
            )
            if r_type == "broadcast_biweekly":
                kw["week"] = "*/2"
            scheduler.add_job(send_broadcast_reminder, 'cron', **kw)

        elif r_type == "broadcast_monthly":
            scheduler.add_job(
                send_broadcast_reminder, 'cron',
                day=r.get("day_of_month", 1),
                hour=hour, minute=minute,
                args=[bot, message],
                id=rid, replace_existing=True
            )

        else:
            print(f"[리마인더] 알 수 없는 type 무시: {r_type} (id={rid})")
            return

        print(f"[리마인더] 복원 완료: id={rid} type={r_type} time={time_str}")

    except Exception as e:
        print(f"[리마인더] 복원 실패 id={rid}: {e}")


def post_init(app):
    """
    봇 시작 시 main.py의 post_init에서 호출됨.
    scheduler.start() 이후에 실행되므로 바로 add_job 가능.
    """
    scheduler = get_scheduler()

    # 기존 시스템 job(daily_summary 등)은 건드리지 않고 리마인더만 제거 후 재등록
    existing_ids = {job.id for job in scheduler.get_jobs()}
    system_ids = {"daily_summary", "weekly_report_analyzer", "monthly_stats"}

    for job_id in existing_ids - system_ids:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

    reminders = get_reminders()  # SQLite에서 is_active=1인 전체 리마인더
    restored = 0
    for r in reminders:
        _add_job(scheduler, r, app.bot)
        restored += 1

    print(f"[리마인더] 봇 재시작 후 {restored}개 복원 완료")


def register(app, config=None):
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
    print("✅ 리마인더 핸들러 등록 완료")
