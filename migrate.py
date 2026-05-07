import json
import os
from database import init_db, add_reminder

def migrate_reminders():
    """reminders.json → SQLite 마이그레이션"""
    init_db()
    
    reminders_path = "/data/reminders.json"
    
    if not os.path.exists(reminders_path):
        print("⚠️ reminders.json 없음 - 마이그레이션 스킵")
        return
    
    try:
        with open(reminders_path, 'r') as f:
            reminders = json.load(f)
        
        for item in reminders:
            add_reminder(
                group_id=item.get("group_id") or item.get("chat_id", 0),
                topic_id=item.get("topic_id"),
                r_type=item.get("type"),
                message=item.get("text") or item.get("message"),
                time=item.get("time"),
                day_of_week=item.get("days"),
                day_of_month=int(item.get("day")) if item.get("day") else None
            )
        
        print(f"✅ {len(reminders)}개 리마인더 마이그레이션 완료")
        
        # 백업
        backup_path = "/data/reminders.json.bak"
        os.rename(reminders_path, backup_path)
        print(f"✅ 백업: {backup_path}")
        
    except Exception as e:
        print(f"❌ 마이그레이션 오류: {e}")

if __name__ == "__main__":
    migrate_reminders()
