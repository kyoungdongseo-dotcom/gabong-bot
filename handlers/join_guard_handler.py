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
        except Exception:
            pass
        await context.bot.leave_chat(chat_id)
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
        return

    # 관리자 초대 → 화이트리스트 확인
    allowed_groups = config.get('allowed_groups') or []
    if allowed_groups and chat_id not in allowed_groups:
        # 미등록 그룹 → 탈퇴
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ 등록되지 않은 그룹입니다. 관리자에게 문의하세요."
            )
        except Exception:
            pass
        await context.bot.leave_chat(chat_id)
        if main_admin_id:
            await context.bot.send_message(
                chat_id=main_admin_id,
                text=(
                    f"⚠️ 화이트리스트 미등록 그룹 탈퇴\n"
                    f"그룹: {chat_title} ({chat_id})\n"
                    f"초대자 ID: {inviter_id}\n"
                    f"→ 자동 탈퇴 완료\n\n"
                    f"등록하려면: /add_group {chat_id}"
                )
            )
        return

    # 승인
    if main_admin_id:
        await context.bot.send_message(
            chat_id=main_admin_id,
            text=(
                f"✅ 봇 초대 승인\n"
                f"그룹: {chat_title} ({chat_id})\n"
                f"초대자 ID: {inviter_id}"
            )
        )


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/add_group [group_id] - 그룹을 화이트리스트에 추가"""
    if not update.message:
        return
    admin_ids = config.get('admin_ids', [])
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    if context.args:
        try:
            group_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ 유효한 그룹 ID를 입력하세요.\n예: /add_group -1001234567890")
            return
    else:
        group_id = update.effective_chat.id
        if group_id > 0:
            await update.message.reply_text("❌ 그룹에서 실행하거나 /add_group [group_id]를 사용하세요.")
            return

    allowed = config.get('allowed_groups') or []
    if group_id in allowed:
        await update.message.reply_text(f"ℹ️ 이미 등록된 그룹입니다: {group_id}")
        return

    allowed.append(group_id)
    config.set_value('allowed_groups', allowed)
    await update.message.reply_text(f"✅ 그룹 {group_id} 화이트리스트 추가 완료")
