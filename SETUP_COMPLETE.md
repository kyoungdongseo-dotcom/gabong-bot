# ✅ 세계경제 뉴스 카드 자동 생성 시스템 - 설정 완료!

## 🎉 설정 현황

| 항목 | 상태 | 세부 정보 |
|-----|------|---------|
| **자동 스케줄링** | ✅ 완료 | 매일 오전 8:00 실행 (월~금) |
| **이미지 변환** | ✅ 완료 | Puppeteer 기반 자동 변환 |
| **로그 기록** | ✅ 완료 | `/Users/seogyeongdong/gabong-bot/logs/auto_generate.log` |
| **테스트 실행** | ✅ 성공 | 7개 이미지 정상 생성됨 |

---

## 📝 매일 해야 할 일 (5분)

### **아침 8시 전에 이것만 하세요:**

1. **텍스트 에디터로 파일 열기:**
   ```
   /Users/seogyeongdong/gabong-bot/news_data.json
   ```

2. **다음 정보만 수정:**
   - `date`: 오늘 날짜 (예: `2026년 5월 8일`)
   - `summary`: 오늘의 경제 요약
   - `quote.text`: 오늘의 명언
   - `quote.author`: 명언 저자
   - `cards` 배열: 6개의 뉴스 정보

3. **저장하고 끝!** 
   - 자동으로 오전 8시에 이미지가 생성됨
   - 또는 수동으로 즉시 실행:
   ```bash
   python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py
   ```

---

## 📂 폴더 구조

```
gabong-bot/
├── 📄 auto_generate_news.py       ← 메인 자동화 스크립트
├── 📄 news_data.json              ← 📝 매일 수정할 뉴스 데이터
├── 📄 AUTO_SETUP_README.md        ← 자세한 설명서
├── 📄 DAILY_GUIDE.sh              ← 빠른 가이드
├── 📄 setup_scheduler.sh          ← 스케줄러 설정 스크립트
├── 📁 logs/
│   └── 📊 auto_generate.log       ← 실행 로그
└── 📁 세계경제뉴스_YYYY년M월D일/  ← 날짜별 생성 폴더
    ├── 00-cover.png
    ├── 01-CEASEFIRE.png
    ├── 02-OIL_MARKET.png
    ├── 03-KOSPI_7000.png
    ├── 04-FX_MARKET.png
    ├── 05-AI_CHIPS.png
    └── 06-ECOMMERCE.png
```

---

## 🔧 현재 설정 확인

**Crontab 설정 (매일 오전 8:00 실행):**
```bash
crontab -l
```

출력 예:
```
0 8 * * 1-5 /usr/bin/python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py >> /Users/seogyeongdong/gabong-bot/logs/auto_generate.log 2>&1
```

---

## 🚀 사용 예시

### **news_data.json 수정 예시:**

```json
{
  "date": "2026년 5월 8일",
  "summary": "미국 실업률 사상 최저, 기술주 강세 지속. 금리 인상 선 긋고...",
  "quote": {
    "text": "성공은 실패보다 조금 더 많은 노력이다.",
    "author": "토마스 에디슨"
  },
  "cards": [
    { "type": "cover" },
    {
      "num": "01",
      "emoji": "📊",
      "category": "경제 · 고용",
      "headline": "실업률\n사상 최저",
      "body": "미국 4월 실업률 3.2%로 경기 강세 지속. 임금 상승률은 둔화 추세로...",
      "tag": "UNEMPLOYMENT",
      "accent": "#06B6D4"
    },
    // ... 5개 더
  ]
}
```

---

## 🎨 이모지 & 색상 추천

| 주제 | 추천 이모지 | 추천 색상 | 16진수 |
|-----|----------|---------|-------|
| 경제 | 📊 | 파랑 | #38BDF8 |
| 에너지 | 🛢️ | 주황 | #F59E0B |
| 증시 | 📈 | 녹색 | #10B981 |
| 외환 | 💴 | 보라 | #8B5CF6 |
| IT/AI | 🤖 | 빨강 | #EF4444 |
| 소비 | 🛍️ | 주황 | #F97316 |

---

## 🐛 문제 해결

### **자동 스케줄이 안 돌면:**
```bash
# 로그 확인
tail -f /Users/seogyeongdong/gabong-bot/logs/auto_generate.log

# 수동 테스트
python3 /Users/seogyeongdong/gabong-bot/auto_generate_news.py

# 시스템 cron 로그
log stream --predicate 'process == "cron"' --level debug
```

### **이미지 생성 실패 시:**
1. news_data.json 문법 확인 (JSON 검증)
2. Python 권한 확인: `ls -la auto_generate_news.py`
3. Puppeteer 설치 확인: `npm list puppeteer` (in `/tmp/react-converter`)

### **한글 문자 깨지면:**
news_data.json 파일이 UTF-8로 저장되었는지 확인

---

## ✨ 고급 설정

### **실행 시간 변경:**
```bash
crontab -e
# 다음 줄 찾아서 시간 수정 (현재: 0 8 = 8시)
# 10시: 0 10 * * 1-5
# 정오: 0 12 * * 1-5
```

### **매일이 아니라 특정 요일만:**
```bash
# 월, 수, 금만: 1,3,5
# 월~목: 1-4
# 월~금: 1-5 (현재)
```

---

## 📞 참고

- **저장 위치**: `/Users/seogyeongdong/gabong-bot/`
- **로그 확인**: `cat logs/auto_generate.log`
- **폴더 자동 생성**: 날짜 형식 `세계경제뉴스_YYYY년M월D일`
- **이미지 사이즈**: 800×800px (2배 스케일, 실제 400×400)

---

**🎊 준비 완료! 내일 아침 자동으로 카드가 생성됩니다.**
