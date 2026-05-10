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

    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type     TEXT NOT NULL,
            pending_key     TEXT NOT NULL,
            data_json       TEXT NOT NULL,
            photos_json     TEXT NOT NULL,
            last_photo_time REAL DEFAULT 0,
            created         REAL NOT NULL,
            UNIQUE(report_type, pending_key)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_photos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type     TEXT NOT NULL,
            pending_key     TEXT NOT NULL,
            photos_json     TEXT NOT NULL,
            created         REAL NOT NULL,
            UNIQUE(report_type, pending_key)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS recent_submissions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type     TEXT NOT NULL,
            submission_hash TEXT NOT NULL,
            summary         TEXT,
            submitted_at    REAL NOT NULL
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_recent_sub_type
        ON recent_submissions(report_type, submitted_at)
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS report_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            user_id     INTEGER,
            chat_id     INTEGER,
            topic_id    INTEGER,
            message_id  INTEGER,
            stage       TEXT NOT NULL,
            status      TEXT NOT NULL,
            detail      TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_report_log_user
        ON report_log(user_id, created_at)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_report_log_type_stage
        ON report_log(report_type, stage, status)
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS format_help_sent (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            report_type TEXT NOT NULL,
            sent_at     REAL NOT NULL,
            UNIQUE(user_id, report_type)
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


# ── PENDING 보고서 영속화 ─────────────────────────────────────────────────────

def save_pending_report(report_type: str, pending_key: str, data: dict,
                        photos: list, last_photo_time: float, created: float):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO pending_reports
        (report_type, pending_key, data_json, photos_json, last_photo_time, created)
        VALUES (?,?,?,?,?,?)
    """, (report_type, pending_key, json.dumps(data, ensure_ascii=False),
          json.dumps(photos, ensure_ascii=False), last_photo_time, created))
    conn.commit()
    conn.close()


def delete_pending_report(report_type: str, pending_key: str):
    conn = get_conn()
    conn.execute("""
        DELETE FROM pending_reports WHERE report_type=? AND pending_key=?
    """, (report_type, pending_key))
    conn.commit()
    conn.close()


def load_pending_reports(report_type: str, max_age_sec: float = 600) -> list:
    """봇 재시작 시 복원용. 너무 오래된 항목은 제외."""
    conn = get_conn()
    threshold = datetime.now().timestamp() - max_age_sec
    rows = conn.execute("""
        SELECT * FROM pending_reports
        WHERE report_type=? AND created >= ?
    """, (report_type, threshold)).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            'pending_key': r['pending_key'],
            'data': json.loads(r['data_json']),
            'photos': json.loads(r['photos_json']),
            'last_photo_time': r['last_photo_time'],
            'created': r['created'],
        })
    return result


def cleanup_pending_reports_db(max_age_sec: float = 600):
    conn = get_conn()
    threshold = datetime.now().timestamp() - max_age_sec
    conn.execute("DELETE FROM pending_reports WHERE created < ?", (threshold,))
    conn.commit()
    conn.close()


def save_pending_photos_db(report_type: str, pending_key: str,
                           photos: list, created: float):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO pending_photos
        (report_type, pending_key, photos_json, created)
        VALUES (?,?,?,?)
    """, (report_type, pending_key,
          json.dumps(photos, ensure_ascii=False), created))
    conn.commit()
    conn.close()


def delete_pending_photos_db(report_type: str, pending_key: str):
    conn = get_conn()
    conn.execute("""
        DELETE FROM pending_photos WHERE report_type=? AND pending_key=?
    """, (report_type, pending_key))
    conn.commit()
    conn.close()


def load_pending_photos_db(report_type: str, max_age_sec: float = 300) -> list:
    conn = get_conn()
    threshold = datetime.now().timestamp() - max_age_sec
    rows = conn.execute("""
        SELECT * FROM pending_photos
        WHERE report_type=? AND created >= ?
    """, (report_type, threshold)).fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            'pending_key': r['pending_key'],
            'photos': json.loads(r['photos_json']),
            'created': r['created'],
        })
    return result


def cleanup_pending_photos_db(max_age_sec: float = 300):
    conn = get_conn()
    threshold = datetime.now().timestamp() - max_age_sec
    conn.execute("DELETE FROM pending_photos WHERE created < ?", (threshold,))
    conn.commit()
    conn.close()


# ── 중복 제출 감지 ─────────────────────────────────────────────────────────────

def record_submission(report_type: str, submission_hash: str, summary: str = ''):
    conn = get_conn()
    conn.execute("""
        INSERT INTO recent_submissions (report_type, submission_hash, summary, submitted_at)
        VALUES (?, ?, ?, ?)
    """, (report_type, submission_hash, summary, datetime.now().timestamp()))
    conn.commit()
    conn.close()


def find_recent_submission(report_type: str, submission_hash: str,
                           window_sec: float = 600) -> dict | None:
    """최근 N초 내 동일 hash 제출이 있으면 반환"""
    conn = get_conn()
    threshold = datetime.now().timestamp() - window_sec
    row = conn.execute("""
        SELECT * FROM recent_submissions
        WHERE report_type=? AND submission_hash=? AND submitted_at >= ?
        ORDER BY submitted_at DESC LIMIT 1
    """, (report_type, submission_hash, threshold)).fetchone()
    conn.close()
    return dict(row) if row else None


def cleanup_recent_submissions(max_age_sec: float = 86400) -> int:
    """24시간 이상 된 항목 정리. 정리 건수 반환 (실패 시 -1)."""
    try:
        conn = get_conn()
        threshold = datetime.now().timestamp() - max_age_sec
        cursor = conn.execute(
            "DELETE FROM recent_submissions WHERE submitted_at < ?",
            (threshold,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        hours = int(max_age_sec / 3600)
        print(f"✅ recent_submissions cleanup: {deleted}건 정리 ({hours}h 이전)")
        return deleted
    except Exception as e:
        print(f"⚠️ recent_submissions cleanup 실패: {e}")
        return -1


# ── 보고서 처리 단계 로그 ─────────────────────────────────────────────────────

def log_report_stage(report_type: str, stage: str, status: str,
                     user_id: int = None, chat_id: int = None,
                     topic_id: int = None, message_id: int = None,
                     detail: str = ''):
    """모든 보고서 처리 단계 추적용. 절대 throw 안 함 (best-effort)."""
    try:
        conn = get_conn()
        conn.execute("""
            INSERT INTO report_log
            (report_type, user_id, chat_id, topic_id, message_id, stage, status, detail)
            VALUES (?,?,?,?,?,?,?,?)
        """, (report_type, user_id, chat_id, topic_id, message_id, stage, status, detail[:500]))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ report_log 기록 실패: {e}")


def get_report_log_stats(report_type: str = None, hours: int = 24) -> dict:
    """최근 N시간 단계별/상태별 통계"""
    try:
        conn = get_conn()
        threshold = (datetime.now().timestamp() - hours * 3600)
        threshold_str = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d %H:%M:%S')
        query = """
            SELECT stage, status, COUNT(*) as cnt FROM report_log
            WHERE created_at >= ?
        """
        params = [threshold_str]
        if report_type:
            query += " AND report_type=?"
            params.append(report_type)
        query += " GROUP BY stage, status"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        result = {}
        for r in rows:
            result.setdefault(r['stage'], {})[r['status']] = r['cnt']
        return result
    except Exception:
        return {}


def cleanup_report_log(max_age_days: int = 90) -> int:
    """N일 이상 된 단계 로그 정리. 정리 건수 반환 (실패 시 -1).
    기본값 90일 (분기 통계 + 디버깅 여유 보장)."""
    try:
        conn = get_conn()
        threshold = (datetime.now().timestamp() - max_age_days * 86400)
        threshold_str = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d %H:%M:%S')
        cursor = conn.execute(
            "DELETE FROM report_log WHERE created_at < ?", (threshold_str,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"✅ report_log cleanup: {deleted}건 정리 ({max_age_days}일 이전)")
        return deleted
    except Exception as e:
        print(f"⚠️ report_log cleanup 실패: {e}")
        return -1


def get_user_reports(user_id: int, days: int = 30) -> list:
    """보고자별 최근 제출 이력 (보고서 단위, 최신순)"""
    try:
        conn = get_conn()
        threshold = (datetime.now().timestamp() - days * 86400)
        threshold_str = datetime.fromtimestamp(threshold).strftime('%Y-%m-%d %H:%M:%S')
        rows = conn.execute("""
            SELECT report_type, message_id, status, detail, created_at
            FROM report_log
            WHERE user_id = ?
              AND stage = 'received'
              AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (user_id, threshold_str)).fetchall()
        result = []
        for r in rows:
            # 같은 user/type/message_id 의 finalize 결과 조회
            final = conn.execute("""
                SELECT stage, status, detail FROM report_log
                WHERE user_id = ? AND report_type = ?
                  AND created_at >= ?
                  AND stage IN ('sheet_saved', 'finalize', 'reporter_ack_sent')
                ORDER BY id DESC LIMIT 5
            """, (user_id, r['report_type'], r['created_at'])).fetchall()
            stages = {f['stage']: f['status'] for f in final}
            if stages.get('finalize') == 'fail':
                outcome = 'fail'
            elif stages.get('sheet_saved') == 'ok':
                outcome = 'ok'
            elif stages.get('sheet_saved') == 'fail':
                outcome = 'sheet_fail'
            elif stages.get('reporter_ack_sent') == 'ok':
                outcome = 'partial'
            else:
                outcome = 'unknown'
            result.append({
                'report_type': r['report_type'],
                'detail': r['detail'] or '',
                'created_at': r['created_at'],
                'outcome': outcome,
            })
        conn.close()
        return result
    except Exception as e:
        print(f"⚠️ get_user_reports 오류: {e}")
        return []


# ── 형식 안내 1일 1회 추적 ────────────────────────────────────────────────────

def should_send_format_help(user_id: int, report_type: str,
                            cooldown_hours: int = 24) -> bool:
    """24시간 내 같은 user/type 안내 보낸 적 없으면 True."""
    try:
        conn = get_conn()
        threshold = datetime.now().timestamp() - cooldown_hours * 3600
        row = conn.execute("""
            SELECT sent_at FROM format_help_sent
            WHERE user_id = ? AND report_type = ?
        """, (user_id, report_type)).fetchone()
        conn.close()
        if row is None:
            return True
        return row['sent_at'] < threshold
    except Exception:
        return True


def mark_format_help_sent(user_id: int, report_type: str):
    try:
        conn = get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO format_help_sent
            (user_id, report_type, sent_at)
            VALUES (?, ?, ?)
        """, (user_id, report_type, datetime.now().timestamp()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ mark_format_help_sent 오류: {e}")
