import os
import subprocess
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

import config
from database import get_reminders
from utils import get_scheduler

BOT_START_TIME = datetime.now()


def _get_last_commit() -> str:
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%s'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "알 수 없음"
    except Exception:
        return "알 수 없음"


def _get_last_backup() -> str:
    backup_dir = "./data/backups"
    if not os.path.exists(backup_dir):
        return "없음"
    files = [
        f for f in os.listdir(backup_dir)
        if f.startswith("gabong_backup_") and f.endswith(".zip")
    ]
    if not files:
        return "없음"
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)))
    mtime = os.path.getmtime(os.path.join(backup_dir, latest))
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    admin_ids = config.get("admin_ids", [])
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    # 업타임
    delta = datetime.now() - BOT_START_TIME
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h}시간 {m}분 {s}초"

    # 리마인더
    try:
        reminder_count = len(get_reminders())
    except Exception:
        reminder_count = -1

    # 스케줄러 jobs
    jobs = get_scheduler().get_jobs()
    job_list = "\n".join(f"  • {j.id}" for j in jobs) if jobs else "  (없음)"

    # 그룹
    allowed = config.get("allowed_groups") or []
    exclude = config.get("exclude_groups") or []
    exclude_names = config.get("exclude_group_names") or {}

    exclude_lines = []
    for gid in exclude:
        name = exclude_names.get(str(gid), "")
        exclude_lines.append(f"  {gid}" + (f" ({name})" if name else ""))
    exclude_detail = "\n".join(exclude_lines) if exclude_lines else "  (없음)"

    # 환경
    api_status = "✅ 설정됨" if os.environ.get("ANTHROPIC_API_KEY") else "❌ 미설정"
    sheets_ok = os.path.exists("credentials.json") and os.path.exists("serviceAccountKey.json")
    sheets_status = "✅ 파일 존재" if sheets_ok else "⚠️ credentials 없음"
    last_backup = _get_last_backup()
    commit = _get_last_commit()

    text = (
        f"🤖 봇 상태\n"
        f"\n"
        f"📌 최신 커밋: {commit}\n"
        f"⏱ 업타임: {uptime_str}\n"
        f"🔢 PID: {os.getpid()}\n"
        f"\n"
        f"📝 리마인더: {reminder_count}개\n"
        f"✅ 허가 그룹: {len(allowed)}개\n"
        f"🚫 제외 그룹: {len(exclude)}개\n"
        f"{exclude_detail}\n"
        f"\n"
        f"🤖 Claude API: {api_status}\n"
        f"📊 Google Sheets: {sheets_status}\n"
        f"💾 마지막 백업: {last_backup}\n"
        f"\n"
        f"📅 스케줄 job ({len(jobs)}개):\n"
        f"{job_list}"
    )
    await update.message.reply_text(text)
