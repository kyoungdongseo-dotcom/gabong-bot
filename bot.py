import json
import os
import uuid
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# 로컬 개발 시 .env 파일에서 환경변수 로드 (선택적 의존성)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv 미설치 시 무시 (Railway 같은 배포 환경에선 env var 직접 설정)
    pass


# ============================================================
# 환경변수 기반 설정
# ============================================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN 환경변수가 설정되지 않았습니다.\n"
        "로컬: 프로젝트 루트에 .env 파일을 만들고 TELEGRAM_TOKEN=... 추가\n"
        "Railway: Variables 탭에서 TELEGRAM_TOKEN 설정"
    )

# 팀 그룹/토픽/관리자 — 기본값은 현재 운영값, 필요 시 env var 로 덮어쓰기
GROUP_ID = int(os.getenv("GROUP_ID", "-1002363981206"))
TOPIC_ID = int(os.getenv("TOPIC_ID", "2"))
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "97057565").split(",") if x.strip()
]

# 리마인더 데이터 저장 경로
# 로컬: 기본값 reminders.json (현재 디렉토리)
# Railway: Volume 마운트 경로 (예: /data/reminders.json) 를 env var 로 지정
REMINDERS_FILE = os.getenv("REMINDERS_FILE", "reminders.json")

KST = ZoneInfo("Asia/Seoul")

# 한글 요일 → 숫자 (월요일=0)
DAY_MAP = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
DAY_REVERSE = {v: k for k, v in DAY_MAP.items()}


# ============================================================
# 저장/불러오기
# ============================================================
def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"리마인드 파일 로드 실패: {e}")
    return []


def save_reminders(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


# ============================================================
# 리마인드 전송 (JobQueue 콜백)
# ============================================================
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    msg = f"⏰ 리마인드\n\n{data['message']}"
    try:
        if data["destination"] == "group":
            await context.bot.send_message(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_ID,
                text=msg,
            )
        else:  # dm
            await context.bot.send_message(
                chat_id=data["user_id"],
                text=msg,
            )
    except Exception as e:
        print(f"리마인드 전송 실패 (id={data.get('id')}): {e}")


def schedule_reminder(job_queue: JobQueue, reminder: dict):
    hour, minute = map(int, reminder["time"].split(":"))
    t = time(hour=hour, minute=minute, tzinfo=KST)

    if reminder["type"] == "daily":
        job_queue.run_daily(
            send_reminder, time=t, data=reminder, name=reminder["id"]
        )
    elif reminder["type"] == "weekly":
        job_queue.run_daily(
            send_reminder,
            time=t,
            days=tuple(reminder["days"]),
            data=reminder,
            name=reminder["id"],
        )
    elif reminder["type"] == "monthly":
        job_queue.run_monthly(
            send_reminder,
            when=t,
            day=reminder["day"],
            data=reminder,
            name=reminder["id"],
        )


# ============================================================
# 유틸: 입력 검증
# ============================================================
def parse_time(time_str: str):
    try:
        h, m = map(int, time_str.split(":"))
        if 0 <= h < 24 and 0 <= m < 60:
            return h, m
    except Exception:
        pass
    return None


def parse_destination(arg: str):
    if arg == "그룹":
        return "group"
    if arg == "개인":
        return "dm"
    return None


# ============================================================
# 기본 명령어
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "안녕하세요! GAbong Bot입니다 🤖\n\n"
        "📋 사용 가능한 명령어\n\n"
        "🔔 공지\n"
        "/notice [내용] - 공지 전송 (관리자)\n\n"
        "⏰ 리마인드\n"
        "/remind_daily HH:MM 그룹|개인 메시지\n"
        "  예: /remind_daily 09:00 그룹 출근 확인\n\n"
        "/remind_weekly 월,수,금 HH:MM 그룹|개인 메시지\n"
        "  예: /remind_weekly 월,수 10:00 그룹 주간 회의\n\n"
        "/remind_monthly 일자 HH:MM 그룹|개인 메시지\n"
        "  예: /remind_monthly 25 14:00 그룹 보고서 제출\n\n"
        "/my_reminders - 내 리마인드 목록\n"
        "/delete_reminder ID - 리마인드 삭제\n\n"
        "💡 '개인'으로 받으려면 먼저 저에게 DM으로 /start 를 보내주세요!"
    )
    await update.message.reply_text(help_text)


async def notice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if ADMIN_IDS and user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ 공지 권한이 없습니다.")
        return

    # 줄바꿈 보존: 원본 메시지에서 /notice 부분만 떼어내기
    _, _, text = update.message.text.partition(" ")
    text = text.strip()

    if not text:
        await update.message.reply_text("사용법: /notice [내용]")
        return

    msg = f"📢 공지사항\n\n{text}"
    await context.bot.send_message(
        chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg
    )
    await update.message.reply_text("✅ 공지가 전송되었습니다!")


# ============================================================
# 리마인드 등록 명령어
# ============================================================
async def remind_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 원본 메시지에서 직접 파싱 (줄바꿈 보존)
    # parts = [명령어, 시간, 대상, 메시지(줄바꿈 포함)]
    parts = update.message.text.split(None, 3)
    if len(parts) < 4:
        await update.message.reply_text(
            "사용법: /remind_daily HH:MM 그룹|개인 메시지\n"
            "예: /remind_daily 09:00 그룹 출근 확인해주세요"
        )
        return

    _, time_str, dest_str, message = parts

    if parse_time(time_str) is None:
        await update.message.reply_text("⚠️ 시간 형식이 잘못됐어요. HH:MM (예: 09:00)")
        return

    destination = parse_destination(dest_str)
    if destination is None:
        await update.message.reply_text("⚠️ '그룹' 또는 '개인'으로 지정해주세요.")
        return

    reminder = {
        "id": str(uuid.uuid4())[:6],
        "type": "daily",
        "time": time_str,
        "message": message,
        "destination": destination,
        "user_id": update.effective_user.id,
        "user_name": update.effective_user.full_name,
    }

    reminders = load_reminders()
    reminders.append(reminder)
    save_reminders(reminders)
    schedule_reminder(context.application.job_queue, reminder)

    dest_label = "그룹" if destination == "group" else "개인 DM"
    await update.message.reply_text(
        f"✅ 리마인드 등록 완료!\n\n"
        f"ID: {reminder['id']}\n"
        f"일정: 매일 {time_str}\n"
        f"전송: {dest_label}\n"
        f"메시지:\n{message}"
    )


async def remind_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 원본 메시지에서 직접 파싱 (줄바꿈 보존)
    # parts = [명령어, 요일, 시간, 대상, 메시지(줄바꿈 포함)]
    parts = update.message.text.split(None, 4)
    if len(parts) < 5:
        await update.message.reply_text(
            "사용법: /remind_weekly 월,수,금 HH:MM 그룹|개인 메시지\n"
            "예: /remind_weekly 월,수 10:00 그룹 주간 회의입니다"
        )
        return

    _, days_str, time_str, dest_str, message = parts

    try:
        days = [DAY_MAP[d.strip()] for d in days_str.split(",")]
    except KeyError:
        await update.message.reply_text(
            "⚠️ 요일은 월,화,수,목,금,토,일 중에서 콤마(,)로 구분해주세요."
        )
        return

    if parse_time(time_str) is None:
        await update.message.reply_text("⚠️ 시간 형식이 잘못됐어요. HH:MM (예: 10:00)")
        return

    destination = parse_destination(dest_str)
    if destination is None:
        await update.message.reply_text("⚠️ '그룹' 또는 '개인'으로 지정해주세요.")
        return

    reminder = {
        "id": str(uuid.uuid4())[:6],
        "type": "weekly",
        "time": time_str,
        "days": days,
        "days_display": ",".join(DAY_REVERSE[d] for d in sorted(days)),
        "message": message,
        "destination": destination,
        "user_id": update.effective_user.id,
        "user_name": update.effective_user.full_name,
    }

    reminders = load_reminders()
    reminders.append(reminder)
    save_reminders(reminders)
    schedule_reminder(context.application.job_queue, reminder)

    dest_label = "그룹" if destination == "group" else "개인 DM"
    await update.message.reply_text(
        f"✅ 리마인드 등록 완료!\n\n"
        f"ID: {reminder['id']}\n"
        f"일정: 매주 {reminder['days_display']} {time_str}\n"
        f"전송: {dest_label}\n"
        f"메시지:\n{message}"
    )


async def remind_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 원본 메시지에서 직접 파싱 (줄바꿈 보존)
    # parts = [명령어, 일자, 시간, 대상, 메시지(줄바꿈 포함)]
    parts = update.message.text.split(None, 4)
    if len(parts) < 5:
        await update.message.reply_text(
            "사용법: /remind_monthly 일자 HH:MM 그룹|개인 메시지\n"
            "예: /remind_monthly 25 14:00 그룹 보고서 제출일입니다"
        )
        return

    _, day_str, time_str, dest_str, message = parts

    try:
        day = int(day_str)
        if not (1 <= day <= 31):
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ 일자는 1~31 사이 숫자로 입력해주세요.")
        return

    if parse_time(time_str) is None:
        await update.message.reply_text("⚠️ 시간 형식이 잘못됐어요. HH:MM (예: 14:00)")
        return

    destination = parse_destination(dest_str)
    if destination is None:
        await update.message.reply_text("⚠️ '그룹' 또는 '개인'으로 지정해주세요.")
        return

    reminder = {
        "id": str(uuid.uuid4())[:6],
        "type": "monthly",
        "time": time_str,
        "day": day,
        "message": message,
        "destination": destination,
        "user_id": update.effective_user.id,
        "user_name": update.effective_user.full_name,
    }

    reminders = load_reminders()
    reminders.append(reminder)
    save_reminders(reminders)
    schedule_reminder(context.application.job_queue, reminder)

    dest_label = "그룹" if destination == "group" else "개인 DM"
    await update.message.reply_text(
        f"✅ 리마인드 등록 완료!\n\n"
        f"ID: {reminder['id']}\n"
        f"일정: 매월 {day}일 {time_str}\n"
        f"전송: {dest_label}\n"
        f"메시지:\n{message}"
    )


# ============================================================
# 리마인드 조회/삭제
# ============================================================
async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminders = load_reminders()
    mine = [r for r in reminders if r["user_id"] == user_id]

    if not mine:
        await update.message.reply_text("📋 등록된 리마인드가 없습니다.")
        return

    lines = ["📋 내 리마인드 목록\n"]
    for r in mine:
        dest = "그룹" if r["destination"] == "group" else "개인"
        if r["type"] == "daily":
            sched = f"매일 {r['time']}"
        elif r["type"] == "weekly":
            sched = f"매주 {r['days_display']} {r['time']}"
        else:
            sched = f"매월 {r['day']}일 {r['time']}"
        lines.append(f"• [{r['id']}] {sched} ({dest})\n   └ {r['message']}")

    await update.message.reply_text("\n".join(lines))


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /delete_reminder ID")
        return

    target_id = context.args[0]
    user_id = update.effective_user.id
    reminders = load_reminders()

    found = None
    for r in reminders:
        if r["id"] == target_id and r["user_id"] == user_id:
            found = r
            break

    if found is None:
        await update.message.reply_text(
            "⚠️ 해당 ID의 리마인드를 찾을 수 없어요. (본인이 등록한 것만 삭제 가능)"
        )
        return

    reminders.remove(found)
    save_reminders(reminders)

    for job in context.application.job_queue.get_jobs_by_name(target_id):
        job.schedule_removal()

    await update.message.reply_text(f"✅ 리마인드 [{target_id}] 삭제 완료")


# ============================================================
# 봇 시작 시 저장된 리마인드 복원
# ============================================================
async def post_init(application):
    reminders = load_reminders()
    for r in reminders:
        try:
            schedule_reminder(application.job_queue, r)
        except Exception as e:
            print(f"리마인드 복원 실패 (id={r.get('id')}): {e}")
    print(f"저장된 리마인드 {len(reminders)}개 복원 완료")


# ============================================================
# 앱 구동
# ============================================================
app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("notice", notice))
app.add_handler(CommandHandler("remind_daily", remind_daily))
app.add_handler(CommandHandler("remind_weekly", remind_weekly))
app.add_handler(CommandHandler("remind_monthly", remind_monthly))
app.add_handler(CommandHandler("my_reminders", my_reminders))
app.add_handler(CommandHandler("delete_reminder", delete_reminder))

print("봇 시작!")
app.run_polling()