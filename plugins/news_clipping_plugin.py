"""주간 뉴스클리핑 플러그인.

- 명령어: /send_news, /news_status, /news_collect (관리자 전용)
- 스케줄: 매주 일요일 22:00 KST 자동 후보 수집 → 본인 DM
"""

from telegram.ext import CommandHandler

from handlers.news_clipping_handler import (
    cmd_news_collect, cmd_news_status, cmd_send_news,
    scheduled_weekly_collect,
)


def register(app, config=None):
    app.add_handler(CommandHandler("send_news", cmd_send_news))
    app.add_handler(CommandHandler("news_status", cmd_news_status))
    app.add_handler(CommandHandler("news_collect", cmd_news_collect))
    print("✅ /send_news, /news_status, /news_collect 등록 완료")
    print("로딩: news_clipping")


async def post_init(app):
    from utils import scheduler
    try:
        cfg = (app.bot_data.get("__news_clipping_cfg__") if hasattr(app, "bot_data") else None) or {}
        import config as _config
        nc = _config.get("news_clipping", {}) or {}
        day_of_week = nc.get("collect_day", "sun")
        hour = int(nc.get("collect_hour", 22))
        scheduler.add_job(
            scheduled_weekly_collect,
            "cron",
            day_of_week=day_of_week,
            hour=hour,
            minute=0,
            args=[app.bot],
            id="weekly_news_collect",
            replace_existing=True,
            timezone="Asia/Seoul",
        )
        print(f"✅ 주간 뉴스 수집 스케줄 등록 ({day_of_week} {hour:02d}:00 KST)")
        _ = cfg
    except Exception as e:
        print(f"⚠️ 주간 뉴스 수집 스케줄 등록 실패: {e}")
