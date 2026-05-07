from telegram import Update
from telegram.ext import ContextTypes
import config
from handlers.weekly_report_analyzer import analyze_weekly_report
from handlers.monthly_stats_handler import analyze_monthly_stats, save_monthly_stats

ADMIN_IDS = config.get('admin_ids', [])

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """즉시 주간 분석 리포트 확인"""
    if not update.message:
        return
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    await update.message.reply_text("📊 주간 분석 리포트 생성 중...")

    try:
        report_text = analyze_weekly_report()
        await update.message.reply_text(report_text)
    except Exception as e:
        await update.message.reply_text(f"❌ 리포트 생성 오류: {e}")

async def monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """즉시 월간통계 확인"""
    if not update.message:
        return
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ 관리자만 사용 가능합니다.")
        return

    await update.message.reply_text("📈 월간통계 생성 중...")

    try:
        result_rows, month_start = analyze_monthly_stats()

        if not result_rows:
            await update.message.reply_text("📈 이번 달 봉사 데이터가 없습니다.")
            return

        save_monthly_stats(result_rows)

        total_count = sum(r[5] for r in result_rows)
        total_volunteers = sum(r[8] for r in result_rows)
        total_beneficiary = sum(r[9] for r in result_rows)

        lines = [
            f"📈 {month_start.year}년 {month_start.month}월 월간 봉사 통계",
            f"━━━━━━━━━━━━━━━━━━",
            f"",
            f"✅ 총 봉사 건수: {total_count}건",
            f"✅ 총 봉사자: {total_volunteers:,}명",
            f"✅ 총 수혜자: {total_beneficiary:,}명",
            f"",
            f"📌 주차별 현황",
        ]

        for r in result_rows:
            lines.append(
                f"  {r[2]}: {r[5]}건 / 봉사자 {r[8]:,}명 / 수혜자 {r[9]:,}명"
            )

        lines.append(f"")
        lines.append(f"✅ 월간통계 시트 저장 완료!")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        await update.message.reply_text(f"❌ 월간통계 오류: {e}")
