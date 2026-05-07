from telegram import Update
from telegram.ext import ContextTypes
import config

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"반응 이벤트 받음!")
    if not update.message_reaction:
        return

    AUTHORIZED_USERS = config.get('reaction_authorized_users', [])
    if update.message_reaction.user.id not in AUTHORIZED_USERS:
        print(f"권한 없음: {update.message_reaction.user.id}")
        return

    REACTION_EXCLUDE_GROUPS = config.get('reaction_exclude_groups', [-1002363981206])
    source_group_id = update.message_reaction.chat.id
    if source_group_id in REACTION_EXCLUDE_GROUPS:
        print(f"제외 그룹에서의 반응 무시: {source_group_id}")
        return

    REACTION_TOPICS = config.get('reaction_topics')
    REPLY_REACTIONS = config.get('reply_reactions')
    for r in update.message_reaction.new_reaction:
        emoji = r.emoji
        print(f"이모티콘: {emoji}")
        if emoji in REACTION_TOPICS:
            topic_id = REACTION_TOPICS[emoji]
            try:
                await context.bot.forward_message(
                    chat_id=config.get('group_id'),
                    message_thread_id=topic_id,
                    from_chat_id=update.message_reaction.chat.id,
                    message_id=update.message_reaction.message_id
                )
                print(f"전달 성공: {emoji} -> 토픽 {topic_id}")
            except Exception as e:
                print(f"전달 오류: {e}")
        if emoji in REPLY_REACTIONS:
            try:
                await context.bot.send_message(
                    chat_id=update.message_reaction.chat.id,
                    text=REPLY_REACTIONS[emoji],
                    reply_to_message_id=update.message_reaction.message_id
                )
                print(f"답장 성공: {emoji}")
            except Exception as e:
                print(f"답장 오류: {e}")
