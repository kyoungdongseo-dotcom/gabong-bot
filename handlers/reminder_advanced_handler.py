import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from utils import load_reminders, save_reminders


async def remind_if_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """키워드 감지 시 자동 알림"""
    if not update.message or not update.message.text:
        return

    try:
        user_id = update.effective_user.id
        text = update.message.text.lower()

        reminders = load_reminders()
        # 사용자의 활성 키워드 리마인더만 조회
        user_keyword_reminders = [
            r for r in reminders
            if r.get("user_id") == user_id
            and r.get("type") == "keyword"
            and r.get("active", True)
        ]

        if not user_keyword_reminders:
            return

        # 메시지에 매칭되는 키워드 찾기
        triggered = False
        for reminder in user_keyword_reminders:
            keyword = reminder.get("keyword", "").lower()
            if keyword in text and not triggered:
                # 알림 전송
                message = reminder.get("message", f"'{keyword}' 키워드 감지됨!")
                await update.message.reply_text(
                    f"🔍 **키워드 감지!**\n키워드: {keyword}\n알림: {message}",
                    reply_to_message_id=update.message.message_id
                )

                # 트리거 통계 업데이트
                reminder["trigger_count"] = reminder.get("trigger_count", 0) + 1
                reminder["last_triggered"] = datetime.now().isoformat()

                # 저장
                for i, r in enumerate(reminders):
                    if r.get("id") == reminder.get("id"):
                        reminders[i] = reminder
                        break
                save_reminders(reminders)
                triggered = True  # 메시지당 한 번만 트리거

    except Exception as e:
        print(f"키워드 리마인더 처리 오류: {e}")


async def handle_remind_if_keyword_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /remind_if_keyword [키워드] [알림메시지]
    예: /remind_if_keyword 회의 회의 시간입니다!
    """
    if not update.message or not update.message.text:
        return

    try:
        text = update.message.text
        parts = text.split(None, 3)  # 최대 3개로 분할

        if len(parts) < 2:
            await update.message.reply_text(
                "❌ 형식: `/remind_if_keyword [키워드] [선택: 알림메시지]`\n"
                "예: `/remind_if_keyword 회의 회의 시간입니다!`"
            )
            return

        keyword = parts[1].strip()
        message = parts[3] if len(parts) > 3 else f"'{keyword}' 키워드가 감지되었습니다!"

        # 중복 체크
        reminders = load_reminders()
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # 같은 사용자의 같은 키워드가 있는지 확인
        existing = [
            r for r in reminders
            if r.get("user_id") == user_id
            and r.get("type") == "keyword"
            and r.get("keyword", "").lower() == keyword.lower()
        ]

        if existing:
            await update.message.reply_text(
                f"⚠️ 이미 등록된 키워드입니다: '{keyword}'"
            )
            return

        # 새 리마인더 생성
        reminder_id = f"{user_id}_{keyword}_{datetime.now().timestamp()}"
        new_reminder = {
            "id": reminder_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "type": "keyword",
            "keyword": keyword,
            "message": message,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "trigger_count": 0,
            "last_triggered": None
        }

        reminders.append(new_reminder)
        save_reminders(reminders)

        await update.message.reply_text(
            f"✅ 키워드 리마인더 등록 완료!\n"
            f"키워드: `{keyword}`\n"
            f"알림: {message}"
        )

    except Exception as e:
        print(f"리마인더 등록 오류: {e}")
        await update.message.reply_text(f"❌ 오류 발생: {str(e)}")


async def reminder_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    이달 리마인더 생성 통계
    """
    if not update.message:
        return

    try:
        user_id = update.effective_user.id
        reminders = load_reminders()
        user_reminders = [r for r in reminders if r.get("user_id") == user_id]

        if not user_reminders:
            await update.message.reply_text("📊 아직 등록된 리마인더가 없습니다.")
            return

        # 이달 통계
        today = datetime.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        reminders_this_month = [
            r for r in user_reminders
            if datetime.fromisoformat(r.get("created_at", "")) >= month_start
        ]

        # 타입별 통계
        total = len(user_reminders)
        keyword_count = len([r for r in user_reminders if r.get("type") == "keyword"])
        active_count = len([r for r in user_reminders if r.get("active", True)])
        this_month_count = len(reminders_this_month)

        stats_text = f"""📊 **리마인더 통계**

**전체 리마인더:** {total}개
**키워드 리마인더:** {keyword_count}개
**활성 리마인더:** {active_count}개
**이달 생성:** {this_month_count}개

📌 **명령어:**
• `/remind_if_keyword` - 키워드 리마인더 등록
• `/reminder_stats` - 이 통계 보기
• `/reminder_analysis` - 상위 5개 분석"""

        await update.message.reply_text(stats_text)

    except Exception as e:
        print(f"통계 조회 오류: {e}")
        await update.message.reply_text(f"❌ 오류 발생: {str(e)}")


async def reminder_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    가장 자주 사용하는 리마인더 top 5
    """
    if not update.message:
        return

    try:
        user_id = update.effective_user.id
        reminders = load_reminders()
        user_reminders = [r for r in reminders if r.get("user_id") == user_id]

        if not user_reminders:
            await update.message.reply_text("📈 분석할 리마인더가 없습니다.")
            return

        # 트리거 횟수로 정렬
        sorted_reminders = sorted(
            user_reminders,
            key=lambda r: r.get("trigger_count", 0),
            reverse=True
        )[:5]

        if not any(r.get("trigger_count", 0) > 0 for r in sorted_reminders):
            await update.message.reply_text(
                "📈 아직 트리거된 리마인더가 없습니다.\n"
                "키워드 리마인더를 등록하고 사용해보세요!"
            )
            return

        # 분석 리포트 생성
        analysis_text = "📈 **자주 사용하는 리마인더 TOP 5**\n\n"

        for idx, reminder in enumerate(sorted_reminders, 1):
            if reminder.get("trigger_count", 0) > 0:
                keyword = reminder.get("keyword", "N/A")
                count = reminder.get("trigger_count", 0)
                last_triggered = reminder.get("last_triggered", "N/A")

                if last_triggered != "N/A":
                    try:
                        last_time = datetime.fromisoformat(last_triggered)
                        time_diff = datetime.now() - last_time
                        if time_diff.days == 0:
                            time_str = f"{time_diff.seconds // 3600}시간 전"
                        else:
                            time_str = f"{time_diff.days}일 전"
                    except:
                        time_str = "N/A"
                else:
                    time_str = "N/A"

                analysis_text += f"{idx}. `{keyword}` - {count}회 트리거\n   마지막: {time_str}\n"

        # 추천 사항 추가
        analysis_text += "\n💡 **추천:**\n"

        top_count = sorted_reminders[0].get("trigger_count", 0) if sorted_reminders else 0
        if top_count > 0:
            analysis_text += f"• 가장 자주 사용하는 키워드로 자동화 설정을 고려해보세요\n"

        keyword_triggers = sum(1 for r in sorted_reminders if r.get("trigger_count", 0) > 0)
        if keyword_triggers < 3:
            analysis_text += f"• 더 많은 키워드 리마인더를 추가해보세요\n"

        await update.message.reply_text(analysis_text)

    except Exception as e:
        print(f"분석 조회 오류: {e}")
        await update.message.reply_text(f"❌ 오류 발생: {str(e)}")
