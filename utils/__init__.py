import json
import os
import sqlite3
import asyncio
import threading
import anthropic
import gspread
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config


DB_LOCK = threading.Lock()
claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
SYSTEM_PROMPT = config.get('system_prompt')
SCOPES = config.get('google_scopes')
SPREADSHEET_ID = config.get('spreadsheet_id')
CACHE_FILE = config.get('cache_file')
REMINDERS_FILE = config.get('reminders_file')
DATABASE_FILE = config.get('database_file') or './data/bot_data.db'

# sheet 변경 감지 디바운싱 (행별 30분 — 도배 방지)
import time as _time_mod
LAST_SHEET_NOTIFY = {}              # {row_key: timestamp}
SHEET_NOTIFY_INTERVAL = 1800        # 30분(초)


def ensure_data_dir():
    db_dir = os.path.dirname(DATABASE_FILE)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def get_db_connection():
    acquired = DB_LOCK.acquire(timeout=10)
    if not acquired:
        raise RuntimeError("Database 접근 타임아웃")
    try:
        ensure_data_dir()
        conn = sqlite3.connect(DATABASE_FILE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    finally:
        DB_LOCK.release()


def init_database():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                role TEXT,
                text TEXT,
                thread_id INTEGER,
                timestamp TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_modes (
                chat_id INTEGER PRIMARY KEY,
                mode TEXT,
                updated_at TEXT
            )
            """
        )
        conn.commit()
    # gabong.db 의 신규 테이블도 함께 초기화 (보고서 PENDING/recent_submissions/report_log)
    try:
        from database import init_db as _init_gabong_db
        _init_gabong_db()
    except Exception as e:
        print(f"⚠️ gabong.db 초기화 실패: {e}")


def log_message(chat_id, user_id, user_name, role, text, thread_id=None, timestamp=None):
    timestamp = timestamp or datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, user_id, user_name, role, text, thread_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, user_name, role, text, thread_id, timestamp)
        )
        conn.commit()


def get_chat_history(chat_id, limit=20):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT role, text FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit)
        ).fetchall()
    return [{"role": row["role"], "content": row["text"]} for row in reversed(rows)]


def clear_chat_history(chat_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()


def fetch_weekly_messages(chat_id, since):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT user_name, role, text, timestamp FROM messages WHERE chat_id = ? AND timestamp >= ? ORDER BY id ASC",
            (chat_id, since.isoformat())
        ).fetchall()
    return [dict(row) for row in rows]


def set_chat_mode(chat_id, mode):
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO chat_modes (chat_id, mode, updated_at) VALUES (?, ?, ?)",
            (chat_id, mode, now)
        )
        conn.commit()


def get_chat_mode(chat_id):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT mode FROM chat_modes WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
    return row["mode"] if row else None


def get_role_prompt(mode):
    modes = config.get('role_prompt_modes') or {}
    return modes.get(mode)


def ask_claude(question, chat_id=None, user_id=None, user_name=None, thread_id=None, mode=None):
    try:
        system_prompt = SYSTEM_PROMPT
        role_prompt = get_role_prompt(mode) if mode else None
        if role_prompt:
            system_prompt = f"{SYSTEM_PROMPT}\n\n{role_prompt}"

        messages = []
        if chat_id:
            history = get_chat_history(chat_id, limit=10)
            messages.extend(history)

        messages.append({"role": "user", "content": question})
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system=system_prompt,
            messages=messages
        )
        answer = response.content[0].text

        if chat_id:
            log_message(chat_id, user_id or 0, user_name or "사용자", "user", question, thread_id)
            log_message(chat_id, None, "AI", "assistant", answer, thread_id)
            if chat_id not in CHAT_HISTORY:
                CHAT_HISTORY[chat_id] = []
            CHAT_HISTORY[chat_id].append({"role": "user", "content": question})
            CHAT_HISTORY[chat_id].append({"role": "assistant", "content": answer})
            if len(CHAT_HISTORY[chat_id]) > 50:
                CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-50:]

        return answer
    except Exception as e:
        print(f"Claude API 오류: {e}")
        return "죄송합니다. AI 답변 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

def get_sheet_data():
    """Google Sheets 데이터 조회"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1.get_all_values()

def get_sheet_service():
    """Google Sheets 서비스 객체 반환"""
    creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def load_cache():
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data):
    os.makedirs("./data", exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def load_reminders():
    os.makedirs("./data", exist_ok=True)
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)
                return [r for r in data if isinstance(r, dict) and "chat_id" in r]
        except:
            return []
    return []

def save_reminders(reminders):
    os.makedirs("./data", exist_ok=True)
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, ensure_ascii=False)

# 리마인더 발송 실패 카운터 (메모리 — 봇 재시작 시 리셋)
REMINDER_FAIL_COUNT = {}
REMINDER_MAX_FAIL = 3


async def _deactivate_reminder(bot, reminder_id, chat_id, reason, message):
    """리마인더 자동 비활성화 + 관리자 DM 알림.
    DB UPDATE → 스케줄러 remove → admin 알림 순서.
    각 단계 실패해도 다음 단계 진행 (best-effort)."""
    if not reminder_id:
        return
    try:
        from database import get_conn
        conn = get_conn()
        conn.execute("UPDATE reminders SET is_active = 0 WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()
        print(f"🔴 리마인더 자동 비활성화: id={reminder_id} 사유={reason}")
    except Exception as e:
        print(f"⚠️ 리마인더 DB 비활성화 실패: id={reminder_id} err={e}")

    try:
        get_scheduler().remove_job(str(reminder_id))
    except Exception:
        pass

    try:
        admin_id = config.get('my_user_id', 97057565)
        await bot.send_message(
            chat_id=admin_id,
            text=(
                f"⚠️ 리마인더 자동 비활성화\n"
                f"ID: {reminder_id}\n"
                f"그룹: {chat_id}\n"
                f"사유: {reason}\n"
                f"메시지: {(message or '')[:50]}"
            )
        )
    except Exception as e:
        print(f"⚠️ 리마인더 비활성화 admin 알림 실패: {e}")


async def send_reminder(bot, chat_id, text, topic_id=None, reminder_id=None):
    """리마인더 발송. 등록한 chat_id/topic_id 로 전송.
    chat_id=None 또는 0 이면 config 기본 그룹/토픽으로 폴백 (구버전 호환).
    reminder_id 전달 시 발송 실패 패턴별 자동 비활성화 (2026-05-13 추가):
      - Forbidden (봇 추방): 즉시 비활성화 + admin DM
      - BadRequest (토픽 삭제 등): 즉시 비활성화
      - 일반 Exception (네트워크): 누적 3회 시 비활성화
    """
    from telegram.error import Forbidden, BadRequest

    if not chat_id:
        chat_id = config.get('group_id')
        topic_id = config.get('topic_id')
    try:
        await bot.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text=f"⏰ 리마인더\n\n{text}"
        )
        print(f"📩 리마인더 발송: chat={chat_id} topic={topic_id}")
        if reminder_id in REMINDER_FAIL_COUNT:
            del REMINDER_FAIL_COUNT[reminder_id]
    except Forbidden as e:
        print(f"🚫 리마인더 봇 추방: chat={chat_id} id={reminder_id} err={e}")
        await _deactivate_reminder(bot, reminder_id, chat_id, "봇 추방 (Forbidden)", text)
    except BadRequest as e:
        msg = str(e).lower()
        if 'message thread' in msg or 'topic' in msg or 'chat not found' in msg:
            print(f"🚫 리마인더 토픽/채팅 미존재: chat={chat_id} id={reminder_id} err={e}")
            await _deactivate_reminder(bot, reminder_id, chat_id, f"BadRequest: {e}", text)
        else:
            print(f"❌ 리마인더 BadRequest: chat={chat_id} id={reminder_id} err={e}")
    except Exception as e:
        print(f"❌ 리마인더 발송 실패: chat={chat_id} topic={topic_id} id={reminder_id} err={e}")
        if reminder_id:
            REMINDER_FAIL_COUNT[reminder_id] = REMINDER_FAIL_COUNT.get(reminder_id, 0) + 1
            if REMINDER_FAIL_COUNT[reminder_id] >= REMINDER_MAX_FAIL:
                await _deactivate_reminder(
                    bot, reminder_id, chat_id,
                    f"연속 {REMINDER_MAX_FAIL}회 발송 실패", text
                )
                del REMINDER_FAIL_COUNT[reminder_id]

async def send_broadcast_reminder(bot, text):
    BROADCAST_GROUPS = config.get('broadcast_groups')
    for group in BROADCAST_GROUPS:
        try:
            await bot.send_message(
                chat_id=group["id"],
                message_thread_id=group["topic_id"],
                text=f"⏰ 리마인더\n\n{text}"
            )
        except Exception as e:
            print(f"브로드캐스트 리마인더 오류 {group['name']}: {e}")

async def send_daily_missing_summary(bot):
    """매일 20:05 서무에게 보고서 미완성 (필수 필드 누락) 현황 DM (2026-05-14).
    stage='missing' 기록을 KST 당일로 필터링, 보고서 타입별 그룹화.
    0건이면 발송 안 함 (silent OK — 정상 운영 신호)."""
    import sqlite3
    SECRETARY_ID = 754270008
    try:
        conn = sqlite3.connect('data/gabong.db')
        cur = conn.cursor()
        cur.execute("""
            SELECT report_type, user_id, detail,
                   strftime('%H:%M', created_at) as t
            FROM report_log
            WHERE stage = 'missing'
              AND date(created_at) = date('now', 'localtime')
            ORDER BY report_type, created_at
        """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            print("📊 일일 미완성 요약: 0건 (발송 안 함)")
            return

        def get_user_name(uid):
            try:
                c2 = sqlite3.connect('data/gabong.db')
                cur2 = c2.cursor()
                cur2.execute(
                    "SELECT user_name FROM messages WHERE user_id=? "
                    "AND user_name IS NOT NULL "
                    "ORDER BY timestamp DESC LIMIT 1", (uid,)
                )
                r = cur2.fetchone()
                c2.close()
                return r[0] if r and r[0] else f"ID:{uid}"
            except Exception:
                return f"ID:{uid}"

        grouped = {'service': [], 'mou': [], 'award': []}
        for report_type, user_id, detail, t in rows:
            if report_type in grouped:
                grouped[report_type].append((user_id, detail, t))

        today = datetime.now().strftime('%Y-%m-%d')
        msg = f"📊 보고서 미완성 현황 ({today})\n\n"
        labels = {'service': '봉사', 'mou': 'MOU', 'award': '수상'}
        total = 0
        for key in ['service', 'mou', 'award']:
            items = grouped[key]
            msg += f"[{labels[key]}] {len(items)}건\n"
            for uid, detail, t in items:
                name = get_user_name(uid)
                miss = (detail or '').replace('missing: ', '') or '?'
                msg += f"- {name}: {miss} ({t})\n"
            msg += "\n"
            total += len(items)

        msg += f"총 {total}건 미완성"

        await bot.send_message(chat_id=SECRETARY_ID, text=msg)
        print(f"📊 일일 미완성 요약 발송: {total}건 → {SECRETARY_ID}")
    except Exception as e:
        print(f"❌ 일일 미완성 요약 실패: {e}")


def cleanup_old_missing():
    """30일 이상 된 stage='missing' 기록 정리 (매일 03:10).
    report_log 의 'missing' stage 만 별도 정리 — 다른 stage 는 cleanup_report_log (90일) 그대로."""
    import sqlite3
    try:
        conn = sqlite3.connect('data/gabong.db')
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM report_log WHERE stage='missing' "
            "AND date(created_at) < date('now', '-30 days')"
        )
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        print(f"🗑️ 30일 지난 missing 기록 삭제: {deleted}건")
    except Exception as e:
        print(f"❌ missing 삭제 실패: {e}")


async def send_daily_summary(bot):
    SUMMARY_GROUPS = config.get('summary_groups')
    MY_USER_ID = config.get('my_user_id')

    # 오늘 KST 00:00 → UTC 변환 (KST = UTC+9)
    now_kst = datetime.utcnow() + timedelta(hours=9)
    since_utc = now_kst.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=9)

    for group_id_str, group_name in SUMMARY_GROUPS.items():
        try:
            group_id = int(group_id_str)

            # GROUP_MESSAGES(int 키) 대신 SQLite에서 직접 조회 → 재시작 후에도 유지
            rows = fetch_weekly_messages(group_id, since_utc)
            user_msgs = [r for r in rows if r["role"] == "user"]

            if user_msgs:
                history = "\n".join(f"{r['user_name']}: {r['text']}" for r in user_msgs)
                question = f"다음은 오늘 '{group_name}' 그룹의 대화 내용입니다. 핵심 내용을 한국어로 요약해주세요:\n{history}"
                summary = ask_claude(question)
                await bot.send_message(
                    chat_id=MY_USER_ID,
                    text=f"📋 일일 요약 - {group_name}\n\n{summary}"
                )
                GROUP_MESSAGES.pop(group_id, None)
            else:
                await bot.send_message(
                    chat_id=MY_USER_ID,
                    text=f"📋 일일 요약 - {group_name}\n\n오늘 대화 내용이 없습니다."
                )
        except Exception as e:
            print(f"요약 오류: {e}")

async def check_changes(app):
    consecutive_errors = 0
    NORMAL_INTERVAL = 60       # 정상 시 60초마다
    MAX_BACKOFF = 600          # 오류 시 최대 10분

    while True:
        try:
            rows = get_sheet_data()
            consecutive_errors = 0
            cache = load_cache()
            new_cache = {}
            for i, row in enumerate(rows[4:9]):
                key = str(i)
                row_str = str(row)
                new_cache[key] = row_str
                if key in cache and cache[key] != row_str and row[0]:
                    # 디바운싱: 같은 행 알림 후 30분 내 추가 변경은 silent skip
                    now_ts = _time_mod.time()
                    last = LAST_SHEET_NOTIFY.get(key, 0)
                    if now_ts - last < SHEET_NOTIFY_INTERVAL:
                        elapsed = int(now_ts - last)
                        remaining = SHEET_NOTIFY_INTERVAL - elapsed
                        print(f"⏸️ sheet 알림 디바운싱: row={key} (last={elapsed}s ago, {remaining}s 후 가능)")
                        continue
                    LAST_SHEET_NOTIFY[key] = now_ts
                    GROUP_ID = config.get('group_id')
                    TOPIC_ID = config.get('topic_id')
                    msg = (
                        f"📋 업무 현황 변경!\n\n"
                        f"과명: {row[0]}\n회의 일자: {row[1]}\n회의 안건: {row[2]}\n"
                        f"금주 진행 일정: {row[8]}\n금주 진행 현황: {row[9]}"
                    )
                    print(f"📋 sheet 변경 감지 → 알림: row={key} content={str(row[0])[:30]!r}")
                    await app.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
            save_cache(new_cache)
            await asyncio.sleep(NORMAL_INTERVAL)

        except asyncio.CancelledError:
            print("[Sheets] check_changes 태스크 종료")
            return

        except Exception as e:
            consecutive_errors += 1
            wait = min(NORMAL_INTERVAL * consecutive_errors, MAX_BACKOFF)
            print(f"[Sheets] 오류 ({consecutive_errors}회 연속): {e}")
            if consecutive_errors == 1:
                print("[Sheets] Google 서비스 계정 키가 유효한지 확인하세요.")
            print(f"[Sheets] {wait}초 후 재시도...")
            try:
                await asyncio.sleep(wait)
            except asyncio.CancelledError:
                print("[Sheets] check_changes 태스크 종료")
                return

# 런타임 데이터
CHAT_HISTORY = {}
GROUP_MESSAGES = {}

_LAST_MENTION_FILE = './data/last_mention.json'

def _load_last_mention() -> dict:
    os.makedirs('./data', exist_ok=True)
    if os.path.exists(_LAST_MENTION_FILE):
        try:
            with open(_LAST_MENTION_FILE, 'r') as f:
                raw = json.load(f)
            return {int(k): v for k, v in raw.items()}
        except Exception as e:
            print(f"[LAST_MENTION] 로드 오류: {e}")
    return {}

def save_last_mention(data: dict):
    os.makedirs('./data', exist_ok=True)
    try:
        with open(_LAST_MENTION_FILE, 'w') as f:
            json.dump({str(k): v for k, v in data.items()}, f)
    except Exception as e:
        print(f"[LAST_MENTION] 저장 오류: {e}")

LAST_MENTION = _load_last_mention()
scheduler = AsyncIOScheduler()

def get_config():
    """config.json 파일에서 설정을 로드"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config.json 파일을 찾을 수 없습니다.")
        return {}
    except json.JSONDecodeError as e:
        print(f"config.json 파싱 오류: {e}")
        return {}

def get_scheduler():
    """스케줄러 인스턴스 반환"""
    return scheduler
# ============================================================================
# 로깅 설정
# ============================================================================
import logging

os.makedirs('logs', exist_ok=True)

# 로거 생성
logger = logging.getLogger('gabong_bot')
logger.setLevel(logging.DEBUG)

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 파일 핸들러
file_handler = logging.FileHandler('logs/bot.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
# ── 권한 체크 (permissions) ────────────────────────────────────
import config as _config

def is_admin(user_id: int) -> bool:
    return user_id in _config.get('admin_ids', [])

async def check_admin(update, context) -> bool:
    if not is_admin(update.effective_user.id):
        return False
    return True
