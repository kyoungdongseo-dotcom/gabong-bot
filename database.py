import sqlite3
import json
import os
from datetime import datetime

os.makedirs("./data", exist_ok=True)
DB_PATH = "./data/gabong.db"

def get_conn():
    """DB 연결"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """테이블 생성 (최초 1회)"""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id    TEXT NOT NULL,
            topic_id    INTEGER,
            type        TEXT NOT NULL,
            message     TEXT NOT NULL,
            time        TEXT,
            day_of_week TEXT,
            day_of_month INTEGER,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            is_active   INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id    TEXT NOT NULL,
            topic_id    INTEGER,
            user_name   TEXT,
            text        TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_state (
            key     TEXT PRIMARY KEY,
            value   TEXT,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type  TEXT,
            description TEXT,
            stack_trace TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료")

def add_reminder(group_id, topic_id, r_type, message, time=None, day_of_week=None, day_of_month=None) -> int:
    """리마인더 추가 후 생성된 ID 반환"""
    conn = get_conn()
    cursor = conn.execute("""
        INSERT INTO reminders (group_id, topic_id, type, message, time, day_of_week, day_of_month)
        VALUES (?,?,?,?,?,?,?)
    """, (group_id, topic_id, r_type, message, time, day_of_week, day_of_month))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id

def get_reminders(r_type=None, group_id=None):
    """리마인더 조회"""
    conn = get_conn()
    query = "SELECT * FROM reminders WHERE is_active=1"
    params = []
    if r_type:
        query += " AND type=?"
        params.append(r_type)
    if group_id:
        query += " AND group_id=?"
        params.append(group_id)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_reminder(reminder_id):
    """리마인더 삭제"""
    conn = get_conn()
    conn.execute("UPDATE reminders SET is_active=0 WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()

def save_message(group_id, topic_id, user_name, text):
    """메시지 저장"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO messages (group_id, topic_id, user_name, text)
        VALUES (?,?,?,?)
    """, (group_id, topic_id, user_name, text))
    conn.commit()
    conn.close()

def get_messages(group_id, limit=100):
    """메시지 조회"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM messages
        WHERE group_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (group_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_messages(group_id):
    """메시지 정리"""
    conn = get_conn()
    conn.execute("DELETE FROM messages WHERE group_id=?", (group_id,))
    conn.commit()
    conn.close()

def set_state(key, value):
    """상태값 저장"""
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO bot_state (key, value, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
    """, (key, json.dumps(value)))
    conn.commit()
    conn.close()

def get_state(key, default=None):
    """상태값 조회"""
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return default

def log_error(error_type, description, stack_trace=""):
    """에러 로그"""
    conn = get_conn()
    conn.execute("""
        INSERT INTO error_logs (error_type, description, stack_trace)
        VALUES (?,?,?)
    """, (error_type, description, stack_trace))
    conn.commit()
    conn.close()
