import config

def is_admin(user_id: int) -> bool:
    """관리자 여부 확인"""
    return user_id in config.get('admin_ids', [])

async def check_admin(update, context) -> bool:
    """
    관리자가 아니면 조용히 무시하고 False 반환.
    핸들러 최상단에서 호출:
        if not await check_admin(update, context): return
    """
    if not is_admin(update.effective_user.id):
        return False
    return True
