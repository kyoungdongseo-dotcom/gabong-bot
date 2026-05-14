"""일일 미완성 요약 DM 통합 검증 (2026-05-15).

실행:
    cd ~/gabong-bot && source venv/bin/activate
    python3 scripts/test_missing_summary.py

기능:
- 환경 진단 (timezone, 토큰 위치, scheduler 설정)
- 토큰 자동 탐지 (다중 소스 fallback)
- 시나리오 1: 테스트 데이터 2건 → 발송 검증
- 시나리오 2: 0건 → 발송 안 함 검증
"""
import asyncio
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

# 프로젝트 루트로 이동 (scripts/ 에서 실행되어도 OK)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

KST = timezone(timedelta(hours=9))


def diagnose_environment():
    """환경 진단 — timezone / 토큰 / DB 상태."""
    print('=' * 60)
    print('환경 진단')
    print('=' * 60)

    # 1) 시스템 시각/timezone
    try:
        sys_date = subprocess.check_output(['date'], text=True).strip()
        print(f'시스템 시각: {sys_date}')
    except Exception as e:
        print(f'⚠️ date 명령 실패: {e}')

    print(f'Python now()  : {datetime.now()}')
    print(f'Python KST    : {datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S %Z")}')
    print(f'Python UTC    : {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")}')

    # 2) /etc/timezone 또는 /etc/localtime
    for path in ['/etc/timezone']:
        if os.path.exists(path):
            with open(path) as f:
                print(f'{path}: {f.read().strip()}')
    if os.path.lexists('/etc/localtime'):
        try:
            tz = os.readlink('/etc/localtime')
            print(f'/etc/localtime → {tz}')
        except OSError:
            pass

    # 3) APScheduler timezone (utils 의 scheduler 인스턴스)
    print()
    try:
        from utils import scheduler
        print(f'APScheduler timezone: {scheduler.timezone}')
    except Exception as e:
        print(f'⚠️ scheduler import 실패: {e}')

    # 4) DB created_at sample (timezone 추정)
    print()
    try:
        conn = sqlite3.connect('data/gabong.db')
        cur = conn.cursor()
        cur.execute(
            "SELECT created_at FROM report_log "
            "ORDER BY id DESC LIMIT 3"
        )
        rows = cur.fetchall()
        conn.close()
        print('최근 report_log.created_at 3건:')
        for r in rows:
            print(f'  {r[0]}')
        if rows:
            db_hour = int(rows[0][0][11:13])
            sys_hour = datetime.now().hour
            kst_hour = datetime.now(KST).hour
            print(f'DB hour={db_hour}, sys hour={sys_hour}, KST hour={kst_hour}')
            if abs(db_hour - kst_hour) <= 1:
                print('  → DB created_at 는 KST 로 추정')
            elif abs(db_hour - kst_hour) >= 8:
                print('  → DB created_at 는 UTC 로 추정 (KST 와 9시간 차)')
    except Exception as e:
        print(f'⚠️ DB 조회 실패: {e}')

    print()


def get_bot_token():
    """가봉봇 토큰 탐지 — config.json 우선 (운영 봇 main.py 와 일치).
    Why: .env 에 다른 봇 (세계경제봇 등) 토큰이 들어있을 수 있어 우선순위 역전 필요.
    main.py:179 는 config.get('telegram_token') 사용 → 검증 스크립트도 동일 출처."""
    # 1) config.json (가봉봇, 운영 봇)
    try:
        with open('config.json') as f:
            cfg = json.load(f)
        for k in ['telegram_token', 'bot_token', 'token']:
            if cfg.get(k):
                return cfg[k], f'config.json:{k}'
    except Exception:
        pass

    # 2) .env fallback (단, 다른 봇 토큰일 수 있으니 주의)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    for var in ['TELEGRAM_TOKEN', 'BOT_TOKEN', 'TELEGRAM_BOT_TOKEN']:
        t = os.getenv(var)
        if t:
            return t, f'.env:{var}'

    return None, None


def insert_test_data():
    """테스트 데이터 2건 삽입 (KST 기준 오늘 시각)."""
    now_kst_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('data/gabong.db')
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO report_log (report_type, user_id, stage, status, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ('service', 97057565, 'missing', 'fail', 'missing: 지파명', now_kst_str)
    )
    cur.execute(
        "INSERT INTO report_log (report_type, user_id, stage, status, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ('mou', 97057565, 'missing', 'fail', 'missing: 협약명', now_kst_str)
    )
    conn.commit()
    conn.close()
    print(f'✅ 테스트 데이터 2건 삽입 (created_at={now_kst_str})')


def cleanup_today_missing():
    """오늘 (KST) missing 데이터 삭제."""
    today_kst = datetime.now(KST).strftime('%Y-%m-%d')
    conn = sqlite3.connect('data/gabong.db')
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM report_log WHERE stage='missing' "
        "AND substr(created_at, 1, 10) = ?", (today_kst,)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


async def main():
    diagnose_environment()

    print('=' * 60)
    print('토큰 탐지')
    print('=' * 60)
    token, source = get_bot_token()
    if not token:
        print('❌ 봇 토큰을 .env / config.json 어디서도 못 찾음')
        print('   확인: .env 의 TELEGRAM_TOKEN 또는 config.json 의 telegram_token')
        return
    print(f'✅ 토큰 출처: {source} (길이: {len(token)})')
    print()

    from utils import send_daily_missing_summary
    from telegram import Bot
    bot = Bot(token)

    print('=' * 60)
    print('시나리오 1: 2건 데이터 → DM 발송')
    print('=' * 60)
    cleanup_today_missing()
    insert_test_data()
    await send_daily_missing_summary(bot)
    print()

    print('=' * 60)
    print('시나리오 2: 0건 → DM 발송 안 함')
    print('=' * 60)
    deleted = cleanup_today_missing()
    print(f'  삭제: {deleted}건')
    await send_daily_missing_summary(bot)
    print()

    print('=' * 60)
    print('✅ 통합 검증 완료')
    print('   서무(754270008) 텔레그램 DM 1건 도착 확인 부탁')
    print('   (시나리오 1 발송, 시나리오 2 침묵)')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())
