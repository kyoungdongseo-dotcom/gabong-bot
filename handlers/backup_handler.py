import asyncio
import os
import zipfile
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import ContextTypes

import config

KST = timezone(timedelta(hours=9))
ADMIN_ID = 97057565
BACKUP_DIR = "./data/backups"
BACKUP_FILES = [
    "./data/gabong.db",
    "./data/bot_data.db",
    "./data/reminders.json",
]


def _cleanup_old_backups(days: int = 7) -> int:
    if not os.path.exists(BACKUP_DIR):
        return 0
    cutoff = datetime.now().timestamp() - days * 86400
    deleted = 0
    for fname in os.listdir(BACKUP_DIR):
        if not fname.startswith("gabong_backup_"):
            continue
        fpath = os.path.join(BACKUP_DIR, fname)
        if os.path.getmtime(fpath) < cutoff:
            try:
                os.remove(fpath)
                deleted += 1
            except Exception:
                pass
    return deleted


def _do_backup() -> tuple:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    now = datetime.now(KST)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    zip_name = f"gabong_backup_{stamp}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)

    included = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in BACKUP_FILES:
            if os.path.exists(fpath):
                zf.write(fpath, os.path.basename(fpath))
                included.append(os.path.basename(fpath))

    if not included:
        os.remove(zip_path)
        return "", "⚠️ 백업할 파일이 없습니다."

    size_kb = os.path.getsize(zip_path) // 1024
    deleted = _cleanup_old_backups()

    msg = (
        f"✅ 백업 완료!\n"
        f"파일: {zip_name}\n"
        f"크기: {size_kb} KB\n"
        f"포함: {', '.join(included)}\n"
        f"로컬 보관: {BACKUP_DIR}\n"
        f"오래된 백업 삭제: {deleted}개"
    )
    return zip_path, msg


async def run_backup(bot) -> str:
    loop = asyncio.get_running_loop()
    try:
        zip_path, result = await loop.run_in_executor(None, _do_backup)
    except Exception as e:
        zip_path, result = "", f"❌ 백업 실패: {e}"

    if bot:
        try:
            if zip_path and os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    await bot.send_document(
                        chat_id=ADMIN_ID, document=f,
                        filename=os.path.basename(zip_path), caption=result
                    )
            else:
                await bot.send_message(chat_id=ADMIN_ID, text=result)
        except Exception as e:
            print(f"[백업] DM 전송 실패: {e}")

    return result


def cleanup_tmp_docx(max_age_hours: int = 24) -> int:
    """/tmp 의 award_*.docx, mou_*.docx, report_*.docx 중 N시간 이전 정리.
    정리 건수 반환 (실패 시 -1)."""
    try:
        cutoff = datetime.now().timestamp() - max_age_hours * 3600
        deleted = 0
        for fname in os.listdir("/tmp"):
            if not fname.endswith(".docx"):
                continue
            if not (fname.startswith("award_") or fname.startswith("mou_")
                    or fname.startswith("report_")):
                continue
            fpath = os.path.join("/tmp", fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    deleted += 1
            except Exception:
                pass
        print(f"✅ /tmp/*.docx cleanup: {deleted}개 정리 ({max_age_hours}h 이전)")
        return deleted
    except Exception as e:
        print(f"⚠️ /tmp/*.docx cleanup 실패: {e}")
        return -1


async def run_daily_cleanup(bot=None):
    """매일 03:30 — 24h 이전 recent_submissions 정리"""
    from database import cleanup_recent_submissions
    loop = asyncio.get_running_loop()
    deleted = await loop.run_in_executor(None, cleanup_recent_submissions, 86400)
    if bot and deleted < 0:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ daily cleanup 실패: recent_submissions"
            )
        except Exception:
            pass


async def run_weekly_cleanup(bot=None):
    """매주 일요일 04:00 — 90일 이전 report_log 정리 + /tmp docx 정리"""
    from database import cleanup_report_log
    loop = asyncio.get_running_loop()
    log_deleted = await loop.run_in_executor(None, cleanup_report_log, 90)
    docx_deleted = await loop.run_in_executor(None, cleanup_tmp_docx, 24)
    if bot:
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    f"🧹 주간 cleanup 완료\n"
                    f"  • report_log (90일): {log_deleted}건\n"
                    f"  • /tmp *.docx (24h): {docx_deleted}개"
                )
            )
        except Exception as e:
            print(f"[cleanup] 관리자 알림 실패: {e}")


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    admin_ids = config.get("admin_ids", [])
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    await update.message.reply_text("⏳ 백업 중입니다...")
    loop = asyncio.get_running_loop()
    try:
        zip_path, result = await loop.run_in_executor(None, _do_backup)
        if zip_path and os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                await update.message.reply_document(
                    document=f, filename=os.path.basename(zip_path), caption=result
                )
        else:
            await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ 백업 실패: {e}")
