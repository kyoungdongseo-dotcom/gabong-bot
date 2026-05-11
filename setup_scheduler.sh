#!/bin/bash
# 세계경제 뉴스 카드 자동 생성 스케줄러 설정 스크립트

echo "🔧 자동 스케줄러 설정을 시작합니다...\n"

# Python 스크립트 경로
PYTHON_SCRIPT="/Users/seogyeongdong/gabong-bot/auto_generate_news.py"
LOG_FILE="/Users/seogyeongdong/gabong-bot/logs/auto_generate.log"

# 로그 디렉토리 생성
mkdir -p /Users/seogyeongdong/gabong-bot/logs

echo "📋 crontab 설정 정보:"
echo "   - 실행 시간: 매일 오전 8시 (월~금 자동)"
echo "   - Python 스크립트: $PYTHON_SCRIPT"
echo "   - 로그 파일: $LOG_FILE"
echo ""

# 기존 crontab 백업
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || echo "기존 crontab 없음"

# 새로운 cron job 추가 (기존 crontab 유지)
# 매일 오전 8:00에 Python 스크립트 실행
CRON_JOB="0 8 * * 1-5 /usr/bin/python3 $PYTHON_SCRIPT >> $LOG_FILE 2>&1"

(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ crontab 설정 완료!"
echo ""
echo "📍 확인 방법:"
echo "   crontab -l"
echo ""
echo "🛠️  수동으로 테스트 실행:"
echo "   /usr/bin/python3 $PYTHON_SCRIPT"
echo ""
echo "📝 로그 확인:"
echo "   tail -f $LOG_FILE"
