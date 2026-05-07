from telegram import Update
from telegram.ext import ContextTypes
import config

async def handle_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return

    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    was_added = (
        old_status in ("left", "kicked") and
        new_status in ("member", "administrator")
    )
    if not was_added:
        return

    admin_ids = config.get('admin_ids', [])
    inviter_id = result.from_user.id
    chat_id = result.chat.id
    chat_title = result.chat.title or str(chat_id)
    main_admin_id = admin_ids[0] if admin_ids else None

    if inviter_id not in admin_ids:
        # 비관리자 초대 → 탈퇴
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ 이 봇은 관리자만 초대할 수 있습니다."
            )
        except:
            pass
        await context.bot.leave_chat(chat_id)

        # gamdongwon에게 알림
        if main_admin_id:
            await context.bot.send_message(
                chat_id=main_admin_id,
                text=(
                    f"⚠️ 무단 초대 차단\n"
                    f"그룹: {chat_title}\n"
                    f"초대자 ID: {inviter_id}\n"
                    f"→ 자동 탈퇴 완료"
                )
            )
    else:
        # 관리자 초대 → 알림만
        if main_admin_id:
            await context.bot.send_message(
                chat_id=main_admin_id,
                text=(
                    f"✅ 봇 초대 승인\n"
                    f"그룹: {chat_title}\n"
                    f"초대자 ID: {inviter_id}"
                )
            )
