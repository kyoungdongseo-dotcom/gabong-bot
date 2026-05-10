"""주간 운영 리포트 — 매주 월요일 10:00 KST 자동 + /weekly_ops 명령어"""

import asyncio
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from telegram import Update
from telegram.ext import ContextTypes

import config
from database import get_conn

KST = pytz.timezone('Asia/Seoul')
ADMIN_USER_ID = 97057565

# 13개 지파 — 미제출 감지 기준
EXPECTED_JIPA = {
    '도마', '다대오', '바돌', '안드레', '요한', '시몬',
    '맛디아', '서야', '빌립', '부야', '베드로', '마태'
}

REPORT_LABEL = {'service': '봉사', 'award': '수상', 'mou': 'MOU'}
REPORT_EMOJI = {'service': '📋', 'award': '🏆', 'mou': '🤝'}
BLOCK_LABEL = {
    'no_photos': '사진 0장',
    'photo_failed': '사진 다운로드 실패',
    'docx_fail': 'Word 생성 실패',
}

AWARD_SPREADSHEET_ID = '1MM79Y5rjOT-s8GnN1WGfnRb3Bq5iZA-Ro4fQzEGZoB4'


# ── 시트 헬퍼 ────────────────────────────────────────────────────────────────

def _get_service():
    scopes = config.get('google_scopes', ['https://www.googleapis.com/auth/spreadsheets'])
    creds = Credentials.from_service_account_file('serviceAccountKey.json', scopes=scopes)
    return build('sheets', 'v4', credentials=creds)


def _read_sheet(sheet_id, sheet_name, rng='A:Z'):
    try:
        service = _get_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{sheet_name}'!{rng}",
            valueRenderOption='FORMATTED_VALUE'
        ).execute()
        return result.get('values', [])
    except Exception as e:
        print(f"⚠️ 시트 읽기 실패 ({sheet_name}): {e}")
        return []


def _filter_by_date_range(rows, start, end, date_col_idx=0):
    matched = []
    for row in rows[1:]:  # skip header
        if len(row) > date_col_idx:
            val = str(row[date_col_idx])[:10]
            try:
                dt = datetime.strptime(val, '%Y-%m-%d').date()
                if start <= dt <= end:
                    matched.append(row)
            except (ValueError, TypeError):
                continue
    return matched


def _match_jipa(jipa_raw: str):
    """'대전지파' / '도마' 등에서 EXPECTED_JIPA 매칭"""
    if not jipa_raw:
        return None
    for exp in EXPECTED_JIPA:
        if exp in jipa_raw:
            return exp
    return None


# ── report_log 통계 ──────────────────────────────────────────────────────────

def collect_report_log_stats(days=7) -> dict:
    """report_log 에서 N일 통계 추출"""
    try:
        conn = get_conn()
        threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

        result = {
            'received': defaultdict(int),
            'blocked': defaultdict(lambda: defaultdict(int)),
            'photos_stats': defaultdict(lambda: {'ok': 0, 'fail': 0, 'count': 0}),
            'time_distribution': Counter(),
        }

        # 보고서별 접수 건수 (received stage)
        rows = conn.execute("""
            SELECT report_type, COUNT(*) as cnt
            FROM report_log
            WHERE stage = 'received' AND status = 'ok' AND created_at >= ?
            GROUP BY report_type
        """, (threshold,)).fetchall()
        for r in rows:
            result['received'][r['report_type']] = r['cnt']

        # 차단 사유별
        rows = conn.execute("""
            SELECT report_type, detail, COUNT(*) as cnt
            FROM report_log
            WHERE stage = 'finalize' AND status = 'fail' AND created_at >= ?
            GROUP BY report_type, detail
        """, (threshold,)).fetchall()
        for r in rows:
            reason = r['detail'] or 'unknown'
            result['blocked'][r['report_type']][reason] = r['cnt']

        # 사진 처리 통계 (detail = "ok=N fail=M")
        rows = conn.execute("""
            SELECT report_type, detail FROM report_log
            WHERE stage = 'photos_downloaded' AND created_at >= ?
        """, (threshold,)).fetchall()
        for r in rows:
            detail = r['detail'] or ''
            m = re.match(r'ok=(\d+) fail=(\d+)', detail)
            if m:
                ok, fail = int(m.group(1)), int(m.group(2))
                stat = result['photos_stats'][r['report_type']]
                stat['ok'] += ok
                stat['fail'] += fail
                stat['count'] += 1

        # 시간대별 (received)
        rows = conn.execute("""
            SELECT created_at FROM report_log
            WHERE stage = 'received' AND status = 'ok' AND created_at >= ?
        """, (threshold,)).fetchall()
        for r in rows:
            try:
                dt = datetime.strptime(r['created_at'], '%Y-%m-%d %H:%M:%S')
                result['time_distribution'][dt.hour] += 1
            except Exception:
                pass

        conn.close()
        return result
    except Exception as e:
        print(f"⚠️ collect_report_log_stats 오류: {e}")
        return {}


def detect_new_users(days=7) -> list:
    """1주일 내 첫 보고자 (지난 90일 동안 안 보낸 사람)"""
    try:
        conn = get_conn()
        now = datetime.now()
        recent_start = (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        past_start = (now - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')

        recent = set(r['user_id'] for r in conn.execute("""
            SELECT DISTINCT user_id FROM report_log
            WHERE stage = 'received' AND created_at >= ?
              AND user_id IS NOT NULL
        """, (recent_start,)).fetchall())

        past = set(r['user_id'] for r in conn.execute("""
            SELECT DISTINCT user_id FROM report_log
            WHERE stage = 'received'
              AND created_at >= ? AND created_at < ?
              AND user_id IS NOT NULL
        """, (past_start, recent_start)).fetchall())

        new_users = recent - past
        conn.close()
        return sorted(new_users)
    except Exception as e:
        print(f"⚠️ detect_new_users 오류: {e}")
        return []


def detect_resubmission_patterns(days=7) -> list:
    """같은 hash 1주일 내 N번 제출 (재제출 패턴)"""
    try:
        conn = get_conn()
        threshold = (datetime.now() - timedelta(days=days)).timestamp()
        rows = conn.execute("""
            SELECT report_type, submission_hash,
                   COUNT(*) as cnt,
                   GROUP_CONCAT(DISTINCT user_id) as users
            FROM recent_submissions
            WHERE submitted_at >= ?
            GROUP BY report_type, submission_hash
            HAVING cnt >= 2
            ORDER BY cnt DESC
            LIMIT 20
        """, (threshold,)).fetchall()
        result = []
        for r in rows:
            result.append({
                'report_type': r['report_type'],
                'hash': r['submission_hash'],
                'count': r['cnt'],
                'users': r['users'] or '',
            })
        conn.close()
        return result
    except Exception as e:
        print(f"⚠️ detect_resubmission 오류: {e}")
        return []


def collect_trend(days=7) -> dict:
    """이번주 vs 전주 비교"""
    try:
        conn = get_conn()
        now = datetime.now()
        this_start = (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        last_start = (now - timedelta(days=days * 2)).strftime('%Y-%m-%d %H:%M:%S')

        this_week = defaultdict(int)
        last_week = defaultdict(int)

        for r in conn.execute("""
            SELECT report_type, COUNT(*) as cnt FROM report_log
            WHERE stage = 'received' AND created_at >= ? AND created_at < ?
            GROUP BY report_type
        """, (last_start, this_start)).fetchall():
            last_week[r['report_type']] = r['cnt']

        for r in conn.execute("""
            SELECT report_type, COUNT(*) as cnt FROM report_log
            WHERE stage = 'received' AND created_at >= ?
            GROUP BY report_type
        """, (this_start,)).fetchall():
            this_week[r['report_type']] = r['cnt']

        blocked_this = conn.execute("""
            SELECT COUNT(*) c FROM report_log
            WHERE stage = 'finalize' AND status = 'fail' AND created_at >= ?
        """, (this_start,)).fetchone()['c']

        blocked_last = conn.execute("""
            SELECT COUNT(*) c FROM report_log
            WHERE stage = 'finalize' AND status = 'fail'
              AND created_at >= ? AND created_at < ?
        """, (last_start, this_start)).fetchone()['c']

        conn.close()
        return {
            'this_week': dict(this_week),
            'last_week': dict(last_week),
            'blocked_this': blocked_this,
            'blocked_last': blocked_last,
        }
    except Exception as e:
        print(f"⚠️ collect_trend 오류: {e}")
        return {}


# ── 시트 통계 ────────────────────────────────────────────────────────────────

def collect_sheet_stats(days=7) -> dict:
    """시트에서 지파별 제출 현황 + 미제출 지파"""
    sheet_id = config.get('spreadsheet_id', AWARD_SPREADSHEET_ID)
    end = datetime.now(KST).date()
    start = end - timedelta(days=days)

    service_rows = _read_sheet(sheet_id, '봉사리포트')
    service_recent = _filter_by_date_range(service_rows, start, end, 0)

    award_rows = _read_sheet(AWARD_SPREADSHEET_ID, '수상보고창')
    award_recent = _filter_by_date_range(award_rows, start, end, 0)

    mou_rows = _read_sheet(AWARD_SPREADSHEET_ID, '협약보고창')
    mou_recent = _filter_by_date_range(mou_rows, start, end, 0)

    def _count_jipa(rows, jipa_col=1):
        c = Counter()
        for row in rows:
            if len(row) > jipa_col:
                jipa = _match_jipa(str(row[jipa_col]).strip())
                if jipa:
                    c[jipa] += 1
        return c

    service_jipa = _count_jipa(service_recent, 1)
    award_jipa = _count_jipa(award_recent, 1)
    mou_jipa = _count_jipa(mou_recent, 1)

    activity = Counter(service_jipa) + Counter(award_jipa) + Counter(mou_jipa)
    submitted = set(activity.keys())
    missing = sorted(EXPECTED_JIPA - submitted)

    return {
        'service_count': len(service_recent),
        'award_count': len(award_recent),
        'mou_count': len(mou_recent),
        'activity': dict(activity),
        'missing': missing,
    }


# ── 리포트 빌더 ──────────────────────────────────────────────────────────────

def build_weekly_ops_report() -> str:
    now = datetime.now(KST)
    end = now.date()
    start = end - timedelta(days=7)
    period = f"{start.strftime('%m/%d')} ~ {end.strftime('%m/%d')}"

    log_stats = collect_report_log_stats(7)
    sheet_stats = collect_sheet_stats(7)
    new_users = detect_new_users(7)
    resubs = detect_resubmission_patterns(7)
    trend = collect_trend(7)

    received = log_stats.get('received', {})
    blocked = log_stats.get('blocked', {})
    total_received = sum(received.values())
    total_blocked = sum(sum(b.values()) for b in blocked.values())

    lines = [
        f"📊 주간 운영 리포트 ({period})",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🎯 요약",
    ]
    for rt in ['service', 'award', 'mou']:
        recv = received.get(rt, 0)
        blk = sum(blocked.get(rt, {}).values())
        normal = recv - blk
        lines.append(
            f"  {REPORT_EMOJI[rt]} {REPORT_LABEL[rt]}: {recv}건 "
            f"(정상 {normal}, 차단 {blk})"
        )

    missing = sheet_stats.get('missing', [])
    if missing:
        lines.append(f"  ⚠️ 미제출 지파: {', '.join(missing)} ({len(missing)}개)")
    else:
        lines.append("  ✅ 13개 지파 모두 제출 완료")

    if new_users:
        lines.append(f"  🆕 신규 사용자: {len(new_users)}명")

    lines.extend(["", "━━━━━━━━━━━━━━━━━━", ""])

    # 보고서별 상세
    lines.append("📋 보고서별 상세")
    for rt in ['service', 'award', 'mou']:
        recv = received.get(rt, 0)
        blk = blocked.get(rt, {})
        blk_total = sum(blk.values())
        normal = recv - blk_total
        lines.append(f"  {REPORT_EMOJI[rt]} {REPORT_LABEL[rt]}: {recv}건")
        lines.append(f"    ✅ 정상: {normal}건")
        if blk_total > 0:
            lines.append(f"    ❌ 차단: {blk_total}건")
            for reason, cnt in blk.items():
                rlabel = BLOCK_LABEL.get(reason, reason)
                lines.append(f"        - {rlabel}: {cnt}건")

    # 지파별 제출 현황 (미제출 강조)
    lines.extend(["", "📊 지파별 제출 현황 (1주일)"])
    activity = sheet_stats.get('activity', {})
    for jipa in sorted(EXPECTED_JIPA):
        cnt = activity.get(jipa, 0)
        if cnt == 0:
            lines.append(f"  ⚠️ {jipa}: 0건 (미제출)")
        else:
            lines.append(f"  • {jipa}: {cnt}건")

    # 트렌드
    if trend.get('last_week'):
        lines.extend(["", "📈 트렌드 (전주 대비)"])
        tw = trend['this_week']
        lw = trend['last_week']
        for rt in ['service', 'award', 'mou']:
            t = tw.get(rt, 0)
            l = lw.get(rt, 0)
            if l > 0:
                pct = round((t - l) / l * 100)
                arrow = '⬆️' if pct > 0 else ('⬇️' if pct < 0 else '➡️')
                lines.append(f"  • {REPORT_LABEL[rt]}: {l}건 → {t}건 ({arrow} {pct:+d}%)")
            else:
                lines.append(f"  • {REPORT_LABEL[rt]}: {l}건 → {t}건")
        bt = trend.get('blocked_this', 0)
        bl = trend.get('blocked_last', 0)
        recv_t = sum(tw.values()) or 1
        recv_l = sum(lw.values()) or 1
        rate_t = round(bt / recv_t * 100, 1)
        rate_l = round(bl / recv_l * 100, 1)
        lines.append(f"  • 차단율: {rate_l}% → {rate_t}%")
    else:
        lines.extend(["", "📈 트렌드: 전주 데이터 없음 (다음 주부터 비교 시작)"])

    # 신규 사용자
    if new_users:
        lines.extend(["", f"🆕 신규 사용자 {len(new_users)}명"])
        for uid in new_users[:10]:
            lines.append(f"  • user_id={uid}")
        if len(new_users) > 10:
            lines.append(f"  ... 외 {len(new_users) - 10}명")

    # 시간대별
    time_dist = log_stats.get('time_distribution', Counter())
    if time_dist:
        lines.extend(["", "🕐 시간대별 트래픽 (Top 5)"])
        for hour, cnt in time_dist.most_common(5):
            lines.append(f"  • {hour:02d}시: {cnt}건")

    # 재제출
    if resubs:
        lines.extend(["", f"🔄 재제출 패턴 ({len(resubs)}건)"])
        for r in resubs[:5]:
            label = REPORT_LABEL.get(r['report_type'], r['report_type'])
            lines.append(f"  • {label}: {r['count']}회 (users: {r['users']})")

    # 사진 통계
    photo_stats = log_stats.get('photos_stats', {})
    if photo_stats:
        lines.extend(["", "📸 사진 통계"])
        for rt, stat in photo_stats.items():
            label = REPORT_LABEL.get(rt, rt)
            cnt = stat['count']
            ok = stat['ok']
            fail = stat['fail']
            avg = round(ok / cnt, 1) if cnt > 0 else 0
            success_rate = round(ok / (ok + fail) * 100, 1) if (ok + fail) > 0 else 100
            lines.append(f"  • {label}: 평균 {avg}장/보고서, 성공률 {success_rate}%")

    # 다음 액션
    lines.extend(["", "━━━━━━━━━━━━━━━━━━", "💡 다음 액션 제안"])
    actions = []
    if missing:
        actions.append(f"미제출 지파 {len(missing)}개에 보고 안내: {', '.join(missing)}")
    if total_blocked > 0:
        actions.append(f"차단된 {total_blocked}건의 시트 정리/사용자 안내 확인")
    if resubs:
        actions.append(f"재제출 {len(resubs)}건 — 사용자 가이드 검토 필요")
    if not actions:
        actions.append("특별한 조치 불필요 — 운영 정상")
    for i, a in enumerate(actions, 1):
        lines.append(f"  {i}. {a}")

    if total_received == 0:
        lines.extend([
            "",
            "ℹ️ 이번 주 보고서 0건 — 의미있는 데이터는 1주일 후부터 시작됩니다."
        ])

    return "\n".join(lines)


# ── 발송 ─────────────────────────────────────────────────────────────────────

def _split_text(text: str, max_len: int = 4000) -> list:
    """텍스트 max_len 넘으면 줄 단위 분할"""
    if len(text) <= max_len:
        return [text]
    parts = []
    current = []
    cur_len = 0
    for line in text.split('\n'):
        line_len = len(line) + 1
        if cur_len + line_len > max_len and current:
            parts.append('\n'.join(current))
            current = [line]
            cur_len = line_len
        else:
            current.append(line)
            cur_len += line_len
    if current:
        parts.append('\n'.join(current))
    return parts


async def send_weekly_ops_report(bot):
    """매주 월 10:00 KST 자동"""
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, build_weekly_ops_report)
        for part in _split_text(text):
            await bot.send_message(chat_id=ADMIN_USER_ID, text=part)
        print(f"✅ 주간 운영 리포트 발송 완료 ({len(text)} chars)")
    except Exception as e:
        print(f"❌ 주간 운영 리포트 오류: {e}")
        try:
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"❌ 주간 운영 리포트 생성 실패: {e}"
            )
        except Exception:
            pass


async def weekly_ops_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/weekly_ops — 메인 관리자 즉시 조회"""
    if not update.message:
        return
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ 메인 관리자 전용 명령입니다.")
        return
    await update.message.reply_text("📊 주간 운영 리포트 생성 중... (수 초 소요)")
    loop = asyncio.get_running_loop()
    try:
        text = await loop.run_in_executor(None, build_weekly_ops_report)
        for part in _split_text(text):
            await update.message.reply_text(part)
    except Exception as e:
        await update.message.reply_text(f"❌ 리포트 생성 실패: {e}")
