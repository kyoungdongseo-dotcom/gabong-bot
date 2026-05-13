import config


def is_admin(user_id: int) -> bool:
    """관리자 여부 확인 (admin_ids 6명)"""
    return user_id in config.get('admin_ids', [])


def is_main_admin(user_id: int) -> bool:
    """메인 관리자 여부 확인 (my_user_id 1명, 기본 97057565)"""
    return user_id == config.get('my_user_id', 97057565)


async def check_admin(update, context) -> bool:
    """관리자가 아니면 조용히 무시하고 False (silent).
    핸들러 최상단:
        if not await check_admin(update, context): return
    """
    if not update.effective_user:
        return False
    return is_admin(update.effective_user.id)


async def require_admin(update, context,
                        message: str = "❌ 관리자만 사용 가능합니다.") -> bool:
    """관리자가 아니면 거부 메시지 발송 후 False.
    핸들러 최상단:
        if not await require_admin(update, context): return
    """
    if not update.effective_user:
        return False
    if not is_admin(update.effective_user.id):
        if update.message:
            try:
                await update.message.reply_text(message)
            except Exception:
                pass
        return False
    return True


async def require_main_admin(update, context,
                             message: str = "❌ 메인 관리자만 사용 가능합니다.") -> bool:
    """메인 관리자가 아니면 거부 메시지 발송 후 False.
    핸들러 최상단:
        if not await require_main_admin(update, context): return
    """
    if not update.effective_user:
        return False
    if not is_main_admin(update.effective_user.id):
        if update.message:
            try:
                await update.message.reply_text(message)
            except Exception:
                pass
        return False
    return True
