import asyncio
import os
import zipfile
import tempfile
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

KST = timezone(timedelta(hours=9))
ADMIN_ID = 97057565
BACKUP_FILES = [
    "./data/gabong.db",
    "./data/bot_data.db",
    "./data/reminders.json",
]


def _get_drive_service():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service) -> str:
    folder_id = config.get("backup_folder_id")
    if folder_id:
        return folder_id

    results = service.files().list(
        q="name='gabong-backup' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id)"
    ).execute()
    files = results.get("files", [])

    if files:
        fid = files[0]["id"]
    else:
        meta = {"name": "gabong-backup", "mimeType": "application/vnd.google-apps.folder"}
        folder = service.files().create(body=meta, fields="id").execute()
        fid = folder["id"]

    config.set_value("backup_folder_id", fid)
    return fid


def _delete_old_backups(service, folder_id: str, days: int = 7) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = service.files().list(
        q=f"'{folder_id}' in parents and name contains 'gabong_backup_' and trashed=false and createdTime < '{cutoff}'",
        fields="files(id)"
    ).execute()
    deleted = 0
    for f in results.get("files", []):
        try:
            service.files().delete(fileId=f["id"]).execute()
            deleted += 1
        except Exception:
            pass
    return deleted


def _do_backup() -> str:
    now = datetime.now(KST)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    zip_name = f"gabong_backup_{stamp}.zip"

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, zip_name)

        included = []
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in BACKUP_FILES:
                if os.path.exists(fpath):
                    zf.write(fpath, os.path.basename(fpath))
                    included.append(os.path.basename(fpath))

        if not included:
            return "⚠️ 백업할 파일이 없습니다."

        service = _get_drive_service()
        folder_id = _get_or_create_folder(service)

        file_meta = {"name": zip_name, "parents": [folder_id]}
        media = MediaFileUpload(zip_path, mimetype="application/zip")
        uploaded = service.files().create(
            body=file_meta, media_body=media, fields="id,size"
        ).execute()

        size_kb = int(uploaded.get("size", 0)) // 1024
        deleted = _delete_old_backups(service, folder_id)

        return (
            f"✅ 백업 완료!\n"
            f"파일: {zip_name}\n"
            f"크기: {size_kb} KB\n"
            f"포함: {', '.join(included)}\n"
            f"오래된 백업 삭제: {deleted}개"
        )


async def run_backup(bot) -> str:
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _do_backup)
    except Exception as e:
        result = f"❌ 백업 실패: {e}"

    if bot:
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=result)
        except Exception as e:
            print(f"[백업] 알림 DM 실패: {e}")

    return result


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    admin_ids = config.get("admin_ids", [])
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    await update.message.reply_text("⏳ 백업 중입니다...")
    result = await run_backup(None)
    await update.message.reply_text(result)
