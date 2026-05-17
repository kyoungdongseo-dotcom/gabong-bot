"""주간 뉴스 클리핑 핸들러.

명령어:
- /news_collect : 즉시 수집 → 후보 시트
- /news_status  : 권역별 후보/체크 현황
- /send_news    : 체크된 후보 12개 그룹 일괄 발송 → 발송이력 이동 + 후보 삭제

자동:
- scheduled_weekly_collect : 일요일 22:00 KST (plugin 에서 등록)

권한: AUTHORIZED_USERS = config.admin_ids (6명).
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import pytz
from telegram import Update
from telegram.ext import ContextTypes

import config
from services.news_collector import (
    CANDIDATE_HEADERS, CANDIDATE_SHEET,
    REGION_QUERY_MAP, collect_all_regions, save_candidates_to_sheet,
    _ensure_worksheet, _get_gspread_client,
)
from utils.week_label import get_week_label

KST = pytz.timezone("Asia/Seoul")

ADMIN_USER_ID = config.get("my_user_id", 97057565)
AUTHORIZED_USERS = set(config.get("admin_ids", []) or [])

HISTORY_SHEET = "발송이력"
SETTINGS_SHEET = "권역설정"

HISTORY_HEADERS = ["발송일자", "권역", "지파", "지역", "카테고리", "제목", "링크", "출처"]
SETTINGS_HEADERS = ["권역", "지파", "그룹ID", "토픽ID", "활성"]

SEND_GAP_SEC = 0.3
DM_DELETE_AFTER = 5

# 권역 ↔ 지파 매핑 (tribes_mapping union 이름과 다른 케이스 "강원지역" 보정)
REGION_TO_TRIBE: dict[str, str] = {
    "서울경기남부": "요한",
    "서울경기북부": "시몬",
    "서울경기동부": "서울야고보",
    "서울경기서부": "바돌로매",
    "인천": "마태",
    "강원": "빌립",
    "대구경북": "다대오",
    "대전충청": "맛디아",
    "전북": "도마",
    "광주전남": "베드로",
    "부산경남서부": "부산야고보",
    "부산경남동부": "안드레",
}

# broadcast_groups 의 이름 토큰 → 정식 지파명 alias
NAME_ALIASES = {
    "서야": "서울야고보",
    "바돌": "바돌로매",
    "부야": "부산야고보",
}


def _spreadsheet_id() -> str:
    sid = (config.get("news_clipping", {}) or {}).get("spreadsheet_id", "")
    if not sid or sid == "사용자_제공_예정_PLACEHOLDER":
        raise ValueError(
            "news_clipping.spreadsheet_id 가 config.json 에 설정되지 않았습니다. "
            "사용자 수동 입력 필요"
        )
    return sid


def _extract_tribe_from_group_name(name: str) -> str | None:
    """'총회-도마 위아원' → '도마' → '도마'. 'XX 위아원' 패턴 깨지면 None."""
    if not name:
        return None
    rest = name.replace("총회-", "").strip()
    token = rest.split(" ", 1)[0].split("위아원", 1)[0].strip()
    return NAME_ALIASES.get(token, token)


def _build_default_settings_rows() -> list[list]:
    """config.broadcast_groups 기반으로 12권역 초기 시드."""
    bg = config.get("broadcast_groups", []) or []
    tribe_to_group: dict[str, dict] = {}
    for entry in bg:
        tribe = _extract_tribe_from_group_name(entry.get("name", ""))
        if not tribe:
            continue
        tribe_to_group[tribe] = {
            "group_id": entry.get("id"),
            "topic_id": entry.get("topic_id"),
        }

    rows: list[list] = []
    for region, tribe in REGION_TO_TRIBE.items():
        g = tribe_to_group.get(tribe, {})
        rows.append([
            region, tribe,
            str(g.get("group_id", "")) if g.get("group_id") is not None else "",
            str(g.get("topic_id", "")) if g.get("topic_id") is not None else "",
            "TRUE",
        ])
    return rows


# ── 권한 / DM 유틸 ────────────────────────────────────────────────────────────

async def _delete_later(bot, chat_id: int, message_id: int, delay: int = DM_DELETE_AFTER):
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def _deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id in AUTHORIZED_USERS:
        return False
    try:
        msg = await update.message.reply_text(
            "❌ 관리자만 사용 가능합니다.",
            disable_notification=True,
        )
        asyncio.create_task(
            _delete_later(context.bot, msg.chat_id, msg.message_id)
        )
    except Exception:
        pass
    return True


async def _notify_admin(bot, text: str):
    try:
        await bot.send_message(chat_id=ADMIN_USER_ID, text=text[:4000])
    except Exception as e:
        print(f"⚠️ 관리자 DM 실패: {e}")


# ── 시트 R/W ──────────────────────────────────────────────────────────────────

def _open_spreadsheet():
    gc = _get_gspread_client()
    return gc.open_by_key(_spreadsheet_id())


def _read_all(ws) -> list[list]:
    """ws.get_all_values() 의 가벼운 래퍼. 헤더 행 포함."""
    return ws.get_all_values()


def _ensure_settings_sheet(ss):
    ws, created = _ensure_worksheet(ss, SETTINGS_SHEET, SETTINGS_HEADERS)
    if created:
        seed = _build_default_settings_rows()
        ws.append_rows(seed, value_input_option="USER_ENTERED")
        print(f"✅ 권역설정 시트 시드 {len(seed)}건 초기화")
    else:
        existing_regions = {row[0] for row in ws.get_all_values()[1:] if row}
        seed = _build_default_settings_rows()
        missing = [row for row in seed if row[0] not in existing_regions]
        if missing:
            ws.append_rows(missing, value_input_option="USER_ENTERED")
            print(f"✅ 권역설정 시트 누락 {len(missing)}건 추가")
    return ws


def _ensure_history_sheet(ss):
    ws, _ = _ensure_worksheet(ss, HISTORY_SHEET, HISTORY_HEADERS)
    return ws


def _read_active_region_map(settings_ws) -> dict[str, dict]:
    """권역설정 시트 → {권역: {tribe, group_id, topic_id, active}}."""
    out: dict[str, dict] = {}
    rows = settings_ws.get_all_values()
    if not rows or len(rows) < 2:
        return out
    for row in rows[1:]:
        if len(row) < 5 or not row[0]:
            continue
        region = row[0].strip()
        active = (row[4] or "").strip().upper() in ("TRUE", "T", "Y", "1", "YES")
        try:
            group_id = int(row[2]) if row[2] else None
        except ValueError:
            group_id = None
        try:
            topic_id = int(row[3]) if row[3] else None
        except ValueError:
            topic_id = None
        out[region] = {
            "tribe": row[1].strip(),
            "group_id": group_id,
            "topic_id": topic_id,
            "active": active,
        }
    return out


def _read_candidates(candidates_ws) -> tuple[list[dict], list[int]]:
    """후보 시트 전체 → (rows_dict, sheet_row_numbers).

    sheet_row_numbers: 1-based 행 번호 (헤더 제외) — 삭제용.
    """
    raw = candidates_ws.get_all_values()
    if not raw or len(raw) < 2:
        return [], []
    headers = raw[0]
    out: list[dict] = []
    row_numbers: list[int] = []
    for i, row in enumerate(raw[1:], start=2):
        d = {h: (row[j] if j < len(row) else "") for j, h in enumerate(headers)}
        out.append(d)
        row_numbers.append(i)
    return out, row_numbers


# ── 발송 포맷팅 ───────────────────────────────────────────────────────────────

def _format_region_message(region: str, items: list[dict], week_label: str) -> str:
    lines = [f"[ {region} 지역 뉴스클리핑 ] - {week_label}", ""]
    if not items:
        lines.append("이번 주는 특이사항 없음")
        return "\n".join(lines)

    for it in items:
        area = it.get("지역", "") or region
        title = it.get("제목", "")
        link = it.get("링크", "")
        summary = it.get("요약", "")
        category = it.get("카테고리", "") or "📰 기타 정보"
        lines.append(f"■ {area} ({category})")
        lines.append(title)
        lines.append(link)
        lines.append(f"✅ {summary}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ── 명령어 ────────────────────────────────────────────────────────────────────

async def cmd_news_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔍 cmd_news_collect 호출 by {update.effective_user.id if update.effective_user else '?'}", flush=True)
    if await _deny(update, context):
        return

    progress = await update.message.reply_text("📰 뉴스 수집 중... (최대 3분)")
    print("🔍 collect_all_regions 호출 시작", flush=True)
    try:
        candidates = await asyncio.wait_for(
            collect_all_regions(),
            timeout=180,  # 3분 safety
        )
        total = sum(len(v) for v in candidates.values())
        print(f"🔍 collect_all_regions 완료: {total}건", flush=True)
    except asyncio.TimeoutError:
        print("❌ 전체 수집 timeout (3분 초과)", flush=True)
        await progress.edit_text("❌ 수집 시간 초과 (3분). 다시 시도해주세요.")
        await _notify_admin(context.bot, "❌ /news_collect timeout (180s 초과)")
        return
    except ValueError as e:
        await progress.edit_text(f"❌ 수집 실패: {e}")
        await _notify_admin(context.bot, f"❌ /news_collect 환경설정 오류: {e}")
        return
    except Exception as e:
        print(f"❌ 수집 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
        await progress.edit_text(f"❌ 수집 중 예외: {str(e)[:200]}")
        await _notify_admin(context.bot, f"❌ /news_collect 예외: {e}")
        return

    try:
        print("🔍 save_candidates_to_sheet 호출", flush=True)
        await _ensure_settings_seed_async()
        result = await asyncio.to_thread(
            save_candidates_to_sheet, candidates, REGION_TO_TRIBE
        )
        print("✅ 시트 저장 완료", flush=True)
    except Exception as e:
        print(f"❌ 시트 저장 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
        await progress.edit_text(f"❌ 시트 저장 실패: {str(e)[:200]}")
        await _notify_admin(context.bot, f"❌ /news_collect 시트 저장 실패: {e}")
        return

    by_region = result.get("by_region", {})
    lines = ["✅ 수집 완료. 권역별 건수:"]
    for region in REGION_QUERY_MAP:
        lines.append(f"  • {region}: {by_region.get(region, 0)}건")
    lines.append(f"\n총 {result.get('appended', 0)}건 추가")
    await progress.edit_text("\n".join(lines))


async def cmd_news_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _deny(update, context):
        return
    try:
        ss = await asyncio.to_thread(_open_spreadsheet)
        ws, _ = await asyncio.to_thread(
            _ensure_worksheet, ss, CANDIDATE_SHEET, CANDIDATE_HEADERS
        )
        rows, _ = await asyncio.to_thread(_read_candidates, ws)
    except Exception as e:
        await update.message.reply_text(f"❌ 상태 조회 실패: {str(e)[:200]}")
        return

    region_total: dict[str, int] = {}
    region_checked: dict[str, int] = {}
    for r in rows:
        region = r.get("권역", "") or "(미지정)"
        region_total[region] = region_total.get(region, 0) + 1
        if (r.get("발송", "") or "").upper() == "TRUE":
            region_checked[region] = region_checked.get(region, 0) + 1

    lines = ["📊 권역별 뉴스 후보 현황"]
    for region in REGION_QUERY_MAP:
        total = region_total.get(region, 0)
        checked = region_checked.get(region, 0)
        lines.append(f"  • {region}: {total}건 중 {checked}건 선별")
    other = [r for r in region_total if r not in REGION_QUERY_MAP]
    for r in other:
        lines.append(f"  • {r} (외): {region_total[r]}건 중 {region_checked.get(r, 0)}건")
    await update.message.reply_text("\n".join(lines))


async def cmd_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await _deny(update, context):
        return

    progress = await update.message.reply_text("📤 발송 준비 중...")
    try:
        ss = await asyncio.to_thread(_open_spreadsheet)
        cand_ws, _ = await asyncio.to_thread(
            _ensure_worksheet, ss, CANDIDATE_SHEET, CANDIDATE_HEADERS
        )
        settings_ws = await asyncio.to_thread(_ensure_settings_sheet, ss)
        history_ws = await asyncio.to_thread(_ensure_history_sheet, ss)
        rows, row_numbers = await asyncio.to_thread(_read_candidates, cand_ws)
        region_map = await asyncio.to_thread(_read_active_region_map, settings_ws)
    except Exception as e:
        await progress.edit_text(f"❌ 시트 접근 실패: {str(e)[:200]}")
        await _notify_admin(context.bot, f"❌ /send_news 시트 접근 실패: {e}")
        return

    # 체크된 행만 (sheet_row_no 함께 보존)
    checked: list[tuple[int, dict]] = []
    for sheet_row, r in zip(row_numbers, rows):
        if (r.get("발송", "") or "").upper() == "TRUE":
            checked.append((sheet_row, r))

    # 권역별 그루핑
    by_region: dict[str, list[tuple[int, dict]]] = {}
    for sheet_row, r in checked:
        region = r.get("권역", "")
        by_region.setdefault(region, []).append((sheet_row, r))

    week_label = get_week_label()

    # 발송: 활성 권역만 + 빈 권역은 "특이사항 없음" 발송
    success = 0
    failed = 0
    sent_rows: list[int] = []
    history_rows: list[list] = []
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    failure_log: list[str] = []

    for region, meta in region_map.items():
        if not meta.get("active"):
            continue
        group_id = meta.get("group_id")
        topic_id = meta.get("topic_id")
        if not group_id:
            failed += 1
            failure_log.append(f"{region}: group_id 누락")
            continue

        items = [r for _, r in by_region.get(region, [])]
        text = _format_region_message(region, items, week_label)

        send_kwargs = {"chat_id": group_id, "text": text}
        if topic_id:
            send_kwargs["message_thread_id"] = topic_id
        try:
            await context.bot.send_message(**send_kwargs)
            success += 1
            for sheet_row, r in by_region.get(region, []):
                sent_rows.append(sheet_row)
                history_rows.append([
                    today_str,
                    r.get("권역", ""),
                    r.get("지파", ""),
                    r.get("지역", ""),
                    r.get("카테고리", ""),
                    r.get("제목", ""),
                    r.get("링크", ""),
                    r.get("출처", ""),
                ])
        except Exception as e:
            failed += 1
            failure_log.append(f"{region}: {str(e)[:100]}")
            print(f"❌ /send_news {region} 실패: {e}")
        await asyncio.sleep(SEND_GAP_SEC)

    # 발송이력 시트 누적
    if history_rows:
        try:
            await asyncio.to_thread(
                history_ws.append_rows, history_rows,
                "USER_ENTERED",
            )
        except Exception as e:
            print(f"⚠️ 발송이력 저장 실패: {e}")
            await _notify_admin(context.bot, f"⚠️ 발송이력 저장 실패: {e}")

    # 발송 성공한 행 후보 시트에서 삭제 (내림차순)
    if sent_rows:
        try:
            for r in sorted(set(sent_rows), reverse=True):
                cand_ws.delete_rows(r)
        except Exception as e:
            print(f"⚠️ 후보 행 삭제 실패: {e}")
            await _notify_admin(context.bot, f"⚠️ 후보 행 삭제 실패: {e}")

    summary_lines = [
        "📤 뉴스클리핑 발송 결과",
        f"성공 {success} / 실패 {failed}",
    ]
    if failure_log:
        summary_lines.append("실패 상세:")
        summary_lines.extend(f"  - {line}" for line in failure_log[:12])

    await progress.edit_text("\n".join(summary_lines))
    await _notify_admin(context.bot, "\n".join(summary_lines))


# ── 스케줄 ────────────────────────────────────────────────────────────────────

async def _ensure_settings_seed_async():
    try:
        ss = await asyncio.to_thread(_open_spreadsheet)
        await asyncio.to_thread(_ensure_settings_sheet, ss)
    except Exception as e:
        print(f"⚠️ 권역설정 시트 시드 실패: {e}")


async def scheduled_weekly_collect(bot=None):
    """일요일 22:00 KST APScheduler 호출."""
    print(f"⏰ scheduled_weekly_collect 실행 ({datetime.now(KST).isoformat()})", flush=True)
    try:
        candidates = await asyncio.wait_for(
            collect_all_regions(),
            timeout=180,  # 3분 safety (cmd_news_collect 와 동일)
        )
        total = sum(len(v) for v in candidates.values())
        print(f"🔍 scheduled_weekly_collect 수집 완료: {total}건", flush=True)
    except asyncio.TimeoutError:
        print("❌ scheduled_weekly_collect timeout (180초 초과)", flush=True)
        if bot:
            await _notify_admin(
                bot,
                "❌ 주간 자동 수집 시간 초과 (3분).\n수동으로 /news_collect 시도 필요.",
            )
        return
    except ValueError as e:
        print(f"❌ scheduled_weekly_collect 환경설정 오류: {e}", flush=True)
        if bot:
            await _notify_admin(bot, f"❌ 주간 뉴스 수집 환경설정 오류: {e}")
        return
    except Exception as e:
        print(f"❌ scheduled_weekly_collect 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if bot:
            await _notify_admin(bot, f"❌ 주간 뉴스 수집 예외: {e}")
        return

    try:
        await _ensure_settings_seed_async()
        result = await asyncio.to_thread(
            save_candidates_to_sheet, candidates, REGION_TO_TRIBE
        )
        print("✅ scheduled_weekly_collect 시트 저장 완료", flush=True)
    except Exception as e:
        print(f"❌ scheduled_weekly_collect 시트 저장 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if bot:
            await _notify_admin(bot, f"❌ 주간 뉴스 시트 저장 실패: {e}")
        return

    if bot:
        by_region = result.get("by_region", {})
        lines = ["📰 주간 뉴스 후보 수집 완료. 시트 확인 후 /send_news 실행"]
        for region in REGION_QUERY_MAP:
            lines.append(f"  • {region}: {by_region.get(region, 0)}건")
        await _notify_admin(bot, "\n".join(lines))
    _ = time  # noqa: prevent linter unused


async def cmd_news_exclude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/news_exclude 키워드 점수 — CUSTOM_KEYWORDS 즉시 추가 (옵션 B c-2)."""
    print(f"🔍 cmd_news_exclude 호출 by {update.effective_user.id if update.effective_user else '?'}", flush=True)
    if await _deny(update, context):
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "사용법: /news_exclude 키워드 점수\n"
            "예: /news_exclude 신곡 -150\n"
            "양수도 가능: /news_exclude 봉사단 +60\n"
            "(다음 /news_collect 부터 적용 — 봇 재시작 후에도 유지)"
        )
        return

    keyword = args[0]
    try:
        score = int(args[1])
    except ValueError:
        await update.message.reply_text("점수는 숫자 (예: -150)")
        return

    import json
    import os
    from services import news_categorizer
    path = news_categorizer.CUSTOM_KEYWORDS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    custom = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception as e:
            print(f"⚠️ custom_keywords.json 읽기 실패: {e}", flush=True)
    custom[keyword] = score
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
    except Exception as e:
        await update.message.reply_text(f"❌ 저장 실패: {e}")
        return

    # 런타임 dict 도 즉시 갱신 (봇 재시작 없이 다음 호출부터 반영)
    news_categorizer.CUSTOM_KEYWORDS[keyword] = score

    await update.message.reply_text(
        f"✅ 키워드 추가: '{keyword}' = {score:+d}점\n"
        f"다음 /news_collect 부터 적용 (즉시 런타임 반영됨)\n"
        f"현재 custom 키워드 {len(custom)}개"
    )
