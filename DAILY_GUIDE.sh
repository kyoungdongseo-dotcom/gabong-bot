#!/bin/bash

# 🚀 빠른 시작 가이드 - 매일 아침 이것만 하면 됩니다!

echo "📰 세계경제 뉴스 카드 자동 생성 시스템"
echo "========================================"
echo ""

# 1. 뉴스 데이터 수정
echo "📝 Step 1: 뉴스 데이터 입력"
echo "   VS Code 또는 텍스트 에디터로 다음 파일을 열기:"
echo "   📄 /Users/seogyeongdong/gabong-bot/news_data.json"
echo ""
echo "   수정할 항목:"
echo "   1️⃣  date: 오늘 날짜 (예: 2026년 5월 8일)"
echo "   2️⃣  summary: 오늘의 경제 요약"
echo "   3️⃣  quote: 오늘의 명언"
echo "   4️⃣  cards[]: 6개의 뉴스 카드 정보"
echo ""

# 2. 파이썬 스크립트 실행
echo "🤖 Step 2: 자동 생성 실행"
echo "   터미널에서 다음 명령어 입력:"
echo ""
echo "   python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py"
echo ""

# 3. 결과 확인
echo "✅ Step 3: 생성 결과 확인"
echo "   다음 폴더에 7개의 이미지가 생성됨:"
echo "   📁 /Users/seogyeongdong/gabong-bot/세계경제뉴스_YYYY년M월D일/"
echo ""

# 4. 인스타 업로드
echo "📱 Step 4: 인스타그램에 올리기"
echo "   Finder에서 위 폴더를 열어서:"
echo "   1️⃣  00-cover.png 먼저 업로드"
echo "   2️⃣  01~06 이미지 순서대로 업로드"
echo ""

echo "========================================"
echo "💡 팁:"
echo "   - 자동 스케줄이 매일 오전 8시에 실행됩니다"
echo "   - 수동으로 언제든 위 명령어로 실행 가능"
echo "   - 오류 발생 시: tail -f logs/auto_generate.log 로 확인"
echo ""
