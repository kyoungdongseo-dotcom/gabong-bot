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
