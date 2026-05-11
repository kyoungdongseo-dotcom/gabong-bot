from telegram import Update
from telegram.ext import ContextTypes
import config

async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message_reaction:
        return

    AUTHORIZED_USERS = config.get('reaction_authorized_users', [])
    reactor_id = update.message_reaction.user.id

    if reactor_id not in AUTHORIZED_USERS:
        return

    REACTION_EXCLUDE_GROUPS = config.get('reaction_exclude_groups', [-1002363981206])
    source_group_id = update.message_reaction.chat.id
    if source_group_id in REACTION_EXCLUDE_GROUPS:
        return

    # Bot API는 메시지 조회를 지원하지 않으므로 본인 글 체크 생략

    REACTION_TOPICS = config.get('reaction_topics')
    REPLY_REACTIONS = config.get('reply_reactions')
    for r in update.message_reaction.new_reaction:
        emoji = r.emoji
        if emoji in REACTION_TOPICS:
            topic_id = REACTION_TOPICS[emoji]
            try:
                await context.bot.forward_message(
                    chat_id=config.get('group_id'),
                    message_thread_id=topic_id,
                    from_chat_id=source_group_id,
                    message_id=update.message_reaction.message_id
                )
                print(f"✅ reaction 처리: {emoji} user={reactor_id} group={source_group_id} -> 토픽 {topic_id}")
            except Exception as e:
                print(f"❌ reaction 전달 오류: {emoji} user={reactor_id} group={source_group_id}: {e}")
        if emoji in REPLY_REACTIONS:
            try:
                await context.bot.send_message(
                    chat_id=source_group_id,
                    text=REPLY_REACTIONS[emoji],
                    reply_to_message_id=update.message_reaction.message_id
                )
                print(f"✅ reaction 답장: {emoji} user={reactor_id} group={source_group_id}")
            except Exception as e:
                print(f"❌ reaction 답장 오류: {emoji} user={reactor_id} group={source_group_id}: {e}")
