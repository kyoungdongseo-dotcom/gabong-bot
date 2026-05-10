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

async def send_reminder(bot, chat_id, text):
    GROUP_ID = config.get('group_id')
    TOPIC_ID = config.get('topic_id')
    await bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=f"⏰ 리마인더\n\n{text}")

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

async def send_daily_summary(bot):
    SUMMARY_GROUPS = config.get('summary_groups')
    for group_id, group_name in SUMMARY_GROUPS.items():
        try:
            if group_id in GROUP_MESSAGES and GROUP_MESSAGES[group_id]:
                history = "\n".join(GROUP_MESSAGES[group_id])
                question = f"다음은 오늘 '{group_name}' 그룹의 대화 내용입니다. 핵심 내용을 한국어로 요약해주세요:\n{history}"
                summary = ask_claude(question)
                MY_USER_ID = config.get('my_user_id')
                await bot.send_message(
                    chat_id=MY_USER_ID,
                    text=f"📋 일일 요약 - {group_name}\n\n{summary}"
                )
                GROUP_MESSAGES[group_id] = []
            else:
                MY_USER_ID = config.get('my_user_id')
                await bot.send_message(
                    chat_id=MY_USER_ID,
                    text=f"📋 일일 요약 - {group_name}\n\n오늘 대화 내용이 없습니다."
                )
        except Exception as e:
            print(f"요약 오류: {e}")

async def check_changes(app):
    while True:
        try:
            rows = get_sheet_data()
            cache = load_cache()
            new_cache = {}
            for i, row in enumerate(rows[4:9]):
                key = str(i)
                row_str = str(row)
                new_cache[key] = row_str
                if key in cache and cache[key] != row_str and row[0]:
                    GROUP_ID = config.get('group_id')
                    TOPIC_ID = config.get('topic_id')
                    msg = f"📋 업무 현황 변경!\n\n과명: {row[0]}\n회의 일자: {row[1]}\n회의 안건: {row[2]}\n금주 진행 일정: {row[8]}\n금주 진행 현황: {row[9]}"
                    await app.bot.send_message(chat_id=GROUP_ID, message_thread_id=TOPIC_ID, text=msg)
            save_cache(new_cache)
        except Exception as e:
            print(f"오류: {e}")
        await asyncio.sleep(60)

# 런타임 데이터 (임시로 여기 둠, 나중에 별도 모듈로)
CHAT_HISTORY = {}
GROUP_MESSAGES = {}
LAST_MENTION = {}
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
