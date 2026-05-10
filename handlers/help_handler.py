"""/help (인라인 버튼) + /myreports + 형식 안내 자동 응답"""

from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

KST = pytz.timezone('Asia/Seoul')


# ── /help 본문 ────────────────────────────────────────────────────────────────

HELP_TEXTS = {
    'service': """📋 봉사보고서 형식

[지파] [교회] 봉사보고서

▪️ 활동명: ○○○ 봉사
▪️ 봉사분류: 정기/일회성
▪️ 활동일시: 2026-05-09
▪️ 활동장소: ○○ 복지관
▪️ 수혜자수: 50
▪️ 내부봉사자: 10
▪️ 외부봉사자: 5

1. 활동 내용
   …
2. 반응 및 특이사항
   …
3. 참여인사
   …
4. 홍보도구
   …
5. 잘된 점
   …
6. 개선할 점
   …

📸 사진 1~10장 + 위 형식 첨부

✅ 키워드 'activity_report' 또는 '봉사보고' 포함 필수
✅ 별칭 OK: 활동명/행사명/봉사명/사업명 등""",

    'award': """🏆 수상보고서 형식

[지역] [지부] 수상보고서

▪️ 수상명: ○○○상
▪️ 수상일시: 2026-05-09
▪️ 수상자: 홍길동
▪️ 수여자: ○○ 시장
▪️ 장소: ○○ 시청
▪️ 수상내용: …

📸 사진 1~10장 + 위 형식 첨부

✅ 키워드 '수상' + '보고' 모두 필요
✅ 필수: 수상명, 수상일시, 수상자
✅ 별칭 OK: 수상명/보고제목/내용/행사명/표창명/상명""",

    'mou': """🤝 MOU 체결보고서 형식

[지역] [지부] MOU 보고

▪️ 협약명: ○○○ 협약
▪️ 기관명: ○○ 단체
▪️ 협약일시: 2026-05-09
▪️ 대표자: 홍길동
▪️ 협약기간: 1년

📸 사진 1~10장 + 위 형식 첨부

✅ 키워드 'MOU' 또는 '협약' + '보고' 모두 필요
✅ 필수: 협약명, 기관명, 협약일시
✅ 별칭 OK: 협약명/MOU명, 기관명/협약대상, 협약일시/체결일""",

    'errors': """❓ 자주 발생하는 오류

1. ⚠️ "필수 항목 누락"
   → 어떤 항목이 누락됐는지 봇이 alias 목록과 함께 안내합니다
   → 안내된 별칭 중 하나로 다시 입력

2. ❌ "사진 다운로드 실패"
   → 텔레그램 파일 링크 만료 (보통 1시간)
   → 사진을 모두 다시 보내주세요

3. ❌ "Word 파일 생성 실패"
   → 사진과 보고서를 다시 보내주세요
   → 시트 저장도 안 되어 있습니다

4. ⚠️ "시트 저장 실패 - 자동 처리됨"
   → Word 파일은 서무에게 정상 전송됨
   → 시트는 서무가 수동 추가합니다

5. 📸 "10/10장 접수 (추가 N장 무시됨)"
   → 보고서당 사진 최대 10장
   → 11장째부터 자동 무시""",

    'contact': """📞 문의처

🔧 시스템 문제: 관리자 DM
📋 보고서 형식 질문: /help
📊 본인 제출 이력: /myreports

🤖 자주 사용하는 명령어:
/help — 이 메시지
/myreports — 본인 제출 이력 (30일)
/report_stats — 월간 통계 (관리자만)
/status — 봇 상태 (관리자만)"""
}

_BUTTON_ROWS = [
    [InlineKeyboardButton("📋 봉사보고서", callback_data="help_service"),
     InlineKeyboardButton("🏆 수상보고서", callback_data="help_award")],
    [InlineKeyboardButton("🤝 MOU 보고서", callback_data="help_mou")],
    [InlineKeyboardButton("❓ 자주 발생 오류", callback_data="help_errors"),
     InlineKeyboardButton("📞 문의", callback_data="help_contact")],
]


def _main_menu_markup():
    return InlineKeyboardMarkup(_BUTTON_ROWS)


def _back_button_markup():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ 도움말 목록", callback_data="help_back")
    ]])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "🤖 GAbong Bot 도움말\n어떤 보고서를 작성하시나요?",
        reply_markup=_main_menu_markup()
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    if data == "help_back":
        try:
            await query.edit_message_text(
                "🤖 GAbong Bot 도움말\n어떤 보고서를 작성하시나요?",
                reply_markup=_main_menu_markup()
            )
        except Exception:
            pass
        return
    key = data.replace("help_", "", 1)
    text = HELP_TEXTS.get(key)
    if not text:
        await query.edit_message_text("알 수 없는 항목입니다.", reply_markup=_main_menu_markup())
        return
    try:
        await query.edit_message_text(text, reply_markup=_back_button_markup())
    except Exception:
        pass


# ── /myreports ────────────────────────────────────────────────────────────────

_REPORT_TYPE_LABEL = {
    'service': '📋 봉사',
    'award': '🏆 수상',
    'mou': '🤝 MOU',
}

_OUTCOME_LABEL = {
    'ok': '✅ 완료',
    'sheet_fail': '⚠️ 시트 실패 (Word 전송됨)',
    'partial': '⚠️ 부분 완료',
    'fail': '❌ 실패',
    'unknown': '⏳ 처리 중',
}


async def myreports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_id = update.effective_user.id
    from database import get_user_reports
    reports = get_user_reports(user_id, days=30)

    if not reports:
        await update.message.reply_text(
            "📭 최근 30일간 제출 이력이 없습니다.\n\n"
            "📌 봇이 메시지를 인식하지 못했을 수 있습니다.\n"
            "/help 로 형식 확인 후 다시 시도해주세요."
        )
        return

    # 통계
    by_type = {}
    by_outcome = {}
    for r in reports:
        rtype = r['report_type']
        outcome = r['outcome']
        by_type[rtype] = by_type.get(rtype, 0) + 1
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

    lines = [f"📋 최근 30일 제출 이력 (총 {len(reports)}건)", "━━━━━━━━━━━━━━━━━━"]

    # 타입별 합계
    type_summary = []
    for rtype, n in by_type.items():
        label = _REPORT_TYPE_LABEL.get(rtype, rtype)
        type_summary.append(f"{label} {n}건")
    lines.append("📊 " + " | ".join(type_summary))

    # 결과별 합계
    if by_outcome:
        outcome_parts = []
        for o, n in by_outcome.items():
            outcome_parts.append(f"{_OUTCOME_LABEL.get(o, o)} {n}")
        lines.append("📈 " + " / ".join(outcome_parts))

    lines.append("")
    lines.append("📅 최근 제출 (최대 20건):")

    for r in reports[:20]:
        ts = r['created_at']
        # YYYY-MM-DD HH:MM 만 표시
        try:
            short_ts = ts[5:16]
        except Exception:
            short_ts = ts
        rtype = _REPORT_TYPE_LABEL.get(r['report_type'], r['report_type'])
        outcome = _OUTCOME_LABEL.get(r['outcome'], r['outcome'])
        detail = (r['detail'] or '')[:40]
        lines.append(f"• {short_ts} {rtype} {outcome}")
        if detail:
            lines.append(f"   └ {detail}")

    if len(reports) > 20:
        lines.append(f"\n... 외 {len(reports) - 20}건")

    await update.message.reply_text("\n".join(lines))


# ── 형식 안내 자동 응답 (D1 + E1) ─────────────────────────────────────────────

# 키워드 부분 일치 패턴: (있어야 할 키워드 1, 있어야 할 키워드 2)
_KEYWORD_PAIRS = {
    'award': (('수상',), ('보고',)),
    'mou': (('MOU', '협약'), ('보고',)),
    'service': (('활동', '봉사'), ('보고',)),
}


def _has_any(text: str, keywords: tuple) -> bool:
    upper = text.upper()
    return any(kw.upper() in upper for kw in keywords)


def is_partial_match(report_type: str, caption: str) -> bool:
    """부분 일치: kw1 또는 kw2 중 하나만 있고 다른 하나는 없음.
    완전 일치(둘 다)도 False, 완전 미일치(둘 다 없음)도 False."""
    if not caption:
        return False
    pair = _KEYWORD_PAIRS.get(report_type)
    if not pair:
        return False
    has1 = _has_any(caption, pair[0])
    has2 = _has_any(caption, pair[1])
    return has1 != has2  # XOR — 정확히 하나만 있을 때


async def maybe_send_format_help(bot, origin: dict, user_id: int,
                                  report_type: str) -> bool:
    """1일 1회 제한 체크 후 형식 안내 reply.
    Returns: 안내 보냈으면 True"""
    if not user_id:
        return False
    from database import should_send_format_help, mark_format_help_sent
    if not should_send_format_help(user_id, report_type, cooldown_hours=24):
        return False
    text = HELP_TEXTS.get(report_type)
    if not text:
        return False
    msg = (
        f"❌ 형식 인식 실패 — 보고서로 처리하지 못했습니다\n\n"
        f"올바른 형식:\n"
        f"━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━\n"
        f"💡 /help 로 다시 확인 가능"
    )
    from handlers.report_base import reply_to_origin
    sent = await reply_to_origin(bot, origin, msg)
    if sent:
        mark_format_help_sent(user_id, report_type)
    return sent
