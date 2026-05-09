"""
reminders.json → SQLite 마이그레이션 스크립트 (1회 실행용)

실행 방법:
  cd ~/gabong-bot
  source venv/bin/activate
  python migrate_reminders.py
"""
import json
import os
import sys

# gabong-bot 디렉토리에서 실행해야 config/database 임포트 가능
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from database import init_db, add_reminder, get_reminders

REMINDERS_FILE = "reminders.json"

# JSON days 숫자 → 한국어 요일
DAYS_NUM_TO_KR = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}


def migrate():
    if not os.path.exists(REMINDERS_FILE):
        print(f"[마이그레이션] {REMINDERS_FILE} 파일이 없습니다. 건너뜀.")
        return

    with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
        json_reminders = json.load(f)

    if not json_reminders:
        print("[마이그레이션] reminders.json이 비어 있습니다.")
        return

    init_db()

    existing = get_reminders()
    existing_keys = {(r["type"], r["time"], r["message"]) for r in existing}

    group_id = config.get("group_id")
    migrated = 0
    skipped = 0

    for r in json_reminders:
        r_type = r.get("type", "")
        time_str = r.get("time", "00:00")
        message = r.get("message", "")

        # 이미 SQLite에 동일 항목이 있으면 건너뜀
        if (r_type, time_str, message) in existing_keys:
            print(f"  [건너뜀] 이미 존재: type={r_type} time={time_str} msg={message[:30]}")
            skipped += 1
            continue

        # days 변환: [2] → "수", [6] → "일"
        days_list = r.get("days", [])
        day_of_week = r.get("days_display") or ",".join(
            DAYS_NUM_TO_KR.get(d, str(d)) for d in days_list
        )

        # destination 처리
        destination = r.get("destination", "group")
        if destination == "group":
            target_group_id = group_id
        else:
            target_group_id = destination  # broadcast 등 커스텀값 그대로 사용

        day_of_month = r.get("day_of_month", None)

        new_id = add_reminder(
            group_id=target_group_id,
            topic_id=None,
            r_type=r_type,
            message=message,
            time=time_str,
            day_of_week=day_of_week if r_type in ("weekly", "biweekly") else None,
            day_of_month=day_of_month if r_type == "monthly" else None,
        )
        print(f"  [마이그레이션 완료] id={new_id} type={r_type} time={time_str} days={day_of_week} msg={message[:40]}")
        migrated += 1

    print(f"\n[마이그레이션] 완료: {migrated}개 삽입, {skipped}개 건너뜀")


if __name__ == "__main__":
    migrate()
