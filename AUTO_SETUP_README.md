# 🤖 세계경제 뉴스 카드 자동 생성 시스템

매일 월~금에 세계경제 뉴스 카드를 자동으로 생성하는 자동화 시스템입니다.

## 📋 시스템 구조

```
gabong-bot/
├── auto_generate_news.py        # 메인 자동화 스크립트
├── news_data.json               # 뉴스 데이터 (매일 수정)
├── setup_scheduler.sh           # 스케줄러 설정 스크립트
├── logs/
│   └── auto_generate.log        # 실행 로그
└── 세계경제뉴스_YYYY년M월D일/  # 생성된 폴더 (날짜별)
    ├── 00-cover.png
    ├── 01-CEASEFIRE.png
    ├── 02-OIL_MARKET.png
    ├── 03-KOSPI_7000.png
    ├── 04-FX_MARKET.png
    ├── 05-AI_CHIPS.png
    └── 06-ECOMMERCE.png
```

## ⏰ 자동 실행 설정

**현재 설정:**
- 📅 매일 **오전 8:00**에 자동 실행
- 📍 **월~금**만 실행 (주말 제외)
- 📝 실행 로그: `/Users/seogyeongdong/gabong-bot/logs/auto_generate.log`

확인:
```bash
crontab -l
```

## 📝 사용 방법

### 1️⃣ 뉴스 데이터 입력

매일 `news_data.json` 파일을 수정해서 뉴스 정보를 입력합니다.

```json
{
  "date": "2026년 5월 8일",          // 📅 오늘 날짜
  "summary": "오늘의 요약 내용...",   // 📄 오늘의 요약
  "quote": {                          // 💬 오늘의 명언
    "text": "명언 내용",
    "author": "저자"
  },
  "cards": [
    {
      "type": "cover"                 // 커버 카드 (수정 불가)
    },
    {
      "num": "01",                    // 카드 번호
      "emoji": "🕊️",                 // 이모지
      "category": "외교 · 에너지",    // 카테고리
      "headline": "제목",              // 제목 (줄바꿈은 \n 사용)
      "body": "본문 내용...",         // 본문
      "tag": "CEASEFIRE",             // 태그 (영문 대문자)
      "accent": "#38BDF8"             // 강조색 (16진수)
    },
    // ... 더 많은 카드
  ]
}
```

### 2️⃣ 수동으로 실행하기

```bash
python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py
```

### 3️⃣ 로그 확인

```bash
# 실시간 로그 확인
tail -f /Users/seogyeongdong/gabong-bot/logs/auto_generate.log

# 전체 로그 확인
cat /Users/seogyeongdong/gabong-bot/logs/auto_generate.log
```

## 🎨 색상 코드 참고

| 카테고리 | 색상 코드 | 미리보기 |
|---------|---------|---------|
| 외교·에너지 | #38BDF8 | 🔵 하늘색 |
| 에너지·중동 | #F59E0B | 🟠 주황색 |
| 증시·반도체 | #10B981 | 🟢 녹색 |
| 환율·외환 | #8B5CF6 | 🟣 보라색 |
| AI·빅테크 | #EF4444 | 🔴 빨강색 |
| 유통·소비 | #F97316 | 🟠 진주황 |

## 🔧 스케줄 변경 방법

오전 8시가 아닌 다른 시간에 실행하려면:

```bash
# crontab 편집
crontab -e

# 예시:
# 매일 오전 10:00 실행
# 0 10 * * 1-5 /usr/bin/python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py >> /Users/seogyeongdong/gabong-bot/logs/auto_generate.log 2>&1
```

### Cron 문법 설명
```
분(0-59) 시(0-23) 일(1-31) 월(1-12) 요일(0-6, 월=1 금=5)
   0        8       *       *       1-5
```

## 🛠️ 문제 해결

### ❌ 이미지가 생성되지 않음
1. 로그 확인: `tail -f logs/auto_generate.log`
2. 수동 실행으로 테스트: `python3 auto_generate_news.py`
3. Puppeteer 설치 확인: `npm list puppeteer` (in `/tmp/react-converter`)

### ❌ 스케줄이 실행되지 않음
1. crontab 설정 확인: `crontab -l`
2. 시스템 로그 확인: `log stream --predicate 'process == "cron"'`
3. Python 경로 확인: `which python3`

### ❌ 권한 오류
```bash
chmod +x /Users/seogyeongdong/gabong-bot/auto_generate_news.py
```

## 📚 파일 위치

| 파일 | 위치 |
|-----|-----|
| 자동화 스크립트 | `/Users/seogyeongdong/gabong-bot/auto_generate_news.py` |
| 뉴스 데이터 | `/Users/seogyeongdong/gabong-bot/news_data.json` |
| 실행 로그 | `/Users/seogyeongdong/gabong-bot/logs/auto_generate.log` |
| 생성된 이미지 | `/Users/seogyeongdong/gabong-bot/세계경제뉴스_YYYY년M월D일/` |

## ✨ 특징

✅ **자동 스케줄링** - 매일 자동으로 실행
✅ **평일만 실행** - 주말은 자동으로 스킵
✅ **날짜별 폴더** - 매일 새로운 폴더 생성
✅ **7개 이미지** - 커버 1장 + 뉴스 6장
✅ **로그 기록** - 실행 결과 자동 저장
✅ **쉬운 수정** - JSON만 편집하면 됨

---

**마지막 설정: 2026년 5월 7일**
