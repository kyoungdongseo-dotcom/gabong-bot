from dotenv import load_dotenv
load_dotenv()
import asyncio
import atexit
import os
import signal
import time
import pkgutil
import importlib
from pathlib import Path
from telegram import BotCommand
from telegram.ext import ApplicationBuilder
import config
from utils import init_database, scheduler, send_daily_summary, check_changes
from handlers.weekly_report_analyzer import send_weekly_report
from handlers.monthly_stats_handler import send_monthly_stats
from handlers.backup_handler import run_backup

PID_FILE = "./data/bot.pid"


def _cleanup_pid():
    """정상 종료 시 PID 파일 제거 (atexit 등록용)"""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                if f.read().strip() == str(os.getpid()):
                    os.remove(PID_FILE)
    except Exception:
        pass


def ensure_single_instance():
    """이전 봇 프로세스 종료 후 현재 PID 저장"""
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            print(f"[PID] 이전 봇(PID {old_pid}) 종료 요청")
            time.sleep(2)
        except (ProcessLookupError, ValueError):
            pass
        except PermissionError:
            print(f"[PID] 이전 봇 종료 권한 없음 - 무시")
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(_cleanup_pid)
    print(f"[PID] 현재 봇 PID {os.getpid()} 등록")


ensure_single_instance()

PLUGIN_DIRECTORY = Path("plugins")


def load_plugins(enabled_names):
    plugins = []
    if not PLUGIN_DIRECTORY.exists():
        print("plugins 디렉토리가 존재하지 않습니다.")
        return plugins

    for finder, module_name, ispkg in pkgutil.iter_modules([str(PLUGIN_DIRECTORY)]):
        if not module_name.endswith("_plugin"):
            continue
        plugin_name = module_name[: -len("_plugin")]
        if enabled_names and plugin_name not in enabled_names:
            continue
        try:
            module = importlib.import_module(f"plugins.{module_name}")
            plugins.append((plugin_name, module))
            print(f"로딩된 플러그인: {plugin_name}")
        except Exception as e:
            print(f"플러그인 로드 실패: {module_name} -> {e}")
    return plugins


def _startup_checks():
    """봇 시작 시 필수 환경 자가 진단 (경고만, 크래시 없음)"""
    ok = True

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️ [진단] ANTHROPIC_API_KEY 미설정 → /ai 기능 불가")
        ok = False

    for fname in ("credentials.json", "serviceAccountKey.json"):
        if not os.path.exists(fname):
            print(f"⚠️ [진단] {fname} 없음 → Google Sheets 연동 불가")
            ok = False

    required_keys = ["telegram_token", "group_id", "admin_ids", "spreadsheet_id"]
    for key in required_keys:
        if not config.get(key):
            print(f"⚠️ [진단] config.json 필수 키 누락: {key}")
            ok = False

    try:
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect("./data/gabong.db")
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        print(f"⚠️ [진단] SQLite 접근 실패: {e}")
        ok = False

    if ok:
        print("✅ [진단] 모든 환경 점검 통과")


async def post_init(app):
    _startup_checks()
    init_database()
    loop = asyncio.get_running_loop()
    scheduler.configure(event_loop=loop)
    scheduler.start()

    await app.bot.set_my_commands([
        BotCommand("start", "봇 시작"),
        BotCommand("notice", "공지 발송"),
        BotCommand("broadcast", "전체 그룹 공지"),
        BotCommand("ai", "AI 응답"),
        BotCommand("summary", "대화 요약"),
        BotCommand("reset", "대화 초기화"),
        BotCommand("remind_daily", "매일 리마인더 등록"),
        BotCommand("remind_weekly", "매주 리마인더 등록"),
        BotCommand("remind_monthly", "매월 리마인더 등록"),
        BotCommand("my_reminders", "내 리마인더 목록"),
        BotCommand("delete_reminder", "리마인더 삭제"),
        BotCommand("schedule", "주간 봉사 일정"),
        BotCommand("report", "주간 봉사 분석 리포트"),
        BotCommand("monthly", "월간 봉사 통계"),
        BotCommand("backup", "즉시 DB 백업"),
        BotCommand("status", "봇 상태 확인"),
        BotCommand("report_stats", "월간 보고서 통계"),
    ])
    print("✅ 봇 명령어 등록 완료")

    for _, plugin in loaded_plugins:
        if hasattr(plugin, "post_init"):
            try:
                result = plugin.post_init(app)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"플러그인 post_init 오류: {plugin.__name__} -> {e}")

    scheduler.add_job(send_daily_summary, 'cron', hour=20, minute=0, args=[app.bot], id="daily_summary")
    scheduler.add_job(send_weekly_report, 'cron', day_of_week='mon', hour=8, minute=0, args=[app.bot], id="weekly_report_analyzer")
    scheduler.add_job(send_monthly_stats, 'cron', day=1, hour=0, minute=0, args=[app.bot], id="monthly_stats")
    scheduler.add_job(run_backup, 'cron', hour=3, minute=0, args=[app.bot], id="daily_backup")
    asyncio.create_task(check_changes(app))


enabled_plugins = config.get("enabled_plugins") or []
loaded_plugins = load_plugins(enabled_plugins)

app = ApplicationBuilder().token(config.get("telegram_token")).post_init(post_init).build()

for plugin_name, plugin in loaded_plugins:
    if hasattr(plugin, "register"):
        try:
            plugin.register(app, config)
        except Exception as e:
            print(f"플러그인 등록 실패: {plugin_name} -> {e}")
    else:
        print(f"플러그인에 register 함수가 없습니다: {plugin_name}")

print("봇 시작!")
app.run_polling(allowed_updates=["message", "message_reaction", "callback_query", "my_chat_member"])
