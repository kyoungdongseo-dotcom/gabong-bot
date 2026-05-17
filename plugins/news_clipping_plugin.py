"""주간 뉴스클리핑 플러그인.

- 명령어: /send_news, /news_status, /news_collect (관리자 전용)
- 스케줄: 매주 일요일 22:00 KST 자동 후보 수집 → 본인 DM
"""

import sys

print("🔍 news_clipping_plugin: 모듈 import 시작", flush=True)
sys.stdout.flush()

from telegram.ext import CommandHandler

print("🔍 news_clipping_plugin: telegram.ext import 완료", flush=True)
sys.stdout.flush()

from handlers.news_clipping_handler import (
    cmd_news_collect, cmd_news_exclude, cmd_news_status, cmd_send_news,
    scheduled_weekly_collect,
)

print("🔍 news_clipping_plugin: handlers.news_clipping_handler import 완료", flush=True)
sys.stdout.flush()


def register(app, config=None):
    print("🔍 news_clipping_plugin: register() 시작", flush=True)
    app.add_handler(CommandHandler("send_news", cmd_send_news))
    app.add_handler(CommandHandler("news_status", cmd_news_status))
    app.add_handler(CommandHandler("news_collect", cmd_news_collect))
    app.add_handler(CommandHandler("news_exclude", cmd_news_exclude))
    print("✅ /send_news, /news_status, /news_collect, /news_exclude 등록 완료", flush=True)
    print("로딩: news_clipping", flush=True)


async def post_init(app):
    print("🔍 news_clipping_plugin: post_init() 시작", flush=True)
    try:
        from utils import scheduler
        print("🔍 news_clipping_plugin: scheduler import 완료", flush=True)
    except Exception as e:
        print(f"❌ news_clipping scheduler import 실패: {e}", flush=True)
        return

    try:
        cfg = (app.bot_data.get("__news_clipping_cfg__") if hasattr(app, "bot_data") else None) or {}
        import config as _config
        nc = _config.get("news_clipping", {}) or {}
        day_of_week = nc.get("collect_day", "sun")
        hour = int(nc.get("collect_hour", 22))
        print("🔍 news_clipping_plugin: APScheduler cron 등록 시작", flush=True)
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
        print("🔍 news_clipping_plugin: APScheduler cron 등록 완료", flush=True)
        print(f"✅ 주간 뉴스 수집 스케줄 등록 ({day_of_week} {hour:02d}:00 KST)", flush=True)
        _ = cfg
    except Exception as e:
        print(f"❌ news_clipping APScheduler 등록 실패: {e}", flush=True)
        # 등록 실패해도 플러그인 자체는 로딩 계속


print("🔍 news_clipping_plugin: 모듈 import 완료", flush=True)
sys.stdout.flush()
